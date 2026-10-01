---
tags: [literature, worksheet-import, verification-pending]
paper_no: 19
updated: 2026-09-30
---

# DGRAG: Distributed Graph-based Retrieval-Augmented Generation in Edge-Cloud Systems

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A20:N20). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 19 |
| Citation | Wenqing Zhou, Yuxuan Yan and Qianqian Yang (2025) |
| Paper Title | DGRAG: Distributed Graph-based Retrieval-Augmented Generation in Edge-Cloud Systems |
| Problem Addressed | Centralised RAG over edge data can increase privacy risk, latency, and cloud cost. |
| Aim / Objective | To use graph summaries and edge-cloud coordination for distributed RAG. |
| Privacy Risk Addressed | Reduces raw data centralisation, but summaries can still leak information. |
| Federated Component / Coordination | Edge nodes build local graphs and cloud coordinates using subgraph summaries. |
| RAG Component | Uses local/cloud retrieval and generation depending on the query. |
| Key Results | Improves distributed QA and reduces cloud overhead. |
| Future Work Mentioned or Implied | Future work should protect summaries and edge source selection. |
| Relevance to My Topic | Useful for distributed knowledge-base architecture. |
| Identified Gap for My Research | It keeps raw data local, but summary leakage and source identity leakage remain open. |
| Link | https://www.semanticscholar.org/search?q=DGRAG%20Distributed%20Graph-based%20Retrieval-Augmented%20Generation%20in%20Edge-Cloud%20Systems&sort=relevance |
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
