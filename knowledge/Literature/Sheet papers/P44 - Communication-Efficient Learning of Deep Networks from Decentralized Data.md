---
tags: [literature, worksheet-import, verification-pending]
paper_no: 44
updated: 2026-09-30
---

# Communication-Efficient Learning of Deep Networks from Decentralized Data

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A45:N45). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 44 |
| Citation | H. Brendan McMahan, Eider Moore, Daniel Ramage, Seth Hampson and Blaise Agüera y Arcas (2017) |
| Paper Title | Communication-Efficient Learning of Deep Networks from Decentralized Data |
| Problem Addressed | Central training requires collecting private device data, while frequent communication is expensive. |
| Aim / Objective | To introduce Federated Averaging for training one model from decentralised client data. |
| Privacy Risk Addressed | Raw data stays local, but individual model updates can still leak information. |
| Federated Component / Coordination | A server selects clients, sends the model and averages their locally trained updates. |
| RAG Component | No RAG component. |
| Key Results | FedAvg reduced communication rounds by about 10 to 100 times compared with synchronised SGD. |
| Future Work Mentioned or Implied | Future work should improve privacy, client participation, heterogeneity and reliability. |
| Relevance to My Topic | This is the basic FL method I could use if I federatively train a router or retriever. |
| Identified Gap for My Research | Keeping data local does not protect updates and does not solve RAG query, document, prompt or output leakage. |
| Link | https://www.semanticscholar.org/search?q=Communication-Efficient%20Learning%20of%20Deep%20Networks%20from%20Decentralized%20Data&sort=relevance |
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
