#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_classify.py  —  ACT Phase 2 held-out evaluation harness.

Compares the two ActionType classifier *methods* head-to-head on the SAME
held-out expression folds, scored against the frozen gold dictionary. NO KG is written.

    no-LLM  :  Tohoku BERT v3 nearest-centroid          (the baseline)
    LLM     :  Gemini catalog classifier                (the primary)

Why this file exists
--------------------
The paper's central quantitative claim is "how much does the LLM path buy us
over the no-LLM baseline, at the expression level" — a METHOD comparison, so we
turn the catalog OFF and classify every test expression with BERT / Gemini only.

Two SEPARATE artifacts (this is what makes the comparison non-circular):
  * gold (grading key)      : frozen CSV act_gold_v0_6_1.csv, expression -> action_types
                              (catalog-authoritative on the 15 reconciled expressions).
  * catalog (training pool) : TTL skos:example + multilabel.ttl — exactly what
                              act_classifiers builds BERT centroids / the LLM prompt from.
The gold and the catalog are different sets: 385 shared, ~189 gold-only ("catalog
gap"), plus catalog-only English glosses we never grade on.

The load-bearing correctness requirement
----------------------------------------
Leak can occur only on SHARED expressions (in both gold and catalog). Per fold we
remove each held-out TEST expression from the catalog pools before (re)building the
BERT centroids and the Gemini prompt catalog, so a test item never sits in its own
class prototype or as an in-context example. The ~189 catalog-gap expressions are
absent from the catalog to begin with -> a pure, leak-free held-out subset, reported
separately. Taxonomy FACTS (prefLabel, definition, AFFIX note) are kept every fold.

Faithfulness notes (differences from production act_classifiers, on purpose)
----------------------------------------------------------------------------
  * BERT_CENTROID_MODE defaults to "mean" (true nearest-centroid = mean of
    per-example CLS embeddings). Production BertCentroid embeds the concatenated
    example-bag once (truncated at 64 tokens); "mean" is the standard estimator and
    makes per-example hold-out meaningful. Set "bag" to measure the production one.
  * The single-label track uses a single-label Gemini prompt (exactly one label);
    the multilabel track uses the multilabel prompt. This avoids an ill-defined
    "top-1 of an unordered set" when reducing a multi-output LLM to one label.

Metrics  (pooled over out-of-fold predictions; small classes get full support)
-------
  Headline  (single-label track, gold has exactly 1 label):
      label-based Macro-F1 over the 44 classes  +  micro accuracy.
  Auxiliary (multilabel track, all gold expr):
      example-based F1 (Dice)  +  label-based Macro-F1 over the 44 classes.
  Each reported OVERALL and on the catalog-gap subset (pure held-out generalization).

Run
---
    python3 eval_classify.py --selftest         # offline: verify scoring math (this sandbox)
    python3 eval_classify.py --bert             # no-LLM only (needs transformers/torch + weights)
    python3 eval_classify.py --bert --llm       # both  (also needs GEMINI_API_KEY + network)
    python3 eval_classify.py --bert --llm --centroid-mode bag
Outputs: eval_report.md, eval_results.json  (NO .ttl).
"""

import os
import re
import sys
import json
import math
import time
import random
import hashlib
import argparse
import unicodedata
import urllib.error
from collections import defaultdict, Counter

from pathlib import Path

# Reuse production primitives so the harness measures the real classifiers,
# not a re-implementation. (BERT/Gemini are only touched when --bert/--llm set.)
EVAL_DIR = Path(__file__).resolve().parent
REPO_DIR = EVAL_DIR.parent
sys.path.insert(0, str(REPO_DIR / "pipeline"))
import act_classifiers as AC

# ==========================================================================
# CONFIG
# ==========================================================================
TAXONOMY_TTL   = AC.TAXONOMY_TTL      # act_taxonomy.ttl at the repository top
MULTILABEL_TTL = AC.MULTILABEL_TTL    # act_multilabel.ttl at the repository top
DATA_DIR       = EVAL_DIR / "data"    # not public (derived from the COTEN History DB)
GOLD_CSV       = DATA_DIR / "gold.csv"   # frozen G-T (expression -> action_types), catalog-authoritative

N_FOLDS  = 5
SEED     = 42                      # fixed for reproducibility (Phase 1 also used 5-fold+seed;
                                   # exact seed differs — Phase 2 is a fresh 44-class run, not a
                                   # bit-for-bit Phase 1 reproduction).

BERT_CENTROID_MODE   = "mean"      # "mean" (true nearest-centroid) | "bag" (production-faithful)
BERT_INCLUDE_LABEL_TEXT = True     # add prefLabel+definition as extra prototype signal
BERT_SIM_THRESHOLD   = AC.BERT_SIM_THRESHOLD
BERT_TOPK            = AC.BERT_TOPK
BERT_CACHE           = REPO_DIR / "cache" / "bert_predictions_cache.json"   # per-(seed,centroid_mode) predictions.
                                                       # BERT is deterministic given the fold
                                                       # split + centroid mode, so once computed
                                                       # the whole run can be skipped entirely.

LLM_INCLUDE_EXAMPLES = True        # False => pure zero-shot (labels+defs only), closer Phase-1 analog
LLM_INCLUDE_AFFIX    = True        # keep scheme editorialNotes (AFFIX rules) in the fold catalog
LLM_CATALOG_MODE     = "fixed"     # "fixed"  (B, simple): ONE catalog built once from ALL catalog
                                   #   exprs (no per-fold rebuild). Matches the exploratory
                                   #   llm_vs_gold.csv condition (act_llm_catalog.md-style: no
                                   #   definitions) and lets the llm_cache.jsonl from that run
                                   #   be reused here (same prompt/catalog -> same cache key).
                                   #   Held-out is NOT enforced on the LLM side in this mode
                                   #   (only on BERT); acceptable per current design decision.
                                   # "fold"   (A, strict): rebuild per fold with test exprs
                                   #   removed (full held-out on both methods, no cache reuse
                                   #   across folds since the catalog text changes).
GEMINI_TEMPERATURE   = 0.0
GEMINI_RATE_SLEEP    = 4.2          # seconds between LLM calls (gemini-3.1-flash-lite: 15 RPM)
GEMINI_MAX_RETRIES   = 6            # backoff retries on 429 before giving up on an expression
GEMINI_BACKOFF_BASE  = 12.0         # seconds; doubles each retry, capped at GEMINI_BACKOFF_CAP
GEMINI_BACKOFF_CAP   = 70.0

# --- LLM catalog VARIANT switch --------------------------------------------------------
# "baseline"  : act_llm_catalog.md (no definitions) + llm_cache.jsonl, model tag unchanged.
#               This is the frozen baseline (matches the exploratory llm_vs_gold.csv run).
# "withdef"   : act_llm_catalog_with_def.md (definitions added) + llm_cache_with_def.jsonl,
#               model tag suffixed "+withdef" so its cache never collides with baseline's.
#               Populate via export_chat_batch.py / import_chat_batch.py --variant withdef.
LLM_VARIANT = "baseline"    # "baseline" | "withdef"

_LLM_VARIANT_CONFIG = {
    "baseline": {"catalog": AC.LLM_CATALOG_MD, "cache": AC.LLM_CACHE, "model_suffix": ""},
    "withdef":  {"catalog": REPO_DIR / "artifacts" / "act_llm_catalog_with_def.md",
                "cache": REPO_DIR / "cache" / "llm_cache_with_def.jsonl", "model_suffix": "+withdef"},
}
GEMINI_CACHE         = AC.LLM_CACHE  # used by "fold" mode only; "fixed" mode resolves its
                                     # own cache/catalog/model from _LLM_VARIANT_CONFIG below

def _resolve_llm_variant():
    """Current LLM_VARIANT's (catalog_path, cache_path, model_name)."""
    cfg = _LLM_VARIANT_CONFIG[LLM_VARIANT]
    model = AC.GEMINI_MODEL + cfg["model_suffix"]
    return cfg["catalog"], cfg["cache"], model

OUT_REPORT = EVAL_DIR / "eval_report.md"
OUT_JSON   = EVAL_DIR / "eval_results.json"

SKOS = "http://www.w3.org/2004/02/skos/core#"


# ==========================================================================
# normalization  — MUST match act_classifiers.normalize exactly
# ==========================================================================
def normalize(expr: str) -> str:
    return unicodedata.normalize("NFKC", (expr or "").strip())

def _ln(u: str) -> str:
    return str(u).split("#")[-1]


# ==========================================================================
# gold + catalog training material  — TWO SEPARATE ARTIFACTS.
#
#   gold (grading key)     : the frozen CSV (act_gold_v0_6_1.csv), expression ->
#                            action_types. Catalog-authoritative on the 15 reconciled
#                            expressions; the ~189 catalog-gap expressions are gold-only.
#   catalog (training pool): TTL skos:example (split on [・,、]) + multilabel.ttl, exactly
#                            what act_classifiers builds BERT centroids / the LLM prompt from.
#
# Because gold != catalog, the comparison is not circular. Leak can only occur on
# expressions that are in BOTH (the shared set): the fold logic removes each test
# expression from the catalog pools before classifying it. Catalog-gap expressions
# are absent from the catalog to begin with -> a pure, leak-free held-out subset.
# ==========================================================================
def _parse_types(cell):
    return [t.strip() for t in re.split(r"[|;,、/]+", str(cell)) if t.strip()]

def load_gold():
    from rdflib import Graph, URIRef
    from rdflib.namespace import SKOS as SK
    tax = Graph(); tax.parse(TAXONOMY_TTL, format="turtle")
    ml  = Graph(); ml.parse(MULTILABEL_TTL, format="turtle")

    class_examples = defaultdict(set)    # class -> {expr}   (CATALOG training pool)
    descriptor = {}                      # class -> "prefLabel... definition..."
    pref = defaultdict(list)             # class -> [prefLabel strings]

    # The 44 ActionTypes = concepts with skos:broader a category (categories/scheme also
    # carry prefLabel, so we must not treat every prefLabel subject as a class).
    Q_AT = ("PREFIX skos:<http://www.w3.org/2004/02/skos/core#> "
            "SELECT ?c WHERE { ?c skos:broader ?cat }")
    at_uris = sorted({r.c for r in tax.query(Q_AT)}, key=str)
    for c in at_uris:
        local = _ln(c)
        prefs = [str(o) for o in tax.objects(c, SK.prefLabel)]
        defs  = [str(o) for o in tax.objects(c, SK.definition)]
        pref[local] = prefs
        descriptor[local] = " ".join(prefs + defs)
        for ex in tax.objects(c, SK.example):
            for tok in re.split(r"[・,、]", str(ex)):
                tok = normalize(tok)
                if tok:
                    class_examples[local].add(tok)
    # multilabel.ttl: a declared multilabel expr is a catalog example of each of its classes
    P_expr = P_type = None
    for p in set(ml.predicates()):
        ln = str(p).split("#")[-1].split("/")[-1]
        if ln == "expression":   P_expr = p
        if ln == "hasActionType": P_type = p
    for s in ml.subjects(P_expr, None):
        e = normalize(str(next(ml.objects(s, P_expr))))
        for c in (_ln(o) for o in ml.objects(s, P_type)):
            if e:
                class_examples[c].add(e)

    # AFFIX operational note (kept in every fold catalog; a fact, not an expression)
    affix_notes = []
    for sch in {s for s in set(tax.subjects()) if "Scheme" in _ln(s)}:
        for n in tax.objects(sch, URIRef(SKOS + "editorialNote")):
            if "AFFIX" in str(n):
                affix_notes.append(str(n))
    affix_notes = sorted(set(affix_notes))

    classes = sorted(descriptor.keys())              # exactly the 44 ActionTypes
    catalog_exprs = set().union(*class_examples.values()) if class_examples else set()

    # gold from the frozen CSV
    import csv as _csv
    gold = {}
    with open(GOLD_CSV, encoding="utf-8-sig", newline="") as f:
        for row in _csv.DictReader(f):
            e = normalize(row["expression"])
            labs = set(_parse_types(row["action_types"]))
            if e and labs:
                gold[e] = labs
    assert gold, f"no gold rows read from {GOLD_CSV}"
    stray = {l for labs in gold.values() for l in labs} - set(classes)
    assert not stray, f"gold labels not in 44 ActionTypes: {sorted(stray)}"
    return dict(gold), dict(class_examples), descriptor, pref, affix_notes, classes, catalog_exprs


# ==========================================================================
# stratified k-fold  — hand-rolled (no sklearn dep), fully deterministic.
#   strat label per expr = its globally rarest gold class (protects small classes).
#   round-robin assignment of each strat group into folds after a seeded shuffle.
# ==========================================================================
def stratified_folds(gold, n_folds=N_FOLDS, seed=SEED):
    freq = Counter()
    for labs in gold.values():
        for l in labs:
            freq[l] += 1
    strat = {}
    for e, labs in gold.items():
        strat[e] = min(labs, key=lambda l: (freq[l], l))
    groups = defaultdict(list)
    for e, s in strat.items():
        groups[s].append(e)
    rng = random.Random(seed)
    fold_of = {}
    pos = 0                            # global rotating pointer -> balanced fold sizes,
    for s, exprs in sorted(groups.items()):   # stratification preserved (each class spread evenly)
        exprs = sorted(exprs)          # deterministic base order
        rng.shuffle(exprs)
        for e in exprs:
            fold_of[e] = pos % n_folds
            pos += 1
    return fold_of


# ==========================================================================
# BERT fold classifier  — reuses AC.BertCentroid backbone (tok/model/_embed),
# rebuilds centroids per fold from TRAIN examples only.
# ==========================================================================
class FoldBert:
    def __init__(self, backbone, descriptor, pref):
        self.bb = backbone                 # an AC.BertCentroid instance (model+tok loaded)
        self.descriptor = descriptor
        self.pref = pref
        self._emb_cache = {}

    def _embed_one(self, text):
        if text not in self._emb_cache:
            self._emb_cache[text] = self.bb._embed([normalize(text)])   # [1,dim] normalized
        return self._emb_cache[text]

    def build(self, class_to_train_exprs, mode=BERT_CENTROID_MODE,
              include_label_text=BERT_INCLUDE_LABEL_TEXT):
        import torch
        self.labels, mats = [], []
        for c in sorted(class_to_train_exprs.keys()):
            texts = list(class_to_train_exprs[c])
            if include_label_text and self.descriptor.get(c):
                texts = texts + [self.descriptor[c]]
            if not texts:
                continue
            if mode == "bag":
                vec = self._embed_one(" ".join(texts))            # production-faithful
            else:                                                 # "mean" nearest-centroid
                vs = torch.cat([self._embed_one(t) for t in texts], 0)
                vec = torch.nn.functional.normalize(vs.mean(0, keepdim=True), dim=1)
            self.labels.append(c)
            mats.append(vec)
        self.centroids = torch.cat(mats, 0)                       # [n_class, dim]

    def _sims(self, expr):
        v = self._embed_one(expr)
        return (v @ self.centroids.T).squeeze(0)                  # cosine

    def predict_single(self, expr):                              # top-1, no threshold
        sims = self._sims(expr)
        i = int(self.bb.torch.argmax(sims))
        return [self.labels[i]], float(sims[i])

    def predict_multi(self, expr, topk=BERT_TOPK, threshold=BERT_SIM_THRESHOLD):
        sims = self._sims(expr)
        vals, idx = self.bb.torch.topk(sims, k=min(topk, len(self.labels)))
        labs = [self.labels[i] for i, s in zip(idx.tolist(), vals.tolist()) if s >= threshold]
        return labs, float(vals[0])


# ==========================================================================
# Gemini fold classifier  — reuses AC.GeminiClassifier._call_once transport,
# builds a fold-restricted catalog (TRAIN examples only) + two prompt modes.
# ==========================================================================
class FoldGemini:
    """Wraps AC.GeminiClassifier.

    LLM_CATALOG_MODE == "fixed" (B, simple, current default): uses AC.GeminiClassifier
    AS-IS, loading the real act_llm_catalog.md (the exact same file and prompt as the
    exploratory llm_vs_gold.csv run) -> cache keys match exactly, so those 189 cached
    multi-label answers are reused with ZERO new API calls. Held-out is NOT enforced on
    the LLM side in this mode (catalog is fixed across folds); only BERT is held-out.

    LLM_CATALOG_MODE == "fold" (A, strict): rebuilds a train-only catalog per fold via
    build_fold_catalog and calls the transport directly (bypassing AC's file-based
    catalog and its cache, since the catalog text changes every fold -> no reuse anyway).
    """
    def __init__(self, api_key=None, model=None):
        self.mode = LLM_CATALOG_MODE
        catalog_path, cache_path, variant_model = _resolve_llm_variant()
        if self.mode == "fixed":
            self.gc = AC.GeminiClassifier(catalog_md=catalog_path, api_key=api_key,
                                          model=model or variant_model,
                                          cache_path=cache_path)
        else:
            gc = AC.GeminiClassifier.__new__(AC.GeminiClassifier)
            gc.model   = model or variant_model
            gc.api_key = api_key or AC.GEMINI_API_KEY
            gc.catalog = ""
            if not gc.api_key:
                raise RuntimeError("GEMINI_API_KEY not set")
            self.gc = gc
            self._cache = _load_jsonl_cache(GEMINI_CACHE)

    def set_catalog(self, catalog_text):
        """No-op in 'fixed' mode (catalog is the real act_llm_catalog.md, set once at
        __init__ and never rebuilt). Used every fold in 'fold' mode."""
        if self.mode == "fold":
            self.catalog = catalog_text
            self.gc.catalog = catalog_text
            self._cat_sig = hashlib.sha1(catalog_text.encode("utf-8")).hexdigest()[:12]

    def _call_with_backoff(self, call_fn):
        """Retry only on HTTP 429 with exponential backoff. Any other outcome (success,
        or a non-429 failure) returns immediately -- we never spin on an expression the
        model genuinely can't answer."""
        delay = GEMINI_BACKOFF_BASE
        for attempt in range(GEMINI_MAX_RETRIES):
            try:
                return call_fn()
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < GEMINI_MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, GEMINI_BACKOFF_CAP)
                    continue
                return None                              # give up (non-429, or retries exhausted)
            except Exception:
                return None

    def classify(self, expr, single_label):
        called_api = False
        if self.mode == "fixed":
            key = ("single|" if single_label else "") + self.gc._cache_key(expr)
            cache_hit = key in self.gc._cache
            def call():
                return self.gc.classify(expr, single_label=single_label)
            result = self._call_with_backoff(call)
            labels = result[0] if result else []
            called_api = not cache_hit
        else:
            mode = "single" if single_label else "multi"
            key = f"{mode}|{self._cat_sig}|{normalize(expr)}"
            if key in self._cache:
                return self._cache[key]                  # cache hit -> no sleep, return now
            prompt = self.gc._prompt(expr, single_label=single_label)
            def call():
                return self.gc._call_once(prompt, GEMINI_TEMPERATURE)
            result = self._call_with_backoff(call)
            labels = result if result is not None else []
            if labels:                                   # cache only successes (429s retry next run)
                _append_jsonl_cache(GEMINI_CACHE, key, labels)
                self._cache[key] = labels
            called_api = True
        if single_label and len(labels) > 1:
            labels = labels[:1]            # best-effort reduction; violations logged by caller
        if called_api and GEMINI_RATE_SLEEP:   # only throttle real API calls, never cache hits
            time.sleep(GEMINI_RATE_SLEEP)
        return labels


