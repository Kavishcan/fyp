---
tags: [literature, worksheet-import, verification-pending]
paper_no: 43
updated: 2026-09-30
---

# Unanswerability Evaluation for Retrieval Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A44:N44). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 43 |
| Citation | Xiangyu Peng, Prafulla Kumar Choubey, Caiming Xiong and Chien-Sheng Wu (2024) |
| Paper Title | Unanswerability Evaluation for Retrieval Augmented Generation |
| Problem Addressed | RAG evaluation usually assumes every question has an answer in the knowledge base. |
| Aim / Objective | To create UAEval4RAG for testing whether a RAG system rejects unanswerable questions. |
| Privacy Risk Addressed | Privacy is not the focus; the main risk is giving unsupported or unsafe answers. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Creates six types of unanswerable questions and tests retrieval, rewriting, reranking, prompting and generation. |
| Key Results | Shows that component and prompt choices affect the balance between answering and correctly refusing. |
| Future Work Mentioned or Implied | Future work should improve rejection on more knowledge bases and real applications. |
| Relevance to My Topic | Useful because a selected client may not contain enough evidence and my system should be able to stop. |
| Identified Gap for My Research | Unanswerability is tested centrally, not across federated clients or under privacy constraints. |
| Link | https://www.semanticscholar.org/search?q=Unanswerability%20Evaluation%20for%20Retrieval%20Augmented%20Generation&sort=relevance |
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
