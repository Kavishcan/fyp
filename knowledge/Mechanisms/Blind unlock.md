---
tags: [type/mechanism, status/recommended]
---

# Blind unlock (`routing_mode="blind"`, docs/47)

**Idea:** download every hospital's locked table once; per question send **exactly P blinded points to every hospital**, real or [[Dummy points]]; unlock only the chosen boxes locally.

- Offline: [[Chunked blind tables]] keyed by OPRF-derived tags; restricted collections only to permitted roles ([[Role-based access]]).
- Online: global top-P clusters across all hospitals ([[Cluster index]]), [[OPRF]] stamping, tag lookup, [[Hybrid rerank]].
- Rounds contact every node before unlocking anything ([[Timing channel]] fix); one implementation, `blind_round`, shared by the API and the [[Standalone client]].
- Keys rotate per epoch ([[Key epochs and rotation]]); key/tag derivation binds the cluster id ([[2HashDH key binding]]).

**Not new cryptography:** the core is [[Unbalanced PSI with precomputation]] + [[Labeled PSI]], with [[Wally]]-style fake queries. The additions are the multi-owner setting: identical cover probes to every owner, cross-owner cluster selection, per-role keys.

Results: [[Blind unlock results]], [[Robustness results]], [[Formal leakage]]. Costs: [[Scaling of blind unlock]].
