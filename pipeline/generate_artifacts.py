"""
Generate the artifacts from act_taxonomy.ttl (the single source of truth).

  1. act_llm_catalog.md        — LLM classifier prompt catalog  (label + examples)
  2. act_annotation_guide.md   — human annotator guideline      (definition + scopeNote + examples)
  3. act_taxonomy_table.md     — human-readable taxonomy table  (category-grouped class list)

DO NOT edit the generated .md files by hand. Edit act_taxonomy.ttl and re-run:
    python3 generate_artifacts.py

Each artifact is produced via a SPARQL query over the taxonomy graph.
"""
from rdflib import Graph
from rdflib.namespace import SKOS, RDF
import datetime

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_DIR = PIPELINE_DIR.parent
TTL = REPO_DIR / "act_taxonomy.ttl"
OUT_DIR = REPO_DIR / "artifacts"
OUT_DIR.mkdir(exist_ok=True)

g = Graph(); g.parse(TTL, format="turtle")

STAMP = datetime.date.today().isoformat()
HEADER = ("<!-- AUTO-GENERATED from act_taxonomy.ttl by generate_artifacts.py on "
          + STAMP + ". DO NOT EDIT BY HAND. Edit the TTL and re-run. -->\n\n")

# ==========================================================================
# CONFIG — edit here to change language / content of generated artifacts
# ==========================================================================
# Languages to emit, in display order. Options: "en", "ja".
#   ["ja","en"] -> Japanese first, then English
#   ["en"]      -> English only
#   ["ja"]      -> Japanese only
LANGS = ["ja", "en"]          # default: both (ja first)

# Include scheme-level Operational notes (multilabel / affix rules / General, etc.)
# in the LLM catalog. Kept OFF for now; the LLM-inclusive pipeline (next step)
# will decide whether to turn this on.
LLM_CATALOG_INCLUDE_OPERATIONAL_NOTES = True

# Include per-ActionType definitions in the LLM catalog (in addition to prefLabel +
# examples). OFF by default to match the original compact-catalog design and the
# exploratory/eval baseline (llm_vs_gold.csv, eval_classify.py's fixed-catalog mode).
# Set True to generate the "with definitions" variant for comparison; this writes to a
# SEPARATE file (act_llm_catalog_with_def.md) so the baseline file is never overwritten.
LLM_CATALOG_INCLUDE_DEFINITIONS = False
# ==========================================================================

LANG_LABEL = {"en": "EN", "ja": "JA"}


NS = "https://w3id.org/act/taxonomy#"

# Display-order hint by broad theme. Categories are read dynamically from the
# TTL (robust to renames); this list only nudges ordering. Any category not
# listed here is appended at the end in alphabetical order. Matching is by a
# keyword found in the category's local name.
CAT_ORDER_HINT = [
 "Military","Resistance","Diplomacy","Political","Lifecycle","Formation",
 "Ending","Movement","Culture","General",
]

def lit(node, prop, lang):
    for o in g.objects(node, prop):
        if getattr(o,'language',None)==lang: return str(o)
    return ""
def any_lit(node, prop):
    for o in g.objects(node, prop): return str(o)
    return ""
def local(uri): return str(uri).split("#")[-1]

# ---- SPARQL: categories in scheme ----
Q_CATS = """
PREFIX skos:<http://www.w3.org/2004/02/skos/core#>
SELECT ?cat WHERE { ?cat skos:topConceptOf ?s . }
"""
# ---- SPARQL: ActionTypes under a given category ----
Q_MEMBERS = """
PREFIX skos:<http://www.w3.org/2004/02/skos/core#>
SELECT ?c WHERE { ?c skos:broader ?cat . }
"""

def members_of(cat_uri):
    from rdflib import URIRef
    rows = g.query(Q_MEMBERS, initBindings={"cat": URIRef(cat_uri)})
    return sorted((r.c for r in rows), key=local)

from rdflib import URIRef
cats_present = sorted({r.cat for r in g.query(Q_CATS)}, key=local)
def order_key(cat_uri):
    ln = local(cat_uri)
    for i,kw in enumerate(CAT_ORDER_HINT):
        if kw in ln: return (i, ln)
    return (len(CAT_ORDER_HINT), ln)  # unknown -> end, alphabetical
cat_uris = sorted(cats_present, key=order_key)

# =====================================================================
# Helpers that respect the LANGS config
# =====================================================================
def preflabels(c):
    """prefLabel string joined per LANGS order, e.g. '軍事攻撃 / Military Attack'."""
    parts=[lit(c,SKOS.prefLabel,l) for l in LANGS]
    return " / ".join(p for p in parts if p)

def defs_lines(c, bullet=True):
    """definition lines per LANGS."""
    lines=[]
    for l in LANGS:
        d=lit(c,SKOS.definition,l)
        if d:
            lines.append((f"- **Definition ({LANG_LABEL[l]})**: {d}" if bullet else d))
    return lines

def examples_for(c):
    """examples per LANGS; ja falls back to any if untagged."""
    res={}
    for l in LANGS:
        ex=lit(c,SKOS.example,l)
        if not ex and l=="ja":
            ex=any_lit(c,SKOS.example)
        if ex: res[l]=ex
    return res

