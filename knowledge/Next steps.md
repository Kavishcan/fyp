---
tags: [hub, research-support]
updated: 2026-10-05
---

# Next Steps

## Now (2026-10-05)
- Commit docs/55–56, PIR tier, Safe Harbor fixes, release harness.
- Run the main comparison on [[MedRAG Textbooks]] (natural sources), then [[TREC-COVID]] and [[MTSamples]]; retrieval metrics only.
- 2–3 seeds for the PMC comparison.
- Optional: wire the [[PIR tier]] into MCP/client; cap tier-2 cluster size at one column.

## First: Close Claim-Relevant Gaps
1. Fix restricted-only public profile fallback and require explicit source identity/signature policy for privacy deployments.
2. Audit labelled-table/OPRF security with a specialist; test replay, collusion, multiple collections, revocation limits and malformed/malicious replies.
3. Measure blind-specific profile hijacking and poisoned evidence. Do not transfer older trust/rerank wins automatically.
4. Test cover scheduling under slow/failing nodes, real transport and realistic budgets. Report missed deadlines and session participation.
5. Assemble current blind, partition, session, QA, de-id and transport results in one reproducible scorecard.

## Then: Strengthen Evaluation
6. Repeat across seeds, additional session splits and generation models.
7. Pre-specify a meaningful noninferiority margin if claiming near-equal utility; pair it with disclosure and cost budgets.
8. Report complete wire bytes, cache footprint/refresh, opened records, energy and concurrent-client throughput.
9. Evaluate metadata leakage and de-identification on expert-reviewed data; separate synthetic ground truth from clinical evidence.
10. Benchmark blind mode on larger real-process federations before claiming scale.

## Finish: Framework and Report
11. Package installable library, secure configuration examples, node lifecycle and cache management.
12. Read closest private-search and FedRAG papers; build a source-grounded capability matrix.
13. Write your own methods, critical literature synthesis, limitations and results discussion.

See [[Reading plan]], [[Research gap analysis]], [[Project status]]. No algorithm can be promised universally superior.
