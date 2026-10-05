---
tags: [hub, research-support]
updated: 2026-10-05
---

# Project Status

| Area | Status | Meaning |
|---|---|---|
| Standalone blind-unlock path | Implemented | Local plan, all-node dispatch, cached unlock and local ranking |
| Query/contact-set protection | Argued and measured within scope | Not a complete deployment security proof |
| PMC retrieval | Measured | 5,000 summaries, 986 queries, eight nodes, three partitions |
| MIRAGE answers | Measured, **out of scope since 2026-10-02** | 150 questions; not headline evidence |
| Session contact-pattern attacks | Measured | Five snippets; held-out sessions on k-means only |
| De-identification and role gating | Implemented and tested | Configuration-dependent and not clinically validated |
| Malicious-profile integrity | Partial | Signing and older trust experiments; blind planner is cosine-only |
| Framework packaging | Prototype exists | Requires install/deploy examples, lifecycle documentation and release hardening |
| Unified blind evaluation command | Partial | Existing scorecard does not assemble every current blind/split/session experiment |
| Published baselines (RAGRoute, Flower FedRAG) | Measured | Reproduced from public code on PMC; cost at 8/16/32 hospitals ([[External baselines results]]) |
| Safe Harbor de-identification | Measured (held out) | Fresh test2 recall .853 with registry; not clinically validated ([[Safe Harbor de-identification results]]) |
| Evidence release (G3) | Measured | Records per question vs top-10, cluster × P frontier ([[Release results]]) |
| Large hospitals (PIR tier) | Prototype measured to 2 GB | 100 GB extrapolated; not wired into client/MCP ([[PIR tier results]]) |
| New datasets (MedRAG Textbooks, MTSamples, TREC-COVID) | Downloaded, not run | See [[Experiments index]] |
| Large-scale blind network deployment | Not measured | Older 30-process/300-source tests concern other modes |
| Publication / 90+ mark | Not assessable from implementation alone | Depends on rigor, report, evaluation, rubric and demonstration |

The POC is a credible research prototype. Its remaining work is both research validation and operational hardening, not only writing. [[Next steps]] sets priorities.

## Implementation / Experiment Sources

- [backend/eval/scorecard.py](../backend/eval/scorecard.py)
- [docs/50-robustness-significance-sessions.md](../docs/50-robustness-significance-sessions.md)
- [docs/52-standalone-client-and-cover-traffic.md](../docs/52-standalone-client-and-cover-traffic.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
