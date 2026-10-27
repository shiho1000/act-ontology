"""
act_etl.py

Pipeline:  CSV exported from the COTEN History DB (long format, one row per event-entity link)
             -> group the rows by event
             -> classify each distinct action expression (act_classifiers.py:
                lookup index -> LLM + BERT centroid, with confidence and band)
             -> entity resolution (Compound Record -> Wikidata -> COTEN entity ID;
                otherwise literal fallback) and entity linking (owl:sameAs to Wikidata)
             -> ACT Turtle output

Design decisions:
  * The classification unit is the distinct action *expression* (type-level). The label
    of the event is NOT read by the classifier. Classification with context is future work.
  * Entity identity is deterministic: canonical URI = entity_<base32(sha1(key))[:8]>.
    The COTEN entity ID (Dewey) is used only as a key and is never written to the graph.
    Wikidata IDs are always written as owl:sameAs. Participants without any identifier
    keep their names as has*Label literals (no name-based merging).
  * hasActionType is 0..* (multilabel). Confidence and band are written to the review CSV.
    RDF-star annotations are available but off by default (EMIT_RDF_STAR_ANNOTATIONS).
  * Python standard library only in this file; act_classifiers.py needs rdflib, and
    torch/transformers for the BERT classifier.

============================================================================
Steps for running the pipeline
============================================================================

0. Repository layout. The scripts find their input files from their own location,
   so they run from any working directory:

     act_ontology.ttl, act_taxonomy.ttl, act_multilabel.ttl   (repository top)
     pipeline/act_etl.py           this file
     pipeline/act_classifiers.py   the classification cascade. If it is missing,
                                   the import fails and classify_action() falls back
                                   to an empty stub, so the graph carries no action types.
     artifacts/act_llm_catalog.md  produced by pipeline/generate_artifacts.py
     cache/llm_cache.jsonl         created on the first run. Keep an existing cache
                                   here to reuse earlier answers of the LLM.

   To use files elsewhere, set the environment variables ACT_TAXONOMY_TTL,
   ACT_MULTILABEL_TTL, ACT_LLM_CATALOG_MD or ACT_LLM_CACHE.

1. Gemini API key (only for classification with the LLM; without it, the pipeline
   runs with the lookup index and the BERT classifier):
     export GEMINI_API_KEY="xxxxxxxx"        # macOS/Linux
     set GEMINI_API_KEY=xxxxxxxx             # Windows (cmd)
     $env:GEMINI_API_KEY = "xxxxxxxx"        # Windows (PowerShell)
   act_classifiers.py reads the variable when it is imported, so set it in the shell
   before starting act_etl.py. Do not write the key into the code.

2. Check the input before each new corpus or new export from the COTEN History DB:
   a. COLUMN_MAP (around line 60 of this file): if the headers of the CSV change,
      update the right-hand side.
   b. DECLARED_CLASSES / CATEGORY_COLLAPSE (just before category_to_class): unknown
      categories in a new corpus raise cat_degraded / cat_no_class warnings. With
      CATEGORY_INVENTORY = True, category_inventory.csv lists every category, so you
      can decide whether to add it to DECLARED_CLASSES.
   The path of the input CSV is a command-line argument, so this file needs no edit.

3. Commands:
     # First full run
     python pipeline/act_etl.py path/to/corpus.csv out/corpus_data.ttl

     # Main outputs, written next to out_ttl:
     #   corpus_data.ttl                         the knowledge graph
     #   category_inventory.csv                  when CATEGORY_INVENTORY = True
     #   name_category_review.csv                when QA_REPORT = True
     #   corpus_data_classification_review.csv   when CLASSIFICATION_REVIEW_CSV = True
     #     (sorted by confidence, lowest first; the labels column can be edited by hand)

     # After editing the review file, run again with the corrections:
     python pipeline/act_etl.py path/to/corpus.csv out/corpus_data.ttl \
         --apply-review out/corpus_data_classification_review.csv
     # With --apply-review, the labels in the file take precedence over
     # classify_action() for the expressions they cover (confidence = 1.0,
     # band = "human"). This second run gives the final graph.

4. Settings in this file (the defaults suit most corpora; change them only with a reason):
     EMIT_PATIENT_OF_BRIDGE     usually False. True when you extract part of a corpus.
     KEY_PRIORITY               "wikidata" (recommended). Despite the name, the key order
                                is Compound Record, then Wikidata, then the COTEN entity
                                ID. Changed in 2026-08, because Wikidata IDs vary
                                within a Compound Record. Wikidata IDs are always recorded
                                with owl:sameAs.
                                "dewey" keeps one node per mention without merging (for
                                diagnosis).
     QA_REPORT / CATEGORY_INVENTORY / CLASSIFICATION_REVIEW_CSV   usually True.
     EMIT_RDF_STAR_ANNOTATIONS  usually False. True only to query the confidence of each
                                triple with SPARQL.
   Settings in act_classifiers.py:
     USE_LLM / USE_BERT         switch the LLM or the BERT classifier on or off
                                (for example, for an evaluation without the LLM).
     GEMINI_MODEL               replace the model if the current one returns 404 or hits
                                the rate limit too often.

============================================================================
"""

