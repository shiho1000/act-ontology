"""
act_classifiers.py  —  ACT Phase 2 ActionType classification cascade.

Replaces the hand-built VERB_TO_AT dictionary with a signal-producing cascade:

    (a) catalog lookup   — normalized skos:example / multilabel.ttl match   -> catalogHit
    (b) Gemini catalog   — LLM prompted with act_llm_catalog.md (expr only)  -> llmLabels
    (c) BERT centroid    — Tohoku BERT v3 prototype nearest-centroid         -> bertLabels

The combiner fuses these into a single result whose confidence is CROSS-SIGNAL
agreement (not LLM self-report, not inter-LLM agreement). Raw signals are stored
separately so the confidence formula can be re-tuned later WITHOUT re-running the
(expensive) LLM/BERT passes.

Public API (drop-in for acta_etl.classify_action):
    classify_action(expr) -> {
        "labels":     [<taxonomy local name>, ...],   # 0..*
        "confidence": float in [0,1],
        "band":       "exact"|"strong"|"moderate"|"weak"|"none",
        "signals":    {"catalogHit":bool, "catalogKind":str|None,
                       "bertLabels":[...], "bertSim":float|None, "bertAgree":bool,
                       "llmLabels":[...], "selfConsistency":float|None},
    }

Design notes
------------
* Classification is EXPRESSION-level (type-level). The Event context is never read
  here — consistent with the "action-centric, portable taxonomy" decision.
* WordNet is intentionally NOT a cascade path (Phase 1: coverage gap on exactly the
  hard words). BERT centroid is the no-LLM baseline (no dictionary gap: always returns).
* Sandbox status: (a) and the combiner are testable offline; (b) needs GEMINI_API_KEY
  + network, (c) needs transformers/torch + the model weights — both run on your
  machine, not in this sandbox. Run `python act_classifiers.py --selftest` for (a)+combiner.
"""

import os
import re
import sys
import json
import math
import time
import unicodedata
import urllib.request
import urllib.error
from collections import defaultdict

# ==========================================================================
# CONFIG
# ==========================================================================
import os
from pathlib import Path

# Paths resolve from the location of this file, so the pipeline runs from any working directory.
# Repository layout: ACT files at the top, scripts in pipeline/, generated artifacts in artifacts/.
PIPELINE_DIR = Path(__file__).resolve().parent
REPO_DIR = PIPELINE_DIR.parent

TAXONOMY_TTL   = Path(os.environ.get("ACT_TAXONOMY_TTL",   REPO_DIR / "act_taxonomy.ttl"))
MULTILABEL_TTL = Path(os.environ.get("ACT_MULTILABEL_TTL", REPO_DIR / "act_multilabel.ttl"))
LLM_CATALOG_MD = Path(os.environ.get("ACT_LLM_CATALOG_MD", REPO_DIR / "artifacts" / "act_llm_catalog.md"))
LLM_CACHE      = Path(os.environ.get("ACT_LLM_CACHE",      REPO_DIR / "cache" / "llm_cache.jsonl"))

# --- Gemini (Google AI Studio free tier) ---
GEMINI_MODEL    = "gemini-3.1-flash-lite"          # free-tier Flash; adjust to current model id
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
GEMINI_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   "{model}:generateContent?key={key}")
SELF_CONSISTENCY_N = 1          # >1 => sample N times at temperature>0, use agreement
GEMINI_TEMPERATURE = 0.0        # 0 for single-shot; raise if SELF_CONSISTENCY_N > 1
LLM_BACKOFF_BASE = 4.2
LLM_MAX_RETRIES  = 6
LLM_BACKOFF_CAP  = 60.0
# LLM_CACHE (defined above) memoizes successful Gemini calls (key: model|expr). 429/network
# failures are NOT cached, so they retry next run. Delete the file to reset. Lets rate-limited
# runs resume cheaply and makes the evaluation reproducible.

