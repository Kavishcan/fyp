---
tags: [type/mechanism]
---

# Cluster index (`privacy/cluster_index.py`, docs/35)

Each node splits its de-identified documents into spherical k-means clusters of ~10 (min size 5 — never publish near-document centroids) and publishes the centroids. The cluster id is the PSI item. Bucket recall 0.89 of dense@10 at nprobe 2 ([[Bucket recall results]]). In [[Blind unlock]] the device scores **all** hospitals' centroids and picks the global top P.