import csv
import sys
import re
import hashlib
import base64
from pathlib import Path
from collections import defaultdict

# ==========================================================================
# CONFIG  — everything corpus/naming-specific lives here.
# ==========================================================================

# --- Namespaces -----------------------------------------------------------
ACT  = "https://w3id.org/act/ontology#"
AT   = "https://w3id.org/act/taxonomy#"
DATA = "https://w3id.org/act/data#"          # minted individuals (events, entities)
WD   = "http://www.wikidata.org/entity/"

PREFIXES = {
    "act":  ACT,
    "at":   AT,
    "":     DATA,          # default namespace = minted resources
    "owl":  "http://www.w3.org/2002/07/owl#",
    "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd":  "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "wd":   WD,
}

# --- COLUMN_MAP: logical name  <->  actual CSV header ----------------------
# Change ONLY the right-hand side if COTEN renames columns upstream.
COLUMN_MAP = {
    "event_id":        "EVENT_ENTITY_ID",
    "event_compound":  "EVENT_COMPOUND_ID",     # 2026-08 追加: イベント自身のCompound Record ID
                                                 #   （書籍横断でのEvent統合キー。無ければevent_idのまま）
    "event_label":     "TITLE",
    "event_category":  "CATEGORY",
    "start_date":      "START_DATE",
    "end_date":        "END_DATE",
    "action":          "ACTION",
    "role":            "ROLE",
    "linked_name":     "LINKED_NAME",
    "linked_category": "LINKED_CATEGORY",
    "linked_dewey":    "LINKED_ENTITY_ID",
    "linked_compound": "LINKED_COMPOUND_ID",   # 2026-08 追加: COTEN Compound Record ID
    "linked_wikidata": "LINKED_WIKIDATA_ID",
    "parent_event":    "PARENT_EVENT_ID",       # optional (may be absent in old data)
    "child_event":     "CHILD_EVENT_ID",        # optional
    "patient_of":      "PATIENT_OF_EVENT_ID",   # optional
    "reference_id":    "REFERENCE_ID",
    "reference_title": "REFERENCE_TITLE",
}

# --- Optional SRL literal columns:  CSV header -> ACT datatype property ----
# Rule: emit a literal iff a value is present; otherwise no triple at all.
OPTIONAL_LIT_COLS = {
    "CAUSE":       "hasCause",
    "INSTRUMENT":  "hasInstrument",
    "MANNER":      "hasManner",
    "PURPOSE":     "hasPurpose",
    "PROBABILITY": "hasProbability",
}

# --- Role routing ---------------------------------------------------------
# agent / place / territory route directly. patient is special: it is split
# into hasPatient (Actor u Space) vs hasTheme (Event u Thing) by category.
ROLE_TO_PROP = {
    "agent":     "hasAgent",
    "place":     "hasPlace",
    "territory": "hasTerritory",
}
PATIENT_SPLIT_BY_TOPCAT = {
    "actor": "hasPatient",
    "space": "hasPatient",
    "event": "hasTheme",
    "thing": "hasTheme",
}

# --- Literal fallback (Entity resolution failure) -------------------------
# NOTE: hasPlaceLabel / hasTerritoryLabel must be ADDED to the ontology (Layer 1 TODO).
PROP_TO_LABEL_PROP = {
    "hasAgent":     "hasAgentLabel",
    "hasPatient":   "hasPatientLabel",
    "hasTheme":     "hasThemeLabel",
    "hasPlace":     "hasPlaceLabel",
    "hasTerritory": "hasTerritoryLabel",
}

# --- Entity classes declared in ACT v1.0 (for longest-prefix cat mapping) -
DECLARED_CLASSES = {
    "Entity", "Event", "EventDispute",
    "EventHazard", "EventMobility",          # EventConcept/EventArtifact abolished (see CATEGORY_COLLAPSE)
    "Actor", "ActorPerson", "ActorGroup", "ActorGroupPolity", "ActorGroupPolityDynasty",
    "Space", "SpacePlace",
    "Thing", "ThingArtifact", "ThingConcept",
    "Reference",
}

