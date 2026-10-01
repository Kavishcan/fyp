---
tags: [literature, worksheet-import, verification-pending]
paper_no: 54
updated: 2026-09-30
---

# Private-RAG: Answering Multiple Queries with LLMs while Keeping Your Data Private

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A55:N55). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 54 |
| Citation | Ruihan Wu, Erchi Wang, Zhiyuan Zhang and Yu-Xiang Wang (2025) |
| Paper Title | Private-RAG: Answering Multiple Queries with LLMs while Keeping Your Data Private |
| Problem Addressed | Repeated RAG queries can reveal documents from a sensitive corpus, and single-query privacy budgets add up quickly. |
| Aim / Objective | To answer many queries while keeping document-level privacy useful in practice. |
| Privacy Risk Addressed | Sensitive-document leakage through answers; evaluates membership inference across repeated queries. |
| Federated Component / Coordination | No federated sources. It studies one private external document collection. |
| RAG Component | MuRAG tracks privacy loss per retrieved document; MuRAG-Ada privately chooses query-specific thresholds before generating answers. |
| Key Results | Reports useful answers for hundreds of queries around ε=10; tests a multi-query membership-inference attack. |
| Future Work Mentioned or Implied | Implied: handle repeated overlapping questions better, since exhausted document budgets can reduce later answer quality. |
| Relevance to My Topic | Useful for my document/output privacy tests, but its privacy guarantee is about documents, not hiding the user's query from the service. |
| Identified Gap for My Research | It does not privately choose among distributed sources or protect source-contact patterns. |
| Link | https://arxiv.org/abs/2511.07637 |
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
