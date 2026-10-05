---
tags: [hub]
updated: 2026-10-05
---

# Experiments Index

[[Dataset register]] provides source links; [[Dataset strategy]] explains each test.

| Experiment | Data / Endpoint |
|---|---|
| [[PMC-Patients]], [[Hospital splits]] | Main retrieval utility and contact-set leakage |
| [[MIRAGE]] | Answer accuracy with six BEIR nodes |
| [[FeB4RAG]] | Federated source selection and origin/topic inference |
| [[BEIR healthcare federation]] | Earlier homogeneous-source contact leakage |
| [[Synthetic privacy cases]] | Fictional query values and malicious fixtures |
| [[Paired bootstrap]] | Shared-query uncertainty tests |
| [[Session attack]] | Longitudinal contact histories, k-means only |
| [[External baselines results]] | RAGRoute / Flower FedRAG / HyFedRAG-style vs blind on PMC; cost at 8/16/32 hospitals |
| [[De-identification benchmark]] | Held-out Safe Harbor identifiers in PMC prose |
| [[Release results]] | Records released per question; cluster × P frontier |
| [[PIR tier results]] | Tier 1 vs tier 2 on PMC; PIR scaling 64 MB–2 GB |
| [[MedRAG Textbooks]], [[MTSamples]], [[TREC-COVID]] | Downloaded 2026-10-02, not yet run |

MIRAGE answer accuracy is out of scope since 2026-10-02. See [[eval harnesses]] for entry points and [[Results index]] for archives.