# --- Deliberate category collapses (NOT degrades; suppressed from cat_degraded) ---
# COTEN abolished event.{toponym,actor,artifact,concept,place}; those records now stop at
# the parent level (ctn.event) to avoid duplication with the normalized entity layer.
# ACT maps all of them straight to :Event, silently (they are intended, not fallbacks).
CATEGORY_COLLAPSE = {
    "event.toponym":  "Event",
    "event.actor":    "Event",
    "event.artifact": "Event",
    "event.concept":  "Event",
    "event.place":    "Event",
}

# --- Behaviour flags ------------------------------------------------------
EMIT_PATIENT_OF_BRIDGE = False   # emit event-event link from PATIENT_OF_EVENT_ID.
                                # Set False if EVENT/ENTITY id spaces are unified
                                # CONFIRMED redundant on full-corpus runs: the forward
                                # ROLE=patient row already links it (id spaces unified).
                                # Enable only for partial slices to maximize coverage.
KEY_PRIORITY = "wikidata"       # "wikidata" (dedupe real-world entities: COTEN Compound Record
                                #   ID first, then Wikidata QID, then raw Dewey id as last
                                #   resort) or "dewey" (keep COTEN mention-level granularity;
                                #   Compound Record dedup is intentionally skipped in this mode).
                                # Event-typed entities ALWAYS key on their uuid so that an
                                # event referenced as a participant unifies with its own node.
                                # 2026-08 design decision (revised): Compound Record now
                                # outranks Wikidata. Rationale: Compound Record IDs are
                                # confirmed stable across corpora/books (same person -> same
                                # Compound Record regardless of which book's export you're
                                # looking at), but Wikidata QID coverage is PATCHY EVEN WITHIN
                                # a single Compound Record -- i.e. some mentions belonging to
                                # the same already-merged real-world entity carry a QID and
                                # others don't. Keying on Wikidata first would then split that
                                # single Compound Record back into >1 URI whenever a QID is
                                # missing on some rows. Wikidata is still recorded via
                                # owl:sameAs regardless of which tier wins the URI, so no LOD
                                # grounding is lost by this reordering.
QA_REPORT = True                # write name<->category mismatch review CSV.
CATEGORY_INVENTORY = True       # write a full category census (category x count x
                                # mapped ACT class x degraded?) — the tool for
                                # reviewing a NEW corpus before extending DECLARED_CLASSES.

# --- ActionType classification: score visibility vs. KG size (2026-08 decision) -----
# classify_action() always computes confidence/band/signals regardless of these flags;
# the two flags below only control WHERE that information ends up.
EMIT_RDF_STAR_ANNOTATIONS = False  # Attach source/confidence/band/catalogHit/bertAgree
                                   # to each hasActionType triple via RDF-star. OFF by
                                   # default: keeps the production KG lean (no per-
                                   # assignment annotation triples). The classification
                                   # logic and its scores are unaffected either way --
                                   # flip to True to re-enable full RDF-star provenance
                                   # in the KG itself (e.g. for a corpus where per-triple
                                   # confidence needs to be SPARQL-queryable).
CLASSIFICATION_REVIEW_CSV = True   # write <out_ttl>_classification_review.csv: one row
                                   # per Action expression with its labels, confidence,
                                   # band, and signals -- sorted by confidence ascending
                                   # so low-confidence assignments surface first. This is
                                   # how confidence stays inspectable even with RDF-star
                                   # annotations OFF. A human can edit the `labels` column
                                   # directly; re-running with --apply-review (see main())
                                   # overrides classify_action()'s output with the edited
                                   # labels for those expressions before KG generation.
                                   # Set False to skip the review step entirely.

# ==========================================================================
# Helpers
# ==========================================================================

_warnings = defaultdict(int)

def warn(kind, detail=""):
    _warnings[kind] += 1
    if _warnings[kind] <= 5:   # cap noise; count is reported at the end
        print(f"  [warn:{kind}] {detail}", file=sys.stderr)


def local_id(raw_key: str, prefix="entity_") -> str:
    """Deterministic canonical local name from any stable id (Dewey/Wikidata/event)."""
    h = hashlib.sha1(raw_key.encode("utf-8")).digest()
    b32 = base64.b32encode(h).decode("ascii").lower().rstrip("=")
    return prefix + b32[:8]


