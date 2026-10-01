---
tags: [hub, research-support]
updated: 2026-09-30
---

# Claims Ledger

| Claim You Can Defend | Evidence | Qualification |
|---|---|---|
| Blind nodes do not receive query text or its embedding | [[Blind unlock]], [[Client and cover results]] | Standalone path; metadata and credentials remain visible |
| Fixed all-node contacts hide query-dependent source selection | [[Robustness results]], [[Session attack]] | Fixed federation; attack measures contact-set leakage, not every side channel |
| Blind P=24 preserves 96.9-98.4% of the matched local hybrid baseline MRR | [[Robustness results]] | Eight simulated nodes, three PMC splits; not official HyFedRAG execution |
| Blind dense improves MIRAGE answers over closed-book in one run | [[Answer quality results]] | 150 questions, one local model; p=.035 |
| De-identification reduces some identifier disclosures | [[De-identification results]] | Synthetic and public-text tests; misses remain; alteration is not semantic damage |
| Collection permissions and persistent budgets constrain future access | [[RBAC results]], [[Credential gate]] | Configured gated nodes; saved plaintext or past unlock keys cannot be revoked |
| This is an implemented integration, not new cryptography | [[Novelty and contribution]] | Broader novelty needs a systematic primary-paper comparison |

**Do not claim:** universally superior; all privacy solved; exact equivalence from nonsignificant p-values; all records anonymised; 1,000 blind nodes measured; published baselines reproduced when only local approximations were run.

Earlier test totals are engineering checks, not evidence of privacy guarantees. See [[Project status]] and [[Source reconciliation]].

## Implementation / Experiment Sources

- [docs/50-robustness-significance-sessions.md](../docs/50-robustness-significance-sessions.md)
- [docs/51-formal-leakage.md](../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
