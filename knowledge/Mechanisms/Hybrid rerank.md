---
tags: [type/mechanism]
---

# Hybrid rerank (`router/hybrid_rerank.py`, docs/48)

z(cosine) + 0.5·z(BM25), BM25 statistics from the passages the device holds only. Device-only — changes nothing that leaves the device. +0.09–0.10 MRR for everyone on [[PMC-Patients]]; **does not help [[MIRAGE]]** (0.613 dense vs 0.573 hybrid). Task-dependent. Results: [[Hybrid rerank results]].