def event_uri(eid: str, compound: str = "") -> str:
    """Deterministic URI for an EVENT's own primary node. 2026-08 addition: events, like
    Actor/Space/Thing, can have a COTEN Compound Record ID (EVENT_COMPOUND_ID) that is
    stable ACROSS books -- unlike event_id, which COTEN assigns per-book (the same
    real-world event described in two different corpora gets two different event_ids).
    Without this, "Napoleon's Egyptian campaign" described in both sekaishizuroku AND
    nihonshizuroku would end up as two separate Event nodes, exactly the mention-level
    fragmentation problem Compound Record already solves for Actor/Space/Thing.
    Every place that builds an Event's URI (the event's own node, an event-typed link in
    entity_uri_and_triples(), and hasSubEvent/hasTheme cross-references below) MUST go
    through this one function so they agree on the same URI for the same event."""
    eid = (eid or "").strip()
    compound = (compound or "").strip()
    if KEY_PRIORITY == "wikidata" and compound:
        return ":" + local_id("cpd:" + compound)
    return ":" + local_id(eid)


def category_to_class(cat: str) -> str:
    """Map a dotted COTEN category to the deepest declared ACT class.
    e.g. thing.concept.order -> ThingConcept ; event.mobility.migration -> Event.
    Deliberate COTEN collapses (event.{toponym,actor,artifact,concept,place}) go to
    :Event silently via CATEGORY_COLLAPSE (not counted as a degrade)."""
    if not cat:
        return "Entity"
    head2 = ".".join(cat.split(".")[:2])
    if head2 in CATEGORY_COLLAPSE:              # intended abolition -> parent, no warning
        return CATEGORY_COLLAPSE[head2]
    parts = cat.split(".")
    while parts:
        cand = "".join(p.capitalize() for p in parts)
        if cand in DECLARED_CLASSES:
            full = "".join(p.capitalize() for p in cat.split("."))
            if cand != full:                       # e.g. EventMobilityMigration -> Event
                warn("cat_degraded", f"{cat} -> {cand}")
            return cand
        parts = parts[:-1]
    warn("cat_no_class", cat)
    return "Entity"


def top_cat(cat: str) -> str:
    return cat.split(".")[0] if cat else ""


