# ACT: an action-centric ontology and taxonomy for historical events

ACT describes historical events through actions. Alongside the semantic roles, places and dates of an event, it assigns each event one or more **action types**, so that the same act written in different words can be counted, compared and queried across sources.

This repository holds:

- the ACT vocabulary: an OWL ontology, a SKOS taxonomy of action types and a resource of expressions with more than one type;
- the pipeline that classifies action expressions and converts records of the COTEN DB into knowledge graphs;
- the code of the evaluations of benchmarking tasks.

## Vocabulary

| File | Content | IRI |
| --- | --- | --- |
| `act_ontology.ttl` | OWL ontology of historical events | <https://w3id.org/act/> |
| `act_taxonomy.ttl` | Taxonomy of 44 action types under 8 categories as SKOS concepts | <https://w3id.org/act/taxonomy> |
| `act_multilabel.ttl` | Expressions that map to more than one action type | <https://w3id.org/act/multilabel>|

Namespace prefixes:

| Prefix | Namespace |
| --- | --- |
| `act:` | `https://w3id.org/act/ontology#` |
| `at:` | `https://w3id.org/act/taxonomy#` |

The turtle files are the only files to be edited by hand. Everything in `artifacts/` derives from them.

## Repository layout

```
act_ontology.ttl, act_taxonomy.ttl, act_multilabel.ttl   ACT vocabulary (persistent IRIs)
artifacts/      generated from the Turtle files by pipeline/generate_artifacts.py
                (LLM catalog with and without definitions, annotation guide, table of types)
pipeline/       classification cascade and conversion to RDF
evaluation/     benchmark of the taxonomy (benchmark.ipynb) and evaluation of the
                pipeline classifiers (eval_classify.py) with their aggregate results
```

## Requirements

Python 3.10 or later.

```
pip install -r requirements.txt
```

The LLM classifier calls the Gemini API and needs a key in the environment variable `GEMINI_API_KEY`. Without a key, the pipeline classifies with the lookup index and the BERT classifier only.

## Running the pipeline

```
# 1. Regenerate the artifacts after editing the Turtle files
python pipeline/generate_artifacts.py

# 2. Set the API key (PowerShell; see pipeline/act_etl.py for other shells)
$env:GEMINI_API_KEY = "..."

# 3. Convert a corpus
python pipeline/act_etl.py path/to/corpus.csv out/corpus_data.ttl

# 4. Optionally correct the types in the review file and run again
python pipeline/act_etl.py path/to/corpus.csv out/corpus_data.ttl --apply-review out/corpus_data_classification_review.csv
```

The input is a CSV in long format, with one row for each link between an event and a role. The docstring of `pipeline/act_etl.py` describes the expected columns, the outputs and the settings.

## Evaluation

- `evaluation/benchmark.ipynb` reproduces the benchmark of the first version of the taxonomy: majority class, character n-grams, Japanese WordNet, Tohoku BERT v3, K-means clustering and four LLMs. It writes the prompt given to the LLMs to `evaluation/prompt.md`.
- `evaluation/eval_classify.py` evaluates the classifiers of the pipeline against the ground truth with five-fold cross-validation. Run `python evaluation/eval_classify.py --bert --llm`. The aggregate results are in `eval_report.md` and `eval_results.json`.

Both need data that this repository does not include (see below). Place the files in `evaluation/data/`, as listed in `evaluation/data/README.md`.

## Data not included

The knowledge graphs, the ground-truth dictionaries, the input CSVs and the answers of the LLMs derive from the COTEN DB and from the published works it uses. They are not part of this repository.

## Licence

- ACT vocabulary (`*.ttl`) and generated artifacts (`artifacts/`): [CC BY 4.0]

## Citation

Nakamura, Shiho. *An Action-Centric Approach to Structuring Historical Events:
The ACT Ontology, Taxonomy and Knowledge Graph*. Master's thesis, Digital Humanities and Digital Knowledge, University of Bologna, 2026.
