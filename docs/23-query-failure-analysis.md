# Where the first candidate-budget router misses evidence

This is a post-hoc analysis of the original saved pilot, not a new experiment.
The input results are unchanged. Each gold document is assigned to exactly one
stage; no document is counted in two failure categories.

## Stage definitions

- Source miss: its source was never contacted.
- Depth miss: its source was contacted, but the document was not returned.
- Rerank miss: the document was returned, but excluded from the final five.
- Recovered: the document reached the final five.

These are operational stages, not causal findings. "Gold" means a positive
BEIR relevance judgment, not necessarily a fact required to answer a question.
The report records the gold document's one-based local rank and source quota
so a reader can distinguish insufficient retrieval depth from a source miss.

## B=12, C=3, final K=5

Percentages are fractions of ALL judged-relevant documents, macro-averaged over
questions and three partition seeds. They are not percentages of missed cases.

| Dataset | Method | Source miss | Depth miss | Rerank miss | Recovered |
|---|---|---:|---:|---:|---:|
| SciFact | Equal | 70.198% | 1.244% | 0.767% | 27.791% |
| SciFact | Old joint | 70.915% | 1.111% | 0.567% | 27.407% |
| NFCorpus | Equal | 86.917% | 6.458% | 1.346% | 5.280% |
| NFCorpus | Old joint | 87.158% | 6.636% | 1.328% | 4.878% |
| SCIDOCS | Equal | 87.179% | 5.624% | 1.378% | 5.819% |
| SCIDOCS | Old joint | 87.568% | 5.405% | 1.349% | 5.678% |

The original method sometimes helps, but more often hurts among changed
query/partition cases. These counts include repeated questions across seeds:

| Dataset | Higher final recall | Lower final recall | Tied |
|---|---:|---:|---:|
| SciFact | 22 | 26 | 852 |
| NFCorpus | 61 | 70 | 838 |
| SCIDOCS | 151 | 174 | 2,675 |

## Two concrete illustrations

These are explicitly selected extremes, not representative samples. The full
artifact contains two helped and two hurt distinct queries per dataset.

**Helped: SciFact query 1, seed 33.** The query concerns inductive properties of
0-dimensional biomaterials. Equal quotas chose sources 011, 019 and 005. The
joint policy replaced 005 with 014, which held gold document 31715818 at local
rank 1. Final relevant-document recall changed from 0% to 100% for this case.

**Hurt: SciFact query 1146, seed 33.** The query compares teaching and non-teaching
hospitals. Equal quotas chose sources 012, 026 and 025. Gold document 13906581,
"Patient Outcomes with Teaching Versus Nonteaching Healthcare: A Systematic
Review", was ranked first within 025. The joint policy chose 015 instead of 025
and missed the evidence entirely. Final recall changed from 100% to 0%.

These examples show that a source replacement can make or break retrieval
even when its useful document is locally ranked first. They do not prove that
the coverage penalty alone caused the aggregate regression.

## What this justifies testing

Prioritize source identification before increasing quota complexity. The next
experiment uses paid passages as anchored pseudo-relevance feedback to choose
the remaining clients, while keeping equal quotas and the final ranker fixed.
Unlike the old rule it does not downweight a source merely because a centroid
resembles an already retrieved passage. It may still drift toward an incorrect
first result, so it must be evaluated rather than assumed better.

Protocol: [anchored feedback routing](24-feedback-routing-protocol.md).

## Reproduce and inspect

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.diagnose_candidates --output experiments/routing-study-diagnosis-v1
```

Use a fresh output path when rerunning. Existing output contains:

- `per-query.csv`: 14,607 query/partition/method rows, including all three
  equal/proportional/joint methods at B=12, query text, contacts and quotas.
- `per-document.jsonl`: each gold document's true corpus ID, source, local rank,
  requested quota and failure stage. Index IDs in saved traces are mapped back
  to original corpus IDs here.
- `report.md`: readable summary and helped/hurt examples.
- `examples.json`: full structured examples, including all gold documents.
- `summary.json` and `manifest.json`: aggregate measurements and provenance.

Files live under `experiments/routing-study-diagnosis-v1/` and remain gitignored
with the original datasets. This tracked report preserves the key findings.