# =====================================================================
# Artifact 1: LLM catalog  (label + examples; optional operational notes)
# =====================================================================
def gen_llm_catalog():
    out=[HEADER, "# ACT ActionType Catalog (for LLM classification)\n\n",
         "Compact list of ActionTypes with representative vocabulary, for use in classifier prompts.\n\n"]
    if LLM_CATALOG_INCLUDE_OPERATIONAL_NOTES:
        sch=URIRef(NS+"ActionTypeScheme")
        notes=list(g.objects(sch,SKOS.editorialNote))
        if notes:
            out.append("## Operational notes\n\n")
            for n in notes: out.append(f"- {n}\n")
            out.append("\n")
    for cat in cat_uris:
        out.append(f"## {preflabels(cat)}\n\n")
        for c in members_of(cat):
            ex=examples_for(c)
            exstr=" | ".join(f"{LANG_LABEL[l]}: {ex[l]}" for l in LANGS if l in ex)
            out.append(f"- **{local(c)}** ({preflabels(c)}): {exstr}\n")
            if LLM_CATALOG_INCLUDE_DEFINITIONS:
                for line in defs_lines(c, bullet=False):
                    out.append(f"  ({line})\n")
        out.append("\n")
    fname = "act_llm_catalog_with_def.md" if LLM_CATALOG_INCLUDE_DEFINITIONS else "act_llm_catalog.md"
    open(OUT_DIR / fname, "w", encoding="utf-8").write("".join(out))
    return fname

# =====================================================================
# Artifact 2: Annotation guideline (definition + scopeNote + examples)
# =====================================================================
def gen_annotation_guide():
    out=[HEADER, "# ACT Annotation Guideline\n\n",
         "For human annotators. Each ActionType lists its definition, scope note (boundaries), and vocabulary examples.\n\n"]
    sch=URIRef(NS+"ActionTypeScheme")
    notes=list(g.objects(sch,SKOS.editorialNote))
    if notes:
        out.append("## Operational notes\n\n")
        for n in notes: out.append(f"- {n}\n")
        out.append("\n")
    for cat in cat_uris:
        out.append(f"## {preflabels(cat)}\n\n")
        cdefs=[lit(cat,SKOS.definition,l) for l in LANGS]
        cdefs=[d for d in cdefs if d]
        if cdefs: out.append("_"+" / ".join(cdefs)+"_\n\n")
        for c in members_of(cat):
            out.append(f"### {local(c)} — {preflabels(c)}\n")
            for line in defs_lines(c): out.append(line+"\n")
            for sn in [str(o) for o in g.objects(c,SKOS.scopeNote) if str(o).strip()]:
                out.append(f"- **Scope note**: {sn}\n")
            ex=examples_for(c)
            for l in LANGS:
                if l in ex: out.append(f"- **Examples ({LANG_LABEL[l]})**: {ex[l]}\n")
            out.append("\n")
    open(OUT_DIR / "act_annotation_guide.md", "w", encoding="utf-8").write("".join(out))

# =====================================================================
# Artifact 3: Human-readable taxonomy table (category-grouped)
# =====================================================================
def gen_taxonomy_table():
    out=[HEADER, "# ACT ActionType Taxonomy (overview table)\n\n",
         "44 ActionTypes across 8 categories. Generated from `act_taxonomy.ttl`.\n\n"]
    # build columns per LANGS
    label_cols=[f"Label ({LANG_LABEL[l]})" for l in LANGS]
    def_cols=[f"Definition ({LANG_LABEL[l]})" for l in LANGS]
    ex_cols=[f"Examples ({LANG_LABEL[l]})" for l in LANGS]
    cols=["ActionType"]+label_cols+def_cols+ex_cols
    for cat in cat_uris:
        out.append(f"## {preflabels(cat)}\n\n")
        cdefs=[lit(cat,SKOS.definition,l) for l in LANGS]
        cdefs=[d for d in cdefs if d]
        if cdefs: out.append("_"+" / ".join(cdefs)+"_\n\n")
        out.append("| "+" | ".join(cols)+" |\n")
        out.append("|"+"|".join(["---"]*len(cols))+"|\n")
        for c in members_of(cat):
            row=[local(c)]
            for l in LANGS: row.append(lit(c,SKOS.prefLabel,l))
            for l in LANGS: row.append(lit(c,SKOS.definition,l).replace("|","\\|"))
            ex=examples_for(c)
            for l in LANGS: row.append(ex.get(l,"").replace("|","\\|"))
            out.append("| "+" | ".join(row)+" |\n")
        out.append("\n")
    open(OUT_DIR / "act_taxonomy_table.md", "w", encoding="utf-8").write("".join(out))

LLM_CATALOG_INCLUDE_DEFINITIONS = False
f1 = gen_llm_catalog()
LLM_CATALOG_INCLUDE_DEFINITIONS = True
f2 = gen_llm_catalog()
print(f"Generated LLM catalogs: {f1} (baseline, no definitions), {f2} (with definitions)")
gen_annotation_guide()
gen_taxonomy_table()
print("Generated: act_llm_catalog.md, act_annotation_guide.md, act_taxonomy_table.md")
