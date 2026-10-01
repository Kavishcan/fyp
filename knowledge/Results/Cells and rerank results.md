---
tags: [type/result]
updated: 2026-09-30
---

# Cells and rerank results

Historical cell-routing results:
| Benchmark | Topic Accuracy Before -> After | Source Accuracy Before -> After |
|---|---|---|
| FeB4RAG | .454 -> .201 | .744 -> .231 |
| BEIR healthcare federation | .615 -> .272 | .875 -> .250 |

FeB4RAG graded gain decreases about .12. Cross-node evidence reranking drops planted-passage citation 1.000 -> .067 in that experiment, not necessarily selection.

Cells retain residual leakage and churn risks. These are not current blind-mode integrity results. See [[Anonymity cells]], [[Forged profile attack]].

## Implementation / Experiment Sources

- [docs/40-cells-rerank-healthcare.md](../../docs/40-cells-rerank-healthcare.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
