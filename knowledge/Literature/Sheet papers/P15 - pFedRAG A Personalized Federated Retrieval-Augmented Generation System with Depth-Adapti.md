---
tags: [literature, worksheet-import, verification-pending]
paper_no: 15
updated: 2026-09-30
---

# pFedRAG: A Personalized Federated Retrieval-Augmented Generation System with Depth-Adaptive Tiered Embedding Tuning

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A16:N16). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 15 |
| Citation | Hangyu He, Xin Yuan, Kai Wu, Ren Ping Liu and Wei Ni (2025) |
| Paper Title | pFedRAG: A Personalized Federated Retrieval-Augmented Generation System with Depth-Adaptive Tiered Embedding Tuning |
| Problem Addressed | Domain RAG needs personalisation, but medical data is non-IID and privacy-sensitive. |
| Aim / Objective | To improve personalised retrieval in FedRAG without centralising medical data. |
| Privacy Risk Addressed | Addresses medical document leakage and model update leakage. |
| Federated Component / Coordination | Uses personalised FL with shared global layers and local adaptive layers. |
| RAG Component | Improves the dense retrieval/embedding part of personalised RAG. |
| Key Results | Improves retrieval and response quality while reducing communication cost. |
| Future Work Mentioned or Implied | Future work needs stronger privacy defenses and wider domain evaluation. |
| Relevance to My Topic | Relevant if my system includes medical or personalised client data. |
| Identified Gap for My Research | It handles personalised retrieval, but not full query, prompt, output, and routing privacy. |
| Link | https://www.semanticscholar.org/search?q=pFedRAG%20Personalized%20Federated%20Retrieval-Augmented%20Generation%20System%20Depth-Adaptive%20Tiered%20Embedding%20Tuning&sort=relevance |
| Priority | High |

## Verify During Reading

- [ ] Resolve the canonical paper record, complete author list and version.
- [ ] Trace query, embedding, document, profile and model-update flows.
- [ ] Identify trusted components, attacker access and visible metadata.
- [ ] Record datasets, partitions, baselines, budgets and actual measured outcomes.
- [ ] Distinguish author-stated limitations from your own inferred gaps.
- [ ] Decide whether it is a direct baseline, related method or background only.
- [ ] Write your own critical summary after reading the paper.

Project comparison: [[Research gap analysis]], [[Threat model]], [[Architecture]], [[Claims ledger]]. Return to [[Paper register]].
