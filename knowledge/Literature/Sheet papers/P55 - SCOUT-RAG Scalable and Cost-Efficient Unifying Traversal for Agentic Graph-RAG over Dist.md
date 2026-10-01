---
tags: [literature, worksheet-import, verification-pending]
paper_no: 55
updated: 2026-09-30
---

# SCOUT-RAG: Scalable and Cost-Efficient Unifying Traversal for Agentic Graph-RAG over Distributed Domains

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A56:N56). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 55 |
| Citation | Longkun Li, Yuanben Zou, Jinghan Wu, Yuqing Wen, Jing Li, Hangwei Qian and Ivor Tsang (2026) |
| Paper Title | SCOUT-RAG: Scalable and Cost-Efficient Unifying Traversal for Agentic Graph-RAG over Distributed Domains |
| Problem Addressed | Distributed graph sources are expensive to search exhaustively, and useful evidence may span several domains. |
| Aim / Objective | To select domains and graph-traversal depth adaptively under a cost budget. |
| Privacy Risk Addressed | Keeps raw graphs with data holders; does not demonstrate formal query or source-contact privacy. |
| Federated Component / Coordination | Independent domains keep local graphs; agents decide when to contact more domains or explore deeper. |
| RAG Component | Four agents estimate relevance, expand retrieval, set traversal depth and synthesize an answer. |
| Key Results | On 89 multi-domain queries, approaches centralized DRIFT quality with over 4x fewer tokens. |
| Future Work Mentioned or Implied | Implied: test wider deployments and explicit leakage/attack measures for cross-domain routing. |
| Relevance to My Topic | A close routing comparison: training-free domain selection and adaptive search are already studied here. |
| Identified Gap for My Research | Its reported privacy constraint is data locality; private query matching and access-pattern protection still need direct evaluation. |
| Link | https://arxiv.org/abs/2602.08400 |
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