# --- Tohoku BERT centroid ---
BERT_MODEL         = "cl-tohoku/bert-base-japanese-v3"
BERT_SIM_THRESHOLD = 0.55       # min cosine to accept a label
BERT_TOPK          = 2          # allow up to K labels (multilabel) above threshold

# --- confidence bands (derived from the numeric score) ---
BANDS = [(0.95, "exact"), (0.75, "strong"), (0.55, "moderate"),
         (0.35, "weak"), (0.0, "none")]

NS_TAX = "https://w3id.org/act/taxonomy#"


# ==========================================================================
# normalization
# ==========================================================================
def normalize(expr: str) -> str:
    """NFKC + strip. Kept deliberately light so the same key is used everywhere
    (catalog build AND lookup MUST call this identically)."""
    return unicodedata.normalize("NFKC", (expr or "").strip())


# ==========================================================================
# (a) catalog lookup  — offline, deterministic, testable
# ==========================================================================
class CatalogIndex:
    """Inverted index built from the PUBLISHED taxonomy artifacts only
    (skos:example single-label + act_multilabel.ttl). The G-T dictionary is
    NOT loaded here — it stays held out as evaluation gold."""

    def __init__(self, taxonomy_ttl=TAXONOMY_TTL, multilabel_ttl=MULTILABEL_TTL):
        from rdflib import Graph
        from rdflib.namespace import SKOS
        self.single = defaultdict(set)    # normalized token -> {class}
        self.multi = {}                   # normalized expr   -> [class, ...]

        g = Graph(); g.parse(taxonomy_ttl, format="turtle")
        for c in set(g.subjects(SKOS.prefLabel, None)):
            local = str(c).split("#")[-1]
            for ex in g.objects(c, SKOS.example):
                for tok in re.split(r"[・,、]", str(ex)):
                    tok = normalize(tok)
                    if tok:
                        self.single[tok].add(local)

        m = Graph(); m.parse(multilabel_ttl, format="turtle")
        P_expr = P_type = None
        for p in set(m.predicates()):
            ln = str(p).split("#")[-1].split("/")[-1]
            if ln == "expression":   P_expr = p
            if ln == "hasActionType": P_type = p
        if P_expr and P_type:
            for s in m.subjects(P_expr, None):
                expr = normalize(str(next(m.objects(s, P_expr))))
                labels = sorted(str(o).split("#")[-1] for o in m.objects(s, P_type))
                if expr and labels:
                    self.multi[expr] = labels

    def lookup(self, expr: str):
        """Return (labels_or_None, kind). kind in {'multilabel','single',None}."""
        key = normalize(expr)
        if key in self.multi:
            return self.multi[key], "multilabel"
        if key in self.single:
            return sorted(self.single[key]), "single"
        return None, None


