---
tags: [literature, worksheet-import, verification-pending]
paper_no: 17
updated: 2026-09-30
---

# FD-RAG: Federated Dual-System Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A18:N18). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 17 |
| Citation | Tianhao Gao, Kai Yang and Yiyang Li (2026) |
| Paper Title | FD-RAG: Federated Dual-System Retrieval-Augmented Generation |
| Problem Addressed | Edge RAG suffers from fragmented knowledge, limited compute, and repeated LLM calls. |
| Aim / Objective | To build a dual-system FedRAG that uses memory first and LLM reasoning only when needed. |
| Privacy Risk Addressed | Keeps raw data local, but shared memories may still leak patterns. |
| Federated Component / Coordination | Aggregates anonymised QA memories across distributed edge devices. |
| RAG Component | Retrieves from memory/evidence and escalates to LLM generation for harder queries. |
| Key Results | Improves accuracy and reduces latency by avoiding unnecessary LLM calls. |
| Future Work Mentioned or Implied | Future work needs stronger privacy analysis for memory aggregation. |
| Relevance to My Topic | Useful for edge or local-device FedRAG design. |
| Identified Gap for My Research | It improves efficiency, but privacy leakage from shared memories is not fully measured. |
| Link | https://www.semanticscholar.org/search?q=FD-RAG%20Federated%20Dual-System%20Retrieval-Augmented%20Generation&sort=relevance |
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
