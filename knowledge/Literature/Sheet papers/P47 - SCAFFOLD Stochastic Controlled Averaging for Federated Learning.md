---
tags: [literature, worksheet-import, verification-pending]
paper_no: 47
updated: 2026-09-30
---

# SCAFFOLD: Stochastic Controlled Averaging for Federated Learning

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A48:N48). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 47 |
| Citation | Sai Praneeth Karimireddy, Satyen Kale, Mehryar Mohri, Sashank J. Reddi, Sebastian U. Stich and Ananda Theertha Suresh (2020) |
| Paper Title | SCAFFOLD: Stochastic Controlled Averaging for Federated Learning |
| Problem Addressed | Non-IID client data causes local updates in FedAvg to drift away from the global objective. |
| Aim / Objective | To correct client drift using control variates in the SCAFFOLD algorithm. |
| Privacy Risk Addressed | Raw data stays local, but shared updates and control values may still leak information. |
| Federated Component / Coordination | The server and clients maintain control variates while local model updates are aggregated. |
| RAG Component | No RAG component. |
| Key Results | SCAFFOLD needs fewer communication rounds and is more robust to data heterogeneity and client sampling. |
| Future Work Mentioned or Implied | Future work should test wider models, large client populations and stronger privacy protection. |
| Relevance to My Topic | Useful if I later train a federated retriever on strongly different client data. |
| Identified Gap for My Research | It solves optimisation drift, not query privacy, document privacy or source routing. |
| Link | https://www.semanticscholar.org/search?q=SCAFFOLD%20Stochastic%20Controlled%20Averaging%20for%20Federated%20Learning&sort=relevance |
| Priority | Medium |

## Verify During Reading

- [ ] Resolve the canonical paper record, complete author list and version.
- [ ] Trace query, embedding, document, profile and model-update flows.
- [ ] Identify trusted components, attacker access and visible metadata.
- [ ] Record datasets, partitions, baselines, budgets and actual measured outcomes.
- [ ] Distinguish author-stated limitations from your own inferred gaps.
- [ ] Decide whether it is a direct baseline, related method or background only.
- [ ] Write your own critical summary after reading the paper.

Project comparison: [[Research gap analysis]], [[Threat model]], [[Architecture]], [[Claims ledger]]. Return to [[Paper register]].
