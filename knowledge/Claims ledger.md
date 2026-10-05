---
tags: [hub, research-support]
updated: 2026-10-05
---

# Claims Ledger

| Claim You Can Defend | Evidence | Qualification |
|---|---|---|
| Blind nodes do not receive query text or its embedding | [[Blind unlock]], [[Client and cover results]] | Standalone path; metadata and credentials remain visible |
| Fixed all-node contacts hide query-dependent source selection | [[Robustness results]], [[Session attack]] | Fixed federation; attack measures contact-set leakage, not every side channel |
| Blind P=24 preserves 96.9-98.4% of the matched local hybrid baseline MRR | [[Robustness results]] | Eight simulated nodes, three PMC splits; not official HyFedRAG execution |
| (Out of scope) Blind dense improves MIRAGE answers over closed-book in one run | [[Answer quality results]] | 150 questions, one local model; p=.035; generation is no longer a thesis claim |
| De-identification reduces some identifier disclosures | [[De-identification results]] | Synthetic and public-text tests; misses remain; alteration is not semantic damage |
| Collection permissions and persistent budgets constrain future access | [[RBAC results]], [[Credential gate]] | Configured gated nodes; saved plaintext or past unlock keys cannot be revoked |
| Blind gives privacy at comparable cost to published systems | [[External baselines results]] | ~4× less hospital CPU and ~30× less traffic than bge broadcast; RAGRoute cheaper in hospital CPU; blind slightly slower; quality vs RAGRoute is split-dependent |
| Selective routing leaks the topic even when cheaper | [[External baselines results]] | RAGRoute .562 vs floor .226 (k-means, 8 hospitals) |
| Safe Harbor rules + NER + registry removed 85% of identifiers on a fresh held-out set | [[Safe Harbor de-identification results]] | Synthetic identifiers in real prose; rules do not generalise; never "HIPAA compliant" |
| Evidence release is measured and tunable | [[Release results]] | 5/5 clusters at P=16: same MRR, 19% fewer records; smaller minimums raise centroid proximity; broadcast releases fewer records |
| Per-question cost is independent of hospital size; a PIR tier removes the full download | [[PIR tier results]] | Measured to 2 GB; 100 GB extrapolated; hospital scans its table per query |
| This is an implemented integration, not new cryptography | [[Novelty and contribution]] | Broader novelty needs a systematic primary-paper comparison |

**Do not claim:** cheapest or fastest; HIPAA compliant; PIR tier as new; universally superior; all privacy solved; exact equivalence from nonsignificant p-values; all records anonymised; 1,000 blind nodes measured; published baselines reproduced when only local approximations were run.

Earlier test totals are engineering checks, not evidence of privacy guarantees. See [[Project status]] and [[Source reconciliation]].

## Implementation / Experiment Sources

- [docs/50-robustness-significance-sessions.md](../docs/50-robustness-significance-sessions.md)
- [docs/51-formal-leakage.md](../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
