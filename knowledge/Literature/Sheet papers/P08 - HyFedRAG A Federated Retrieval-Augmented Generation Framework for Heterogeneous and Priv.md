---
tags: [literature, worksheet-import, verification-pending]
paper_no: 8
updated: 2026-09-30
---

# HyFedRAG: A Federated Retrieval-Augmented Generation Framework for Heterogeneous and Privacy-Sensitive Data

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A9:N9). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training; Healthcare and sensitive-domain applications.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 8 |
| Citation | Cheng Qian, Hainan Zhang, Yongxin Tong, Hong-Wei Zheng and Zhiming Zheng (2025) |
| Paper Title | HyFedRAG: A Federated Retrieval-Augmented Generation Framework for Heterogeneous and Privacy-Sensitive Data |
| Problem Addressed | Healthcare data is distributed, sensitive, and heterogeneous, so centralised RAG is not suitable. |
| Aim / Objective | To create a FedRAG framework for heterogeneous and privacy-sensitive healthcare-style data. |
| Privacy Risk Addressed | my |
| Federated Component / Coordination | Uses an edge-cloud federated setup with local retrievers and a cloud reasoning layer. |
| RAG Component | Combines local retrieval with server-side generation/reasoning over protected representations. |
| Key Results | Shows FedRAG can work across SQL, graphs, and clinical notes. |
| Future Work Mentioned or Implied | Future work needs stronger formal privacy guarantees and real-world testing. |
| Relevance to My Topic | Very relevant because it is close to privacy-sensitive FedRAG architecture. |
| Identified Gap for My Research | It uses anonymisation, but full query, routing, prompt, and output privacy is still open. |
| Link | https://www.semanticscholar.org/search?q=HyFedRAG%20A%20Federated%20Retrieval-Augmented%20Generation%20Framework%20for%20Heterogeneous%20and%20Privacy-Sensitive%20Data&sort=relevance |
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