def _load_jsonl_cache(path):
    cache = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                    cache[o["k"]] = o["v"]
                except Exception:
                    pass
    return cache

def _append_jsonl_cache(path, k, v):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"k": k, "v": v}, ensure_ascii=False) + "\n")


# ==========================================================================
# fold-restricted LLM catalog builder (TRAIN examples only; facts kept)
# ==========================================================================
def build_fold_catalog(classes, pref, descriptor, class_to_train_exprs,
                       affix_notes, include_examples=LLM_INCLUDE_EXAMPLES,
                       include_affix=LLM_INCLUDE_AFFIX):
    out = ["# ACT ActionType Catalog (for LLM classification)\n"]
    if include_affix and affix_notes:
        out.append("\n## Operational notes\n")
        for n in affix_notes:
            out.append(f"- {n}\n")
    out.append("\n## ActionTypes\n")
    for c in classes:
        names = " / ".join(pref.get(c, [])) or c
        line = f"- **{c}** ({names})"
        if include_examples:
            exs = sorted(class_to_train_exprs.get(c, []))
            if exs:
                line += ": " + "・".join(exs)
        out.append(line + "\n")
    return "".join(out)


# ==========================================================================
# metrics  (hand-rolled; no sklearn)
# ==========================================================================
def macro_f1(pairs, classes):
    """pairs: list of (gold_set, pred_set). label-based macro-F1 over `classes`
    (only classes with gold support contribute to the macro average)."""
    tp = Counter(); fp = Counter(); fn = Counter(); support = Counter()
    for g, p in pairs:
        for c in classes:
            ing, inp = (c in g), (c in p)
            if ing: support[c] += 1
            if ing and inp: tp[c] += 1
            elif inp and not ing: fp[c] += 1
            elif ing and not inp: fn[c] += 1
    per = {}
    f1s = []
    for c in classes:
        if support[c] == 0:
            continue
        P = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        R = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        F = 2 * P * R / (P + R) if (P + R) else 0.0
        per[c] = {"P": round(P, 4), "R": round(R, 4), "F1": round(F, 4),
                  "support": support[c]}
        f1s.append(F)
    return (sum(f1s) / len(f1s) if f1s else 0.0), per