# ==========================================================================
# (b) Gemini catalog classifier  — needs API key + network (run on your machine)
# ==========================================================================
class GeminiClassifier:
    def __init__(self, catalog_md=LLM_CATALOG_MD, api_key=None, model=None, cache_path=None):
        # Read the CURRENT module globals at construction time. Do NOT default the
        # signature to GEMINI_API_KEY/GEMINI_MODEL: default args are bound once at import,
        # so a later `act_classifiers.GEMINI_API_KEY = ...` would be ignored (the classic
        # frozen-default bug -> empty key -> HTTP 403 unregistered caller).
        self.model   = model   if model   is not None else GEMINI_MODEL
        self.api_key = api_key if api_key is not None else GEMINI_API_KEY
        with open(catalog_md, encoding="utf-8") as f:
            self.catalog = f.read()
        self.cache_path = cache_path if cache_path is not None else LLM_CACHE
        self._cache = self._load_cache()

    def _cache_key(self, expr):
        return f"{self.model}|{normalize(expr)}"

    def _load_cache(self):
        cache = {}
        if self.cache_path and os.path.exists(self.cache_path):
            with open(self.cache_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        o = json.loads(line)
                        cache[o["k"]] = (o["labels"], o["sc"])
                    except Exception:
                        pass
        return cache

    def _append_cache(self, key, labels, sc):
        self._cache[key] = (labels, sc)
        if self.cache_path:
            Path(self.cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"k": key, "labels": labels, "sc": sc},
                                   ensure_ascii=False) + "\n")

    def _prompt(self, expr: str, single_label: bool = False) -> str:
        # (ii): the multilabel permission + output format live HERE (task instruction),
        # not in the catalog (which carries only taxonomy-derived facts + AFFIX rules).
        instr = (
            "Classify the single Japanese Action expression below. Assign EXACTLY ONE "
            "ActionType local name (the single best fit)."
            if single_label else
            "Classify the single Japanese Action expression below into one or more "
            "ActionType local names from the catalog. Assign MORE THAN ONE only when "
            "the expression is genuinely multivalent (per the AFFIX rules / multilabel)."
        )
        return (
            "You are an ActionType classifier for a historical-event knowledge graph.\n"
            + instr + " Judge the expression alone; do NOT invent context.\n"
            "Output STRICT JSON only: {\"labels\": [\"LocalName\", ...]}. No prose.\n\n"
            "=== CATALOG ===\n" + self.catalog +
            "\n=== EXPRESSION ===\n" + expr + "\n"
        )

    def _call_once(self, prompt: str, temperature: float) -> list:
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature,
                                 "responseMimeType": "application/json"},
        }).encode("utf-8")
        url = GEMINI_ENDPOINT.format(model=self.model, key=self.api_key)
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text).get("labels", [])

    def classify(self, expr: str, n=SELF_CONSISTENCY_N, single_label: bool = False):
        """Return (labels, self_consistency). self_consistency in [0,1] over n samples
        (1.0 if n==1). Network/parse errors -> ([], None) so the combiner degrades.
        Successful results are memoized to self.cache_path; failures (e.g. HTTP 429) are
        NOT cached, so a rate-limited run can resume and only retry the misses.
        Cache key for the default multi-label prompt (single_label=False) is UNCHANGED
        ("{model}|{expr}") for backward compatibility with existing cache files; the
        single-label prompt uses a separate "single|{model}|{expr}" namespace so the two
        prompts never collide."""
        key = ("single|" if single_label else "") + self._cache_key(expr)
        if key in self._cache:                          # cache hit -> no API call needed,
            return self._cache[key]                      # check this BEFORE requiring a key
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        prompt = self._prompt(expr, single_label=single_label)
        runs = []
        temp = GEMINI_TEMPERATURE if n == 1 else max(GEMINI_TEMPERATURE, 0.4)
        for _ in range(max(1, n)):
            try:
                runs.append(tuple(sorted(self._call_once(prompt, temp))))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    raise    # let the caller (e.g. eval's backoff wrapper) retry;
                             # swallowing this here made rate limits look like
                             # "genuinely empty" results with no way to recover.
                continue     # other HTTP errors: skip this attempt, same as before
            except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError):
                continue
        if not runs:
            return [], None                             # all attempts failed -> DO NOT cache
        # majority label set + agreement fraction
        from collections import Counter
        top, cnt = Counter(runs).most_common(1)[0]
        labels, sc = list(top), (cnt / len(runs))
        self._append_cache(key, labels, sc)             # cache only successful responses
        return labels, sc


