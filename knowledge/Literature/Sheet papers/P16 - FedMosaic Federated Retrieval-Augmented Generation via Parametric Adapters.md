---
tags: [literature, worksheet-import, verification-pending]
paper_no: 16
updated: 2026-09-30
---

# FedMosaic: Federated Retrieval-Augmented Generation via Parametric Adapters

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A17:N17). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 16 |
| Citation | Zhilin Liang, Yuxiang Wang, Zimu Zhou, Hainan Zhang, Boyi Liu and Yongxin Tong (2026) |
| Paper Title | FedMosaic: Federated Retrieval-Augmented Generation via Parametric Adapters |
| Problem Addressed | Sharing raw retrieved documents in FedRAG creates privacy and communication problems. |
| Aim / Objective | To use parametric adapters instead of sending raw documents. |
| Privacy Risk Addressed | Targets raw document leakage and communication/storage overhead. |
| Federated Component / Coordination | Distributed silos provide adapters that the central server can selectively aggregate. |
| RAG Component | Replaces retrieved text with selected adapters for generation. |
| Key Results | Reports higher accuracy with much lower storage and communication cost. |
| Future Work Mentioned or Implied | Future work should test adapter leakage and real cross-silo deployment. |
| Relevance to My Topic | Useful as another way to share knowledge without raw documents. |
| Identified Gap for My Research | Adapters may still leak information, and routing/privacy attacks are not fully studied. |
| Link | https://www.semanticscholar.org/search?q=FedMosaic%20Federated%20Retrieval-Augmented%20Generation%20via%20Parametric%20Adapters&sort=relevance |
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