def micro_accuracy(pairs):
    """exact single-label match (both sides singletons)."""
    ok = sum(1 for g, p in pairs if g == p)
    return ok / len(pairs) if pairs else 0.0

def example_based_f1(pairs):
    """mean per-expression Dice overlap 2|P∩G|/(|P|+|G|)."""
    vals = []
    for g, p in pairs:
        if not g and not p:
            vals.append(1.0); continue
        inter = len(g & p)
        denom = len(g) + len(p)
        vals.append(2 * inter / denom if denom else 0.0)
    return sum(vals) / len(vals) if vals else 0.0


# ==========================================================================
# evaluation driver
# ==========================================================================
def _bert_cache_key():
    return f"seed{SEED}|folds{N_FOLDS}|{BERT_CENTROID_MODE}|label{int(BERT_INCLUDE_LABEL_TEXT)}"


def _load_bert_cache():
    """Return {expr: {"multi":[labels], "multi_sim":float, "single":[labels],
    "single_sim":float, "is_gap":bool}} for the CURRENT config key, or {} if the
    cache file is absent/for a different config (fold split, centroid mode, etc.)."""
    if not os.path.exists(BERT_CACHE):
        return {}
    try:
        with open(BERT_CACHE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if data.get("key") != _bert_cache_key():
        return {}   # stale (different seed/folds/centroid mode) -> recompute
    return data.get("predictions", {})


def _save_bert_cache(predictions):
    BERT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(BERT_CACHE, "w", encoding="utf-8") as f:
        json.dump({"key": _bert_cache_key(), "predictions": predictions}, f, ensure_ascii=False)


def run(use_bert, use_llm, centroid_mode, dump_predictions=False):
    gold, class_examples, descriptor, pref, affix_notes, classes, catalog_exprs = load_gold()
    fold_of = stratified_folds(gold)
    all_exprs = sorted(gold.keys())
    single_only = {e for e, v in gold.items() if len(v) == 1}
    gap = {e for e in all_exprs if e not in catalog_exprs}   # catalog-gap: pure held-out

    print(f"gold expressions: {len(all_exprs)}  (single-label {len(single_only)}, "
          f"multi {len(all_exprs)-len(single_only)}) | classes {len(classes)} | "
          f"folds {N_FOLDS} seed {SEED}")
    print(f"catalog training exprs: {len(catalog_exprs)} | catalog-gap (pure held-out) gold exprs: {len(gap)}")
    if use_bert:
        print(f"BERT centroid mode: {centroid_mode}")
    if use_llm:
        _cat_path, _cache_path, _model = _resolve_llm_variant()
        print(f"LLM variant: {LLM_VARIANT}  (catalog={_cat_path}, cache={_cache_path}, "
              f"model={_model})")
        print(f"LLM catalog mode: {LLM_CATALOG_MODE}"
              + ("  (fixed catalog, no per-fold held-out on LLM side)" if LLM_CATALOG_MODE == "fixed"
                 else "  (rebuilt per fold, held-out enforced)"))

    # backbones (loaded once, reused across folds)
    bert = gem = None
    bert_cache = _load_bert_cache() if use_bert else {}
    bert_cache_hit = use_bert and bert_cache and all(e in bert_cache for e in all_exprs)
    if use_bert:
        if bert_cache_hit:
            print(f"BERT predictions cache HIT ({BERT_CACHE}, key={_bert_cache_key()}) "
                  f"-> skipping model load and fold rebuilds entirely")
        else:
            backbone = AC.BertCentroid()                 # loads Tohoku BERT once
            bert = FoldBert(backbone, descriptor, pref)
    if use_llm:
        gem = FoldGemini()

    # pooled out-of-fold predictions
    pool = {"bert_single": [], "bert_multi": [], "llm_single": [], "llm_multi": []}
    bert_abstain = 0
    llm_single_violations = 0

    rows_single = []   # for --dump-predictions: (expr, gold, bert_pred, llm_pred, is_gap)
    new_bert_cache = {}   # populated only on a cache MISS; saved to BERT_CACHE after all folds

    for f in range(N_FOLDS):
        test = [e for e in all_exprs if fold_of[e] == f]
        train = [e for e in all_exprs if fold_of[e] != f]
        test_set = set(test)

        # per-class CATALOG pools with ONLY the held-out test expressions removed.
        # (Catalog exprs that are not gold — English glosses, non-gold JA examples —
        #  are never in test, so they correctly stay in the training pool.)
        c2train = defaultdict(set)
        for c, exs in class_examples.items():
            keep = exs - test_set
            if keep:
                c2train[c] = keep

        if use_bert and not bert_cache_hit:
            bert.build(c2train, mode=centroid_mode)
        if use_llm and LLM_CATALOG_MODE == "fold":       # "fixed" mode: catalog set once at init
            cat = build_fold_catalog(classes, pref, descriptor, c2train, affix_notes)
            gem.set_catalog(cat)

        for ti, e in enumerate(test):
            g = gold[e]
            is_gap = e in gap
            bs_for_dump = ls_for_dump = None
            if use_bert:
                if bert_cache_hit:
                    entry = bert_cache[e]
                    labs_m = entry["multi"]
                else:
                    labs_m, _ = bert.predict_multi(e)
                if not labs_m:
                    bert_abstain += 1
                pool["bert_multi"].append((g, set(labs_m), is_gap))
                if e in single_only:
                    if bert_cache_hit:
                        labs_s = bert_cache[e]["single"]
                    else:
                        labs_s, _ = bert.predict_single(e)
                    pool["bert_single"].append((g, set(labs_s), is_gap))
                    bs_for_dump = labs_s
                if not bert_cache_hit:
                    new_bert_cache[e] = {"multi": labs_m,
                                         "single": bs_for_dump if e in single_only else []}
            if use_llm:
                labs_m = gem.classify(e, single_label=False)
                pool["llm_multi"].append((g, set(labs_m), is_gap))
                if e in single_only:
                    labs_s = gem.classify(e, single_label=True)
                    if len(labs_s) != 1:
                        llm_single_violations += 1
                    pool["llm_single"].append((g, set(labs_s), is_gap))
                    ls_for_dump = labs_s
            if e in single_only:
                rows_single.append((e, sorted(g), bs_for_dump, ls_for_dump, is_gap))
            if use_llm and (ti + 1) % 10 == 0:
                print(f"    fold {f}: {ti+1}/{len(test)} expressions done "
                      f"(last: {e!r})", flush=True)
        print(f"  fold {f}: test={len(test)} train={len(train)}  done")

    if use_bert and not bert_cache_hit:
        _save_bert_cache(new_bert_cache)
        print(f"saved BERT predictions cache -> {BERT_CACHE} "
              f"({len(new_bert_cache)} exprs, key={_bert_cache_key()})")

    # ---- score ----
    results = {"config": {"n_folds": N_FOLDS, "seed": SEED,
                          "centroid_mode": centroid_mode,
                          "llm_include_examples": LLM_INCLUDE_EXAMPLES,
                          "llm_catalog_mode": LLM_CATALOG_MODE,
                          "llm_variant": LLM_VARIANT,
                          "gold_csv": GOLD_CSV},
               "n_expr": len(all_exprs), "n_single": len(single_only),
               "n_catalog_gap": len(gap)}

    def _strip(pairs, gap_only=False):
        return [(g, p) for (g, p, isg) in pairs if (isg or not gap_only)]

    def block(single_pairs3, multi_pairs3):
        def sub(single3, multi3):
            sp, mp = _strip(single3), _strip(multi3)
            macro_s, per_s = macro_f1(sp, classes) if sp else (None, {})
            macro_m, per_m = macro_f1(mp, classes) if mp else (None, {})
            return {"single_macro_f1": macro_s, "single_accuracy": micro_accuracy(sp) if sp else None,
                    "single_per_class": per_s, "n_single": len(sp),
                    "multi_example_f1": example_based_f1(mp) if mp else None,
                    "multi_macro_f1": macro_m, "multi_per_class": per_m, "n_multi": len(mp)}
        out = sub(single_pairs3, multi_pairs3)                       # overall (all 574)
        out["catalog_gap"] = sub([x for x in single_pairs3 if x[2]], # pure held-out (~189)
                                 [x for x in multi_pairs3  if x[2]])
        return out

    if use_bert:
        results["no_llm_bert"] = block(pool["bert_single"], pool["bert_multi"])
        results["no_llm_bert"]["abstain_multi"] = bert_abstain
    if use_llm:
        results["llm_gemini"] = block(pool["llm_single"], pool["llm_multi"])
        results["llm_gemini"]["single_label_violations"] = llm_single_violations

    _write_outputs(results, use_bert, use_llm)
    _print_summary(results, use_bert, use_llm)

    if dump_predictions:
        _dump_predictions(rows_single, use_bert, use_llm)

    return results


def _dump_predictions(rows_single, use_bert, use_llm):
    """Write predictions_single[_<variant>].csv (one row per single-label gold expression,
    pooled out-of-fold) and print the subset where BOTH methods disagree with gold -- the
    review list requested for human inspection before touching gold/catalog."""
    import csv as _csv
    suf = _out_suffix(use_llm)
    pred_path = DATA_DIR / f"predictions_single{suf}.csv"   # lists expressions: not public
    wrong_path = DATA_DIR / f"both_wrong{suf}.csv"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(pred_path, "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["expression", "gold", "bert_pred", "llm_pred", "catalog_gap"])
        for e, g, bp, lp, is_gap in rows_single:
            w.writerow([e, "|".join(g),
                       "|".join(bp) if bp is not None else "",
                       "|".join(lp) if lp is not None else "",
                       is_gap])
    print(f"\nwrote {pred_path} ({len(rows_single)} single-label expressions)")

    if use_bert and use_llm:
        both_wrong = []
        for e, g, bp, lp, is_gap in rows_single:
            if bp is None or lp is None:
                continue
            gset = set(g)
            if set(bp) != gset and set(lp) != gset:
                both_wrong.append((e, g, bp, lp, is_gap))
        print(f"\n両手法ともgoldと不一致: {len(both_wrong)}/{len(rows_single)} "
              f"({len(both_wrong)/len(rows_single):.0%})\n")
        print(f"{'expression':<14}{'gold':<24}{'BERT':<24}{'LLM':<24}gap")
        print("-" * 90)
        for e, g, bp, lp, is_gap in sorted(both_wrong):
            print(f"{e:<14}{'|'.join(g):<24}{'|'.join(bp):<24}{'|'.join(lp):<24}{is_gap}")
        with open(wrong_path, "w", encoding="utf-8-sig", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["expression", "gold", "bert_pred", "llm_pred", "catalog_gap"])
            for e, g, bp, lp, is_gap in sorted(both_wrong):
                w.writerow([e, "|".join(g), "|".join(bp), "|".join(lp), is_gap])
        print(f"\nwrote {wrong_path} ({len(both_wrong)} rows)")


def _print_summary(r, use_bert, use_llm):
    print("\n==================== SUMMARY ====================")
    print(f"expressions {r['n_expr']} (single {r['n_single']}) | "
          f"folds {r['config']['n_folds']} seed {r['config']['seed']}")
    def row(tag, b):
        sm = f"{b['single_macro_f1']*100:5.1f}" if b['single_macro_f1'] is not None else "  -  "
        sa = f"{b['single_accuracy']*100:5.1f}" if b['single_accuracy'] is not None else "  -  "
        ex = f"{b['multi_example_f1']*100:5.1f}" if b['multi_example_f1'] is not None else "  -  "
        mm = f"{b['multi_macro_f1']*100:5.1f}" if b['multi_macro_f1'] is not None else "  -  "
        print(f"  {tag:16} single-MacroF1 {sm}  acc {sa}   | multi exF1 {ex}  MacroF1 {mm}")
    print(f"  {'method':16} {'HEADLINE (single-label)':>28}   {'AUX (multilabel)':>24}")
    if use_bert: row("no-LLM (BERT)", r["no_llm_bert"])
    if use_llm:  row("LLM (Gemini)",  r["llm_gemini"])
    print(f"\n  --- catalog-gap subset (pure held-out, n_single={r['no_llm_bert']['catalog_gap']['n_single'] if use_bert else r['llm_gemini']['catalog_gap']['n_single']}) ---")
    if use_bert: row("no-LLM (BERT)", r["no_llm_bert"]["catalog_gap"])
    if use_llm:  row("LLM (Gemini)",  r["llm_gemini"]["catalog_gap"])
    if use_bert and use_llm:
        d = r["llm_gemini"]["single_macro_f1"] - r["no_llm_bert"]["single_macro_f1"]
        print(f"\n  LLM lift on headline single-label Macro-F1: {d*100:+.1f} points")
    print("=================================================\n")


def _out_suffix(use_llm):
    """Filename suffix so baseline vs withdef runs (or bert-only runs) never overwrite
    each other. Empty for bert-only (unchanged filenames, backward compatible)."""
    return f"_{LLM_VARIANT}" if use_llm else ""


def _write_outputs(results, use_bert, use_llm):
    suf = _out_suffix(use_llm)
    out_json = OUT_JSON.with_name(f"{OUT_JSON.stem}{suf}.json")
    out_report = OUT_REPORT.with_name(f"{OUT_REPORT.stem}{suf}.md")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    llm_note = ""
    if use_llm:
        if results["config"]["llm_catalog_mode"] == "fold":
            llm_note = " and the LLM prompt catalog (both methods fully held-out)."
        else:
            llm_note = (
                f" only -- LLM uses a FIXED catalog (variant={results['config']['llm_variant']}), "
                "not rebuilt per fold, so held-out is not enforced on the LLM side "
                "(current design choice)."
            )

    lines = ["# ACT Phase 2 — expression-level classifier evaluation\n",
             f"\n- expressions: {results['n_expr']} (single-label {results['n_single']})",
             f"\n- protocol: {results['config']['n_folds']}-fold stratified CV, "
             f"seed {results['config']['seed']}, catalog OFF (method comparison); "
             f"held-out propagated into BERT centroids" + llm_note,
             f"\n- BERT centroid mode: {results['config']['centroid_mode']}\n",
             "\n## Headline — single-label track (label-based Macro-F1)\n",
             "\n| method | Macro-F1 | accuracy |\n|---|---|---|\n"]
    if use_bert:
        b = results["no_llm_bert"]
        lines.append(f"| no-LLM (BERT centroid) | {b['single_macro_f1']*100:.1f} | "
                     f"{b['single_accuracy']*100:.1f} |\n")
    if use_llm:
        b = results["llm_gemini"]
        lines.append(f"| LLM (Gemini, variant={results['config']['llm_variant']}) | "
                     f"{b['single_macro_f1']*100:.1f} | {b['single_accuracy']*100:.1f} |\n")
    lines.append("\n## Auxiliary — multilabel track\n")
    lines.append("\n| method | example-based F1 | Macro-F1 |\n|---|---|---|\n")
    if use_bert:
        b = results["no_llm_bert"]
        lines.append(f"| no-LLM (BERT centroid) | {b['multi_example_f1']*100:.1f} | "
                     f"{b['multi_macro_f1']*100:.1f} |\n")
    if use_llm:
        b = results["llm_gemini"]
        lines.append(f"| LLM (Gemini, variant={results['config']['llm_variant']}) | "
                     f"{b['multi_example_f1']*100:.1f} | {b['multi_macro_f1']*100:.1f} |\n")
    lines.append(f"\n_Per-class tables are in {out_json.name}._\n")
    open(out_report, "w", encoding="utf-8").write("".join(lines))
    print(f"\nwrote {out_report}, {out_json}")


# ==========================================================================
# offline self-test: verify the scoring math on a tiny synthetic case
# ==========================================================================
def _selftest():
    print("scoring self-test (hand-computable):")
    classes = ["A", "B", "C"]
    # single-label pairs
    sp = [({"A"}, {"A"}),   # TP A
          ({"A"}, {"B"}),   # FN A, FP B
          ({"B"}, {"B"}),   # TP B
          ({"C"}, {"A"})]   # FN C, FP A
    # A: tp1 fp1 fn1 -> P .5 R .5 F .5 ; B: tp1 fp1 fn0 -> P .5 R 1 F .667 ;
    # C: tp0 fp0 fn1 -> P0 R0 F0 ; macro=(.5+.667+0)/3=.389
    m, per = macro_f1(sp, classes)
    acc = micro_accuracy(sp)
    print(f"  single macro-F1={m:.3f} (expect 0.389)  acc={acc:.3f} (expect 0.500)")
    assert abs(m - 0.3889) < 1e-3 and abs(acc - 0.5) < 1e-9

    # multilabel example-based F1
    mp = [({"A", "B"}, {"A", "B"}),   # dice 1.0
          ({"A", "B"}, {"A"}),        # dice 2*1/3 = .667
          ({"A"}, {"B"}),             # dice 0
          (set(), set())]             # dice 1.0
    ex = example_based_f1(mp)         # (1 + .667 + 0 + 1)/4 = .667
    print(f"  example-based F1={ex:.3f} (expect 0.667)")
    assert abs(ex - 0.6667) < 1e-3

    # fold determinism + no-leak invariant on the real gold/catalog
    gold, class_examples, descriptor, pref, affix, classes, catalog_exprs = load_gold()
    f1 = stratified_folds(gold); f2 = stratified_folds(gold)
    assert f1 == f2, "folds not deterministic"
    sizes = Counter(f1.values())
    print(f"  gold {len(gold)} | catalog exprs {len(catalog_exprs)} | "
          f"catalog-gap {len([e for e in gold if e not in catalog_exprs])}")
    print(f"  fold sizes: {dict(sorted(sizes.items()))}  (n={sum(sizes.values())})")

    # pick a SHARED sample (gold expr that is also in the catalog) so removal is meaningful
    shared = [e for e in sorted(gold) if e in catalog_exprs]
    sample = shared[0]
    tf = f1[sample]
    test_set = {e for e, k in f1.items() if k == tf}
    # rebuild the fold's catalog pools with the new rule (remove only test exprs)
    c2train = defaultdict(set)
    for c, exs in class_examples.items():
        keep = exs - test_set
        if keep: c2train[c] = keep
    leaked = any(sample in pool for pool in c2train.values())
    assert not leaked, "held-out (shared) expr leaked into a train pool"
    cat = build_fold_catalog(classes, pref, descriptor, c2train, affix)
    assert ("・" + sample not in cat) and (sample + "・" not in cat) and \
           (": " + sample not in cat.replace("\n", "")), "held-out expr present in fold catalog"
    # catalog-gap exprs are absent from catalog pools by construction (sanity)
    gap = [e for e in gold if e not in catalog_exprs]
    assert gap, "expected a non-empty catalog-gap subset"
    assert all(g not in set().union(*class_examples.values()) for g in gap[:20])
    print(f"  no-leak invariant OK (shared sample {sample!r} removed from fold {tf}); "
          f"gap subset non-empty ({len(gap)})")
    print("ALL SELF-TESTS PASSED")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="offline scoring/leak checks")
    ap.add_argument("--bert", action="store_true", help="run no-LLM BERT method")
    ap.add_argument("--llm",  action="store_true", help="run LLM Gemini method")
    ap.add_argument("--centroid-mode", choices=["mean", "bag"], default=BERT_CENTROID_MODE)
    ap.add_argument("--llm-variant", choices=["baseline", "withdef"], default=LLM_VARIANT,
                    help="which LLM catalog/cache/model-tag set to use (see _LLM_VARIANT_CONFIG)")
    ap.add_argument("--dump-predictions", action="store_true",
                    help="write predictions_single.csv and both_wrong.csv "
                         "(rows where BOTH bert and llm disagree with gold)")
    a = ap.parse_args()
    LLM_VARIANT = a.llm_variant
    if a.selftest or not (a.bert or a.llm):
        _selftest()
    else:
        run(use_bert=a.bert, use_llm=a.llm, centroid_mode=a.centroid_mode,
            dump_predictions=a.dump_predictions)