---
tags: [type/mechanism]
updated: 2026-09-30
---

# Cluster index

Nodes build spherical k-means clusters from embeddings, targeting about ten documents per cluster. The minimum-size heuristic is capped by the corpus size; it cannot ensure five records when a corpus contains fewer.

Published centroids help local routing but can disclose source structure. They are not differentially private and do not implement secure profile matching. Restricted-profile publication needs its own authorisation checks.

See [[Role-scoped publication]], [[Bucket recall results]].

## Implementation / Experiment Sources

- [backend/privacy/cluster_index.py](../../backend/privacy/cluster_index.py)
- [docs/35-bucket-recall.md](../../docs/35-bucket-recall.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