def esc_literal(s: str) -> str:
    return (s.replace("\\", "\\\\").replace('"', '\\"')
             .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


def lit(s: str, lang="ja") -> str:
    return f'"{esc_literal(s)}"@{lang}' if lang else f'"{esc_literal(s)}"'


# --- GDTF (COTEN Genealogical Date Text Format) parser --------------------
# COTEN stores dates as structured free text, not SQL DATE. Policy:
#   * startDateRaw/endDateRaw : ALWAYS emitted (lossless xsd:string).
#   * startYear/endYear       : ALWAYS emitted when a year is derivable
#                               (integer; range/wildcard use the LOWER bound). Range-query anchor.
#   * startDate/endDate        : typed xsd:gYear / gYearMonth / date, emitted ONLY for a
#                               clean, exact single point (year/month/day). BCE (negative)
#                               is a valid gYear. Range [], wildcard x, circa ~, approx % ->
#                               NO typed date.
#   * startDateApproximate/... : boolean true for ~ % [] x (uncertain / not an exact point).
#                               Open intervals ( X/ , /X ) are NOT approximate (the known
#                               endpoint is exact); the slash position sets which side.
# START_DATE and END_DATE are separate cells; a slash's position (X/ -> start, /X -> end)
# overrides which column a value came from.

def _g(y: int) -> str:
    """Canonical xsd:gYear lexical form (>=4 digits, leading zeros; BCE negative)."""
    return f"-{abs(y):04d}" if y < 0 else f"{y:04d}"


def _parse_point(core: str):
    """One date token (slash/openness already stripped) -> (year|None, typed|None, approx)."""
    core = (core or "").strip()
    if not core:
        return (None, None, False)
    approx = ("~" in core) or ("%" in core)
    c = core.replace("~", "").replace("%", "").strip()

    m = re.match(r"^\[\s*(-?\d{1,4})\s*\.\.\s*(-?\d{1,4})\s*\]$", c)      # [a..b] range
    if m:
        return (int(m.group(1)), None, True)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(-?\d{3,4})$", c)                 # M/D/Y
    if m:
        mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (yr, None if approx else f'"{_g(yr)}-{mo:02d}-{dy:02d}"^^xsd:date', approx)
    m = re.match(r"^(-?)(\d{1,4})-(\d{2})-(\d{2})$", c)                   # ISO date
    if m:
        yr = int(m.group(1) + m.group(2))
        return (yr, None if approx else f'"{_g(yr)}-{m.group(3)}-{m.group(4)}"^^xsd:date', approx)
    m = re.match(r"^(-?)(\d{1,4})-(\d{2})$", c)                           # ISO year-month
    if m:
        yr = int(m.group(1) + m.group(2))
        return (yr, None if approx else f'"{_g(yr)}-{m.group(3)}"^^xsd:gYearMonth', approx)
    m = re.match(r"^(-?)(\d{1,4})$", c)                                   # year (BCE ok)
    if m:
        yr = int(c)
        return (yr, None if approx else f'"{_g(yr)}"^^xsd:gYear', approx)
    m = re.match(r"^(-?)(\d*)(x+)$", c, re.IGNORECASE)                    # wildcard 196x/19xx
    if m and m.group(2):
        return (int(m.group(1) + m.group(2) + "0" * len(m.group(3))), None, True)
    m = re.search(r"-?\d{1,4}", c)                                       # fallback: first int
    if m:
        return (int(m.group(0)), None, True)
    return (None, None, False)


def _split_slash(tok: str):
    """(side, core, ongoing). 'X/..' ongoing/open-end; 'X/' open-end -> start side;
    '/X' open-start -> end side. M/D/Y internal slashes are NOT open-interval markers."""
    tok = (tok or "").strip()
    if not tok:
        return (None, "", False)
    if tok.endswith("/.."):
        return ("start", tok[:-3].strip(), True)
    if tok.endswith("/") and not re.match(r"^\d{1,2}/\d{1,2}/-?\d{3,4}$", tok):
        return ("start", tok[:-1].strip(), False)
    if tok.startswith("/"):
        return ("end", tok[1:].strip(), False)
    return (None, tok, False)


def gdtf_parse(start_raw, end_raw):
    """Parse a GDTF start/end pair (two cells) -> dict of ACT date fields.
    Keys: {start,end}Raw, {start,end}Year, {start,end}Date, {start,end}Approx, ongoing."""
    out = {"startRaw": (start_raw or "").strip(), "endRaw": (end_raw or "").strip(),
           "startYear": None, "startDate": None, "startApprox": False,
           "endYear": None,   "endDate": None,   "endApprox": False, "ongoing": False}
    for col, raw in (("start", start_raw), ("end", end_raw)):
        raw = (raw or "").strip()
        if not raw:
            continue
        side, core, ongoing = _split_slash(raw)
        if ongoing:
            out["ongoing"] = True
        target = side or col                         # slash side overrides column
        yr, typed, approx = _parse_point(core)
        if yr is None and typed is None:
            continue
        if out[target + "Year"] is not None or out[target + "Date"] is not None:
            warn("date_slot_conflict", f"{target}: {raw!r}")
        out[target + "Year"]   = yr
        out[target + "Date"]   = typed
        out[target + "Approx"] = approx
    return out


# ==========================================================================
# Classification  
# ==========================================================================

try:
    from act_classifiers import classify_action        # real cascade (needs rdflib etc.)
except Exception:                                       # structure-only run if unavailable
    def classify_action(expr: str) -> dict:
        return {"labels": [], "confidence": None, "band": None, "signals": {}}


class _ClassifyCache:
    """Wraps classify_action so each unique Action EXPRESSION is classified exactly
    ONCE per run, no matter how many events/rows use it (consistent with ACT's
    expression-level design; also cuts LLM API calls on production corpora with
    repeated vocabulary). Also applies human review overrides (see main()'s
    --apply-review) and tracks per-expression occurrence counts for the review CSV.
    """
    def __init__(self, classify_fn, overrides=None):
        self.classify_fn = classify_fn
        self.overrides = overrides or {}          # expr -> {"labels":[...], "bertLabels":[...],
                                                    #          "llmLabels":[...]}  (human-edited)
        self.cache = {}                           # expr -> result dict
        self.count = defaultdict(int)             # expr -> how many rows referenced it

    def __call__(self, expr):
        self.count[expr] += 1
        if expr not in self.cache:
            if expr in self.overrides:
                ov = self.overrides[expr]
                self.cache[expr] = {
                    "labels": ov["labels"], "confidence": 1.0, "band": "human",
                    # 2026-08 fix: preserve what BERT/LLM had actually suggested before
                    # the human override, instead of blanking it out. catalogHit/bertAgree
                    # are left False since those describe the (now-superseded) automatic
                    # decision, not the human one.
                    "signals": {"catalogHit": False, "bertAgree": False,
                               "bertLabels": ov["bertLabels"], "llmLabels": ov["llmLabels"]},
                }
            else:
                self.cache[expr] = self.classify_fn(expr)
        return self.cache[expr]

    def write_review_csv(self, path):
        """One row per unique expression, sorted by confidence ascending (lowest/most
        uncertain first) so a human reviewer sees what needs attention up top. Rows
        with confidence=None (structure-only stub run) sort last."""
        rows = sorted(self.cache.items(),
                      key=lambda kv: (kv[1].get("confidence") if kv[1].get("confidence")
                                      is not None else 2.0))
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["expression", "occurrences", "labels", "confidence", "band",
                       "source", "catalogHit", "bertAgree", "bertLabels", "llmLabels"])
            for expr, result in rows:
                sig = result.get("signals", {})
                source = ("human" if expr in self.overrides else
                          "catalog" if sig.get("catalogHit") else
                          "classifier" if result["labels"] else "")
                w.writerow([expr, self.count[expr], "|".join(result["labels"]),
                           result.get("confidence"), result.get("band"), source,
                           sig.get("catalogHit", False), sig.get("bertAgree", False),
                           "|".join(sig.get("bertLabels") or []),
                           "|".join(sig.get("llmLabels") or [])])
        return len(rows)


