---
tags: [hub, type/claim]
---

# Claims ledger

| Claim (exact wording) | Evidence | Scope / caveat |
|---|---|---|
| No hospital receives the question in blind mode | [[Formal leakage]] claim 1; tests patch every text/vector tool to fail | under the [[Threat model]]; the device sees it |
| The contact pattern is at the inference floor | [[Robustness results]], [[Session attack]] | 3 splits; sessions on k-means only |
| Only blind unlock does both, among the designs compared | [[HyFedRAG comparison results]], [[Robustness results]] | HyFedRAG-style ties on pattern; PSI ties on content |
| With the standalone client no server holds the question | [[Client and cover results]] | studio still uses the API as the device |
| With cover traffic, nodes cannot tell when the user asks | [[Client and cover results]] | credential id still visible; budget cost |
| Retrieval: 97–98% of a local HyFedRAG-style baseline at P = 24 (matched hybrid ranking) | [[Robustness results]] | quote the split; P = 8 is 81–94%; n.s. only on k-means |
| Blind unlock beats PSI + cells by ~+0.07 MRR | [[Robustness results]] | all splits, p < 0.001 |
| Blind unlock improves answers over closed-book | [[Answer quality results]] | MIRAGE, 150 q, one model, p = 0.035 |
| De-identification mitigates, not eliminates, identifier leakage | [[De-identification results]] | ~13% uncued unregistered names missed |
| Not new cryptography | [[Unbalanced PSI with precomputation]] | the multi-owner setting is the contribution |

**Never say:** "privacy fully solved", "superior retrieval", "94–98%" without the split, "HyFedRAG leaks both", "end-to-end", "PII removed".
