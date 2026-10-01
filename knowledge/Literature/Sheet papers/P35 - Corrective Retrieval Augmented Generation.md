---
tags: [literature, worksheet-import, verification-pending]
paper_no: 35
updated: 2026-09-30
---

# Corrective Retrieval Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A36:N36). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation; Integrity, malicious sources and poisoning.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 35 |
| Citation | Shi-Qi Yan, Jia-Chen Gu, Yun Zhu and Zhen-Hua Ling (2024) |
| Paper Title | Corrective Retrieval Augmented Generation |
| Problem Addressed | RAG can fail badly when retrieved documents are irrelevant or misleading. |
| Aim / Objective | To correct weak retrieval before generating the final answer. |
| Privacy Risk Addressed | Web fallback and evidence filtering can expose private queries. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Evaluates retrieval quality, corrects evidence, and then generates. |
| Key Results | Improves RAG robustness across multiple datasets. |
| Future Work Mentioned or Implied | Future work should improve retrieval evaluators and evidence filtering. |
| Relevance to My Topic | Useful for handling wrong retrieval in FedRAG. |
| Identified Gap for My Research | Need corrective retrieval without leaking private queries or evidence. |
| Link | https://www.semanticscholar.org/search?q=Corrective%20Retrieval%20Augmented%20Generation&sort=relevance |
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
