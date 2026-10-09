# ACT Phase 2 — expression-level classifier evaluation

- expressions: 574 (single-label 482)
- protocol: 5-fold stratified CV, seed 42, catalog OFF (method comparison); held-out propagated into BERT centroids only -- LLM uses a FIXED catalog (act_llm_catalog.md, not rebuilt per fold), so held-out is not enforced on the LLM side (current design choice, matches the exploratory llm_vs_gold.csv condition; no definitions in prompt).
- BERT centroid mode: mean

## Headline — single-label track (label-based Macro-F1)

| method | Macro-F1 | accuracy |
|---|---|---|
| no-LLM (BERT centroid) | 47.7 | 50.0 |
| LLM (Gemini) | 90.4 | 86.9 |

## Auxiliary — multilabel track

| method | example-based F1 | Macro-F1 |
|---|---|---|
| no-LLM (BERT centroid) | 46.4 | 46.1 |
| LLM (Gemini) | 81.5 | 80.5 |

_Per-class tables are in eval_results.json._
