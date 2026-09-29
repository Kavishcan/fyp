---
tags: [hub]
---

# Experiments index

| Dataset / harness | Used for |
|---|---|
| [[FeB4RAG]] | resource selection, pattern leak (docs/36, 39, 40) |
| [[PMC-Patients]] | patient-to-patient retrieval, HyFedRAG comparison, blind unlock (docs/46–50) |
| [[MIRAGE]] | answer accuracy with a local LLM (docs/38, 50) |
| [[BEIR healthcare federation]] | same-domain 8-client federation (docs/40) |
| [[Synthetic privacy cases]] | 200 cases, sensitive values reaching nodes (docs/37) |
| [[Hospital splits]] | k-means / Dirichlet / random robustness (docs/50) |
| [[Paired bootstrap]] | significance for every retrieval ratio |

Harnesses live in `backend/eval/` — see [[Code map]].
