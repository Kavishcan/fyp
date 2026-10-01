---
tags: [literature, worksheet-import, verification-pending]
paper_no: 36
updated: 2026-09-30
---

# Benchmarking Large Language Models in Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A37:N37). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 36 |
| Citation | Jiawei Chen, Hongyu Lin, Xianpei Han and Le Sun (2023) |
| Paper Title | Benchmarking Large Language Models in Retrieval-Augmented Generation |
| Problem Addressed | LLMs do not always use retrieved evidence correctly in RAG. |
| Aim / Objective | To benchmark LLM behaviour under retrieved evidence. |
| Privacy Risk Addressed | Focuses on reliability risks, not privacy. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Tests generation under retrieved context, noise, and counterfactual evidence. |
| Key Results | Shows LLMs struggle to reject false or irrelevant retrieved information. |
| Future Work Mentioned or Implied | Future work should improve evidence use and rejection ability. |
| Relevance to My Topic | Useful for testing answer reliability in my FedRAG system. |
| Identified Gap for My Research | Need FedRAG tests with noisy or malicious clients plus privacy constraints. |
| Link | https://www.semanticscholar.org/search?q=Benchmarking%20Large%20Language%20Models%20in%20Retrieval-Augmented%20Generation&sort=relevance |
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
