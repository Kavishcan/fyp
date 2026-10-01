---
tags: [type/experiment]
updated: 2026-09-30
---

# BEIR healthcare federation

Source: [BEIR official repository](https://github.com/beir-cellar/beir).

Different experiments use different sampled corpora. Earlier eight same-domain clients pool biomedical sources and partition them; the latest MIRAGE run instead uses six named source corpora.

Documents/relevance labels come from public benchmark collections. Clients are simulated organisational partitions, not independently governed hospitals.

See [[Dataset register]], [[Cells and rerank results]], [[MIRAGE]].

## Implementation / Experiment Sources

- [backend/eval/run_healthcare.py](../../backend/eval/run_healthcare.py)
- [docs/40-cells-rerank-healthcare.md](../../docs/40-cells-rerank-healthcare.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
