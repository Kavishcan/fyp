---
tags: [literature, worksheet-import, verification-pending]
paper_no: 11
updated: 2026-09-30
---

# C-FedRAG: A Confidential Federated Retrieval-Augmented Generation System

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A12:N12). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training; Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 11 |
| Citation | Parker Addison, Minh-Tuan H. Nguyen, Tomislav Medan, Jinali Shah, Mohammad T. Manzari, Brendan McElrone, Laksh Lalwani, Aboli More, Smita Sharma, Holger R. Roth, Isaac Yang, Chester Chen, Daguang Xu, Yan Cheng, Andrew Feng and Ziyue Xu (2024) |
| Paper Title | C-FedRAG: A Confidential Federated Retrieval-Augmented Generation System |
| Problem Addressed | Organisations need RAG across data silos, but cannot freely share private documents. |
| Aim / Objective | To build confidential FedRAG using protected execution across data providers. |
| Privacy Risk Addressed | Focuses on context confidentiality and cross-institution data exposure. |
| Federated Component / Coordination | Uses NVIDIA FLARE to coordinate a federated RAG workflow. |
| RAG Component | Federated retrieval sends protected context for LLM answer generation. |
| Key Results | Shows confidential computing can make secure FedRAG practical. |
| Future Work Mentioned or Implied | Future work needs broader threat models and more benchmarks. |
| Relevance to My Topic | Very relevant because it is close to privacy-aware FedRAG architecture. |
| Identified Gap for My Research | It relies on trusted hardware and does not mainly solve privacy-aware routing. |
| Link | https://www.semanticscholar.org/search?q=C-FedRAG%20A%20Confidential%20Federated%20Retrieval-Augmented%20Generation%20System&sort=relevance |
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
