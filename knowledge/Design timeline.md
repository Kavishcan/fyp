---
tags: [hub]
updated: 2026-10-05
---

# Design Timeline

1. Text-based selective routing: useful but sources see the query.
2. Vector dispatch: literal text hidden, tested inversion still succeeds.
3. Per-query PSI: query inputs hidden, selective contacts leak patterns and table transfer costs are high.
4. Decoys/cells: partial pattern mitigation, longitudinal and churn weaknesses.
5. Cached blind unlock: local cluster selection, all-node equal probes, setup amortisation.
6. Local reranking: PMC utility improves; MIRAGE hybrid answers do not.
7. Permissions, budgets and audit fixes: source disclosure constrained but not solved.
8. Standalone client and finite cover scheduling: tighter query boundary and timing treatment.
9. Three PMC partitions, bootstrap comparisons and session attacks: broader evidence, still scoped.
10. Current review: correct revocation, signing, disclosure and timing overclaims.
11. Published baselines reproduced (RAGRoute, Flower FedRAG): privacy at comparable cost, not cheapest ([[External baselines results]]).
12. Safe Harbor de-identification with held-out tests: rules do not generalise to new phrasing ([[Safe Harbor de-identification results]]).
13. PIR tier for large hospitals ([[PIR tier results]]).
14. Evidence release measured; scope narrowed to privacy + retrieval ([[Release results]]).

See [[Source reconciliation]], [[Next steps]]. Historical modes remain controls, not current recommended deployment.