# ==========================================================================
# Core ETL
# ==========================================================================

class Graph:
    """Minimal ordered triple sink with de-duplication."""
    def __init__(self):
        self._seen = set()
        self._lines = []

    def add(self, s, p, o):
        t = (s, p, o)
        if t in self._seen:
            return
        self._seen.add(t)
        self._lines.append(f"{s} {p} {o} .")

    def serialize(self) -> str:
        head = "\n".join(f"@prefix {k}: <{v}> ." for k, v in PREFIXES.items())
        return head + "\n\n" + "\n".join(self._lines) + "\n"


def entity_uri_and_triples(g: Graph, name, category, dewey, wikidata, compound=None):
    """Resolve one linked entity to a URI (or None) and emit its node triples.
    Returns (uri_or_None, is_literal_fallback)."""
    dewey = (dewey or "").strip()
    wikidata = (wikidata or "").strip()
    compound = (compound or "").strip()
    cls = category_to_class(category)
    is_event = top_cat(category) == "event"

    if is_event and (compound or dewey):         # event-as-entity: same priority as an
        uri = event_uri(dewey, compound)            # event's own primary node (see event_uri)
    elif KEY_PRIORITY == "wikidata" and compound:   # tier 0: Compound Record (highest
        uri = ":" + local_id("cpd:" + compound)     #   priority: cross-corpus stable, near-
                                                     #   universal coverage; outranks Wikidata
                                                     #   because Wikidata coverage is patchy even
                                                     #   WITHIN one Compound Record -- 2026-08
                                                     #   revised decision, see design record)
    elif KEY_PRIORITY == "wikidata" and wikidata:   # tier 0.5: Wikidata (only reached when
        uri = ":" + local_id("wd:" + wikidata)      #   compound itself is blank)
    elif dewey:                                 # tier 1: Dewey (not emitted)
        uri = ":" + local_id(dewey)
    elif wikidata:                              # tier 2: Wikidata (reached only in "dewey" mode
        uri = ":" + local_id("wd:" + wikidata)  #   when dewey itself is blank)
    else:                                       # tier 3: no id -> literal fallback
        return None, True

    g.add(uri, "a", "act:" + cls)
    if name:
        g.add(uri, "rdfs:label", lit(name, "ja"))
    if wikidata:
        g.add(uri, "owl:sameAs", "wd:" + wikidata)
    return uri, False