# ==========================================================================
# (c) BERT centroid  — needs transformers/torch + model weights (run on your machine)
# ==========================================================================
class BertCentroid:
    def __init__(self, taxonomy_ttl=TAXONOMY_TTL, model_name=BERT_MODEL):
        import torch                                    # lazy: only if BERT path used
        from transformers import AutoTokenizer, AutoModel
        from rdflib import Graph
        from rdflib.namespace import SKOS
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).eval()

        # class prototype text = examples + prefLabel + definition (label-aware)
        g = Graph(); g.parse(taxonomy_ttl, format="turtle")
        Q_AT = ("PREFIX skos:<http://www.w3.org/2004/02/skos/core#> "
                "SELECT ?c WHERE { ?c skos:broader ?cat }")
        action_types = set(g.query(Q_AT))
        self.labels, texts = [], []
        for row in action_types:
            c = row.c
            local = str(c).split("#")[-1]
            bag = []
            for ex in g.objects(c, SKOS.example):
                bag += [t for t in re.split(r"[・,、]", str(ex)) if t.strip()]
            bag += [str(o) for o in g.objects(c, SKOS.prefLabel)]
            bag += [str(o) for o in g.objects(c, SKOS.definition)]
            if bag:
                self.labels.append(local)
                texts.append(" ".join(bag))
        self.centroids = self._embed(texts)                # [n_class, dim], L2-normalized

    def _embed(self, texts):
        import torch
        vecs = []
        with torch.no_grad():
            for t in texts:
                enc = self.tok(t, return_tensors="pt", truncation=True, max_length=64)
                out = self.model(**enc).last_hidden_state[:, 0]   # CLS
                vecs.append(torch.nn.functional.normalize(out, dim=1))
        return torch.cat(vecs, 0)

    def classify(self, expr, topk=BERT_TOPK, threshold=BERT_SIM_THRESHOLD):
        v = self._embed([normalize(expr)])              # [1, dim]
        sims = (v @ self.centroids.T).squeeze(0)        # cosine (both normalized)
        vals, idx = self.torch.topk(sims, k=min(topk, len(self.labels)))
        labels = [self.labels[i] for i, s in zip(idx.tolist(), vals.tolist())
                  if s >= threshold]
        return labels, float(vals[0])                   # top similarity as signal


# ==========================================================================
# combiner  — cross-signal agreement -> confidence + band
# ==========================================================================
def _band(score: float) -> str:
    for thr, name in BANDS:
        if score >= thr:
            return name
    return "none"

def combine(catalog, bert, llm):
    """
    catalog: (labels|None, kind)
    bert:    (labels, top_sim) | None
    llm:     (labels, self_consistency) | None
    Returns the public result dict. Confidence is a TRANSPARENT function of the
    stored signals so it can be recomputed/re-tuned without re-running b/c.
    """
    cat_labels, cat_kind = catalog
    bert_labels, bert_sim = bert if bert else ([], None)
    llm_labels, self_cons = llm if llm else ([], None)

    signals = {
        "catalogHit":  cat_labels is not None,
        "catalogKind": cat_kind,
        "bertLabels":  bert_labels,
        "bertSim":     bert_sim,
        "bertAgree":   False,
        "llmLabels":   llm_labels,
        "selfConsistency": self_cons,
    }

    # 1) catalog is authoritative when it hits (deterministic, matches published vocab)
    if cat_labels is not None:
        signals["bertAgree"] = bool(bert_labels) and bert_labels[0] in cat_labels
        return {"labels": cat_labels, "confidence": 1.0,
                "band": "exact", "signals": signals}

    # 2) otherwise LLM is primary; BERT is the cross-signal check
    labels = llm_labels or bert_labels
    bert_agree = bool(bert_labels) and bool(llm_labels) and (bert_labels[0] in llm_labels)
    signals["bertAgree"] = bert_agree

    score = 0.50 if llm_labels else 0.30            # base: did the LLM commit?
    if bert_agree:                 score += 0.20    # methods agree (independent cross-check)
    if llm_labels and bert_labels: score += 0.05    # both methods produced something
    # NOTE: selfConsistency is recorded in signals (above) for observability, but is
    # NOT scored. With SELF_CONSISTENCY_N=1 it is always 1.0 (single sample vs itself),
    # so it added no real signal beyond "the LLM answered" -- double-counting the base
    # score. Re-enable a self-consistency bonus only if SELF_CONSISTENCY_N > 1 is used
    # (multi-sample agreement), at which point it becomes a genuine independent check.
    if not llm_labels and not bert_labels:
        return {"labels": [], "confidence": 0.15, "band": "none", "signals": signals}
    score = min(score, 0.75)                        # max reachable via LLM+BERT agreement
                                                     # alone (no self-consistency bonus);
                                                     # 'exact' (1.0) stays reserved for
                                                     # catalog hits; 'strong' (>=0.78) is
                                                     # now unreachable without catalog --
                                                     # by design (per 2026-08 decision).

    return {"labels": labels, "confidence": round(score, 3),
            "band": _band(score), "signals": signals}


