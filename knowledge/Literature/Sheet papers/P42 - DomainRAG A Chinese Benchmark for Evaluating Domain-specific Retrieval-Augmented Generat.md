---
tags: [literature, worksheet-import, verification-pending]
paper_no: 42
updated: 2026-09-30
---

# DomainRAG: A Chinese Benchmark for Evaluating Domain-specific Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A43:N43). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 42 |
| Citation | Shuting Wang, Jiongnan Liu, Shiren Song, Jiehan Cheng, Yuqi Fu, Peidong Guo, Kun Fang, Yutao Zhu and Zhicheng Dou (2024) |
| Paper Title | DomainRAG: A Chinese Benchmark for Evaluating Domain-specific Retrieval-Augmented Generation |
| Problem Addressed | General RAG benchmarks do not properly test expert and domain-specific questions. |
| Aim / Objective | To build a Chinese college-enrolment benchmark covering six domain RAG abilities. |
| Privacy Risk Addressed | Privacy is not studied, although domain queries and records may be sensitive. |
| Federated Component / Coordination | No federated component; the benchmark uses a central domain corpus. |
| RAG Component | Tests conversational, structured, time-sensitive, noisy and multi-document RAG. |
| Key Results | Closed-book LLMs struggle with domain questions, and current RAG systems still have several weaknesses. |
| Future Work Mentioned or Implied | Future work should improve conversation understanding, denoising, multi-document reasoning and faithfulness. |
| Relevance to My Topic | Useful for showing that different domain clients may need different retrieval behaviour. |
| Identified Gap for My Research | It evaluates domain RAG, but not distributed private data or privacy-aware routing. |
| Link | https://www.semanticscholar.org/search?q=DomainRAG%20A%20Chinese%20Benchmark%20for%20Evaluating%20Domain-specific%20Retrieval-Augmented%20Generation&sort=relevance |
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