def process(rows, g: Graph, qa_writer=None, classify_fn=None):
    # group rows by event
    events = defaultdict(list)
    order = []
    for r in rows:
        eid = r["event_id"].strip()
        if not eid:
            continue
        if eid not in events:
            order.append(eid)
        events[eid].append(r)

    # pre-pass: eid -> own EVENT_COMPOUND_ID, so parent/child/patient_of references
    # (which only carry the OTHER event's raw event_id, never its compound) can still
    # resolve to that event's correct compound-aware URI via event_uri() below.
    event_compound_by_id = {eid: events[eid][0].get("event_compound", "") for eid in order}

    for eid in order:
        erows = events[eid]
        head = erows[0]
        ev = event_uri(eid, head.get("event_compound"))

        # --- event node ---
        g.add(ev, "a", "act:" + category_to_class(head.get("event_category", "")))
        if head.get("event_label"):
            g.add(ev, "rdfs:label", lit(head["event_label"], "ja"))  # 2026-08: was act:eventLabel
        d = gdtf_parse(head.get("start_date", ""), head.get("end_date", ""))
        for side in ("start", "end"):
            if d[side + "Raw"]:                                  # lossless raw (always)
                g.add(ev, "act:" + side + "DateRaw", lit(d[side + "Raw"], None))
            if d[side + "Year"] is not None:                     # integer anchor (range queries)
                g.add(ev, "act:" + side + "Year", f'"{d[side + "Year"]}"^^xsd:integer')
            if d[side + "Date"] is not None:                     # typed date: exact single point only
                g.add(ev, "act:" + side + "Date", d[side + "Date"])
            if d[side + "Approx"]:                                # ~ % [] x  (open intervals are NOT approx)
                g.add(ev, "act:" + side + "DateApproximate", "true")
        if head.get("reference_id", "").strip():
            ref = ":" + local_id("ref:" + head["reference_id"])
            g.add(ref, "a", "act:Reference")
            if head.get("reference_title"):
                g.add(ref, "rdfs:label", lit(head["reference_title"], "ja"))
            g.add(ev, "act:hasReference", ref)

        # --- action expression + classification -----------------------------------
        # classify_fn defaults to the module-level classify_action (see below main()),
        # but main() normally passes a caching wrapper (_ClassifyCache) so an Action
        # expression that recurs across many events is classified ONCE, not once per
        # row -- consistent with ACT's expression-level (type-level) design, and it
        # also cuts LLM API calls for production corpora with repeated vocabulary.
        action = head.get("action", "").strip()
        if action:
            g.add(ev, "act:hasAction", lit(action, "ja"))
            fn = classify_fn or classify_action
            result = fn(action)
            sig  = result.get("signals", {})
            conf = result.get("confidence")
            band = result.get("band")
            source = ("catalog" if sig.get("catalogHit")
                      else "classifier" if result["labels"] else None)

            for label in result["labels"]:                      # 0..* (multilabel)
                g.add(ev, "act:hasActionType", "at:" + label)
                # RDF-star provenance annotations: OFF by default (lean production KG).
                # classify_action()'s scores remain inspectable via the review CSV
                # (see CLASSIFICATION_REVIEW_CSV / _ClassifyCache in main()).
                if EMIT_RDF_STAR_ANNOTATIONS:
                    star = f"<< {ev} act:hasActionType at:{label} >>"
                    if source:           g.add(star, "act:source", lit(source, None))
                    if conf is not None: g.add(star, "act:confidence", f'"{conf}"^^xsd:decimal')
                    if band:             g.add(star, "act:band", lit(band, None))
                    g.add(star, "act:catalogHit", "true" if sig.get("catalogHit") else "false")
                    if "bertAgree" in sig:
                        g.add(star, "act:bertAgree", "true" if sig.get("bertAgree") else "false")
        # else: Action-less event -> no hasActionType (in scope decision)

        # --- optional SRL literals (event-level; take first non-empty) ---
        for csv_col, prop in OPTIONAL_LIT_COLS.items():
            val = ""
            for r in erows:
                if r.get(csv_col, "").strip():
                    val = r[csv_col].strip(); break
            if val:
                g.add(ev, "act:" + prop, lit(val, "ja"))

        # --- participants (one per row) ---
        for r in erows:
            role = r.get("role", "").strip()
            if not role:
                continue
            name = r.get("linked_name", "").strip()
            cat  = r.get("linked_category", "").strip()

            # resolve role -> property
            if role == "patient":
                prop = PATIENT_SPLIT_BY_TOPCAT.get(top_cat(cat))
                if prop is None:
                    warn("patient_topcat", f"{cat!r} (event {eid[:8]})")
                    prop = "hasPatient"
            else:
                prop = ROLE_TO_PROP.get(role)
                if prop is None:
                    warn("unknown_role", role); continue

            uri, is_lit = entity_uri_and_triples(
                g, name, cat, r.get("linked_dewey"), r.get("linked_wikidata"),
                r.get("linked_compound"))
            if is_lit:
                if name:
                    g.add(ev, "act:" + PROP_TO_LABEL_PROP[prop], lit(name, "ja"))
            else:
                g.add(ev, "act:" + prop, uri)

            # QA: person-like name filed under a space.* category, etc.
            if QA_REPORT and qa_writer and role in ("agent", "patient") \
               and top_cat(cat) == "space":
                qa_writer.writerow([eid, role, name, cat,
                                    r.get("linked_dewey", ""), r.get("linked_wikidata", "")])

        # --- event <-> event links (sub-events) ---
        parent = head.get("parent_event", "").strip()
        if parent:
            g.add(event_uri(parent, event_compound_by_id.get(parent, "")), "act:hasSubEvent", ev)
        for r in erows:
            child = r.get("child_event", "").strip()
            if child:
                g.add(ev, "act:hasSubEvent", event_uri(child, event_compound_by_id.get(child, "")))

        # --- event-as-patient bridge (pattern 2) ---
        if EMIT_PATIENT_OF_BRIDGE:
            for r in erows:
                po = r.get("patient_of", "").strip()
                if po:
                    # this event is the (event-typed) patient of `po` -> hasTheme
                    g.add(event_uri(po, event_compound_by_id.get(po, "")), "act:hasTheme", ev)


