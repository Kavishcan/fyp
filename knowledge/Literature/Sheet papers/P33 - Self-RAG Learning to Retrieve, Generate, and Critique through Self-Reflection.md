---
tags: [literature, worksheet-import, verification-pending]
paper_no: 33
updated: 2026-09-30
---

# Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A34:N34). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 33 |
| Citation | Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil and Hannaneh Hajishirzi (2023) |
| Paper Title | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection |
| Problem Addressed | Fixed retrieval can add irrelevant passages and reduce answer quality. |
| Aim / Objective | To let the model decide when to retrieve, generate, and critique. |
| Privacy Risk Addressed | Retrieved evidence and reflection traces may leak sensitive information. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Uses adaptive retrieval, generation, and self-critique. |
| Key Results | Improves factuality and citation accuracy across tasks. |
| Future Work Mentioned or Implied | Future work should improve controllable retrieval and critique. |
| Relevance to My Topic | Useful for reducing unnecessary retrieval in FedRAG. |
| Identified Gap for My Research | Need adaptive retrieval that also protects query and source exposure. |
| Link | https://www.semanticscholar.org/search?q=Self-RAG%20Learning%20to%20Retrieve%20Generate%20and%20Critique%20through%20Self-Reflection&sort=relevance |
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
