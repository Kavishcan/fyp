---
tags: [literature, worksheet-import, verification-pending]
paper_no: 46
updated: 2026-09-30
---

# Federated Optimization in Heterogeneous Networks

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A47:N47). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 46 |
| Citation | Tian Li, Anit Kumar Sahu, Manzil Zaheer, Maziar Sanjabi, Ameet Talwalkar and Virginia Smith (2020) |
| Paper Title | Federated Optimization in Heterogeneous Networks |
| Problem Addressed | FedAvg can become unstable when clients have different data and different computing resources. |
| Aim / Objective | To introduce FedProx for handling statistical and system heterogeneity. |
| Privacy Risk Addressed | Raw data remains local, but no formal protection is provided for model updates. |
| Federated Component / Coordination | Clients optimise a proximal local objective and the server aggregates their updates. |
| RAG Component | No RAG component. |
| Key Results | FedProx gives more stable and accurate convergence than FedAvg in highly heterogeneous settings. |
| Future Work Mentioned or Implied | Future work should improve large-scale, personalised and privacy-protected heterogeneous FL. |
| Relevance to My Topic | Useful if federated retriever or router clients have different data sizes and capabilities. |
| Identified Gap for My Research | It improves federated optimisation, but does not protect runtime retrieval or RAG information. |
| Link | https://www.semanticscholar.org/search?q=Federated%20Optimization%20in%20Heterogeneous%20Networks%20FedProx&sort=relevance |
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
