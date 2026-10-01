---
tags: [type/result]
updated: 2026-09-30
---

# Blind unlock results

Do not mix table formats or reranking conditions.

| Run / Configuration | K-means MRR | Disclosure / Setup |
|---|---|---|
| Initial dense P=4 | .399 | About 74 passages/query |
| Initial dense P=8 | .421 | About 140 passages/query |
| Initial dense P=24 | .437 | About 393 passages/query |
| Int8 dense P=8 | .422576 | 15,037,120 offline table bytes |
| Int8 hybrid P=8 | .508276 | Same table; 140.39 passages/query |
| Int8 hybrid P=24 | .535746 | Same table; 393.43 passages/query |

Int8 P=8 reports 4,608 sent and 4,608 received bytes/query in harness accounting. These are counted payload bytes, not verified full authenticated RPC/TLS wire totals. Offline transfer and refresh are separate.

All eight nodes are contacted; no raw query/embedding is dispatched. P=24 preserves more retrieval but opens substantially more passages. See [[Robustness results]], [[Chunked blind tables]].

## Implementation / Experiment Sources

- [docs/47-blind-unlock.md](../../docs/47-blind-unlock.md)
- [docs/results/hyfedrag_compare_kmeans_int8_20260929-210923.csv](../../docs/results/hyfedrag_compare_kmeans_int8_20260929-210923.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