# ==========================================================================
# Entry point
# ==========================================================================

def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        actual = {v: k for k, v in COLUMN_MAP.items()}   # header -> logical
        for raw in reader:
            row = {}
            for header, val in raw.items():
                if header in actual:
                    row[actual[header]] = val
                row[header] = val            # keep raw header too (optional lit cols)
            yield row



def write_category_inventory(rows, out_ttl):
    """Census of every category seen (event-level CATEGORY + linked LINKED_CATEGORY),
    with its mapped ACT class and whether it was degraded (collapsed to an ancestor).
    Use this on a new corpus to decide which classes to add to DECLARED_CLASSES."""
    from collections import Counter
    cnt = Counter()
    seen_ev = set()
    for r in rows:
        eid = r.get("event_id", "").strip()
        if eid and eid not in seen_ev:
            seen_ev.add(eid)
            c = r.get("event_category", "").strip()
            if c:
                cnt[("event", c)] += 1
        c = r.get("linked_category", "").strip()
        if c:
            cnt[("linked", c)] += 1
    path = Path(out_ttl).with_name("category_inventory.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scope", "category", "count", "mapped_class", "degraded"])
        for (scope, cat), n in cnt.most_common():
            cls = category_to_class(cat)
            full = "".join(p.capitalize() for p in cat.split("."))
            w.writerow([scope, cat, n, cls, "yes" if cls != full else "no"])
    print(f"category inventory -> {path}")


def main(in_csv, out_ttl, apply_review=None):
    Path(out_ttl).parent.mkdir(parents=True, exist_ok=True)   # 2026-08: out_ttl の親dirが無ければ作る
    rows = list(load_rows(in_csv))
    if CATEGORY_INVENTORY:
        write_category_inventory(rows, out_ttl)

    # --- optional human review overrides (see CLASSIFICATION_REVIEW_CSV) ---
    overrides = {}
    if apply_review:
        with open(apply_review, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                lbls = [l for l in (r.get("labels") or "").split("|") if l]
                if lbls:
                    # 2026-08 fix: keep the ORIGINAL bert/llm suggestions around even
                    # though a human overrode the final label -- previously this was
                    # discarded, so re-running --apply-review silently erased the record
                    # of what the classifier had actually proposed before review.
                    overrides[r["expression"]] = {
                        "labels": lbls,
                        "bertLabels": [l for l in (r.get("bertLabels") or "").split("|") if l],
                        "llmLabels":  [l for l in (r.get("llmLabels")  or "").split("|") if l],
                    }
        print(f"applying {len(overrides)} human-reviewed expression(s) from {apply_review}")

    cc = _ClassifyCache(classify_action, overrides)

    g = Graph()
    qa_f = qa_writer = None
    if QA_REPORT:
        qa_path = Path(out_ttl).with_name("name_category_review.csv")
        qa_f = open(qa_path, "w", encoding="utf-8-sig", newline="")
        qa_writer = csv.writer(qa_f)
        qa_writer.writerow(["event_id", "role", "name", "category", "dewey", "wikidata"])
    try:
        process(rows, g, qa_writer, classify_fn=cc)
    finally:
        if qa_f:
            qa_f.close()

    Path(out_ttl).write_text(g.serialize(), encoding="utf-8")
    print(f"wrote {out_ttl}  ({len(g._lines)} triples, {len(rows)} rows)")
    if _warnings:
        print("warnings:", dict(_warnings))
    if QA_REPORT:
        print(f"QA review -> {Path(out_ttl).with_name('name_category_review.csv')}")
    if CLASSIFICATION_REVIEW_CSV:
        review_path = Path(out_ttl).with_name(Path(out_ttl).stem + "_classification_review.csv")
        n = cc.write_review_csv(review_path)
        print(f"classification review -> {review_path}  "
              f"({n} unique expressions, sorted by confidence ascending)")
        print(f"  edit the 'labels' column and re-run with apply_review={review_path!r} "
              f"(or --apply-review {review_path}) to apply your corrections")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("output_ttl")
    ap.add_argument("--apply-review", default=None,
                    help="path to a classification_review.csv with human-edited "
                         "'labels' column; those expressions override classify_action()")
    a = ap.parse_args()
    main(a.input_csv, a.output_ttl, apply_review=a.apply_review)