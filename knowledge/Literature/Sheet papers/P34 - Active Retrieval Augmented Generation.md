---
tags: [literature, worksheet-import, verification-pending]
paper_no: 34
updated: 2026-09-30
---

# Active Retrieval Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A35:N35). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 34 |
| Citation | Zhengbao Jiang, Frank F. Xu, Luyu Gao, Zhiqing Sun, Qian Liu, Jane Dwivedi-Yu, Yiming Yang, Jamie Callan and Graham Neubig (2023) |
| Paper Title | Active Retrieval Augmented Generation |
| Problem Addressed | One-time retrieval is weak for long-form answers with changing information needs. |
| Aim / Objective | To retrieve actively during generation when more evidence is needed. |
| Privacy Risk Addressed | Repeated generated search queries can leak user intent and intermediate text. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Uses iterative retrieval while the answer is being generated. |
| Key Results | Active retrieval improves long-form generation quality and factuality. |
| Future Work Mentioned or Implied | Future work should improve uncertainty signals and retrieval timing. |
| Relevance to My Topic | Relevant for multi-step FedRAG workflows. |
| Identified Gap for My Research | Need private active retrieval so intermediate queries do not leak to clients. |
| Link | https://www.semanticscholar.org/search?q=Active%20Retrieval%20Augmented%20Generation%20FLARE&sort=relevance |
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
