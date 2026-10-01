---
tags: [type/result]
updated: 2026-09-30
---

# Robustness results

Same 5,000 PMC documents, 986 queries and eight nodes; matched hybrid ranking unless stated.

| Configuration | K-means MRR | Dirichlet MRR | Random MRR |
|---|---|---|---|
| HyFedRAG-style dense | .444 | .444 | .444 |
| HyFedRAG-style hybrid | .543 | .542 | .535 |
| Blind P=8 hybrid | .509 | .465 | .432 |
| Blind P=16 hybrid | .526 | .514 | .499 |
| Blind P=24 hybrid | .535 | .528 | .519 |
| Centralised hybrid | .555 | .555 | .555 |

P=24 baseline ratios: 98.4% [96.6,100.2], 97.4% [95.2,99.5], 96.9% [94.5,99.2]. Difference tests: p=.08, .01, .01 respectively. The k-means result is **not demonstrated equivalence**.

P=8 ratios are 93.6%, 85.8%, 80.7%; never generalise the strongest split. Blind dense versus PSI+cells dense gains .071/.073/.067, p<.001. Contact-set topic prediction matches each split's floor.

See [[Hospital splits]], [[Paired bootstrap]], [[Claims ledger]].

## Implementation / Experiment Sources

- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)
- [docs/results/hyfedrag_compare_kmeans_20260929-210204.csv](../../docs/results/hyfedrag_compare_kmeans_20260929-210204.csv)
- [docs/results/hyfedrag_compare_dirichlet_20260929-214214.csv](../../docs/results/hyfedrag_compare_dirichlet_20260929-214214.csv)
- [docs/results/hyfedrag_compare_random_20260929-221645.csv](../../docs/results/hyfedrag_compare_random_20260929-221645.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