# ==========================================================================
# public entry — lazy singletons; drop-in for acta_etl.classify_action
# ==========================================================================
_index = _gemini = _bert = None
USE_LLM = True     # toggle to run the no-LLM (catalog + BERT only) configuration
USE_BERT = True

def _lazy():
    global _index, _gemini, _bert
    if _index is None:
        _index = CatalogIndex()
    if USE_LLM and _gemini is None and GEMINI_API_KEY:
        _gemini = GeminiClassifier()
    if USE_BERT and _bert is None:
        try:
            _bert = BertCentroid()
        except Exception as e:                      # transformers/torch/model absent
            print(f"[act_classifiers] BERT unavailable: {e}", file=sys.stderr)
            
def _call_llm_with_backoff(gc, expr):
    """Same retry policy as api_fill_from_corpus.py's call_with_backoff, inlined here
    so the live path benefits without needing the offline tool. On exhaustion, degrades
    to ([], None) same as before -- the combiner still works, just without LLM signal."""
    delay = LLM_BACKOFF_BASE
    for attempt in range(LLM_MAX_RETRIES):
        try:
            return gc.classify(expr)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < LLM_MAX_RETRIES - 1:
                time.sleep(delay)
                delay = min(delay * 2, LLM_BACKOFF_CAP)
                continue
            return [], None
        except Exception:
            return [], None
    return [], None

def classify_action(expr: str) -> dict:
    _lazy()
    catalog = _index.lookup(expr)
    if catalog[0] is not None:                      # short-circuit: no LLM/BERT needed
        return combine(catalog, None, None)
    bert = None
    if USE_BERT and _bert is not None:
        try: bert = _bert.classify(expr)
        except Exception: bert = None
    llm = None
    if USE_LLM and _gemini is not None:
        llm = _call_llm_with_backoff(_gemini, expr)
    return combine(catalog, bert, llm)
 

# ==========================================================================
# offline self-test: catalog lookup + combiner only
# ==========================================================================
def _selftest():
    idx = CatalogIndex()
    print(f"catalog: {len(idx.single)} single tokens, {len(idx.multi)} multilabel exprs\n")
    for e in ["暗殺", "侵略", "交渉開始", "調印", "この語は辞書に無い"]:
        labels, kind = idx.lookup(e)
        print(f"  lookup {e!r:12} -> {labels} ({kind})")
    print()
    cases = {
        "catalog multilabel": combine((["MilitaryAttack", "ConquestOccupation"], "multilabel"), None, None),
        "llm+bert agree":     combine((None, None), (["MilitaryAttack"], 0.71), (["MilitaryAttack"], 1.0)),
        "llm only, no bert":  combine((None, None), ([], 0.40), (["Declaration"], 1.0)),
        "llm vs bert differ": combine((None, None), (["Suppression"], 0.60), (["Declaration"], 0.6)),
        "nothing":            combine((None, None), ([], 0.10), ([], None)),
    }
    for name, r in cases.items():
        print(f"  {name:22} conf={r['confidence']:.2f} band={r['band']:9} labels={r['labels']} "
              f"bertAgree={r['signals']['bertAgree']}")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("usage: python act_classifiers.py --selftest   (offline: catalog + combiner)")