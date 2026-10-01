---
tags: [literature, worksheet-import, verification-pending]
paper_no: 38
updated: 2026-09-30
---

# RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A39:N39). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 38 |
| Citation | Dongyu Ru, Lin Qiu, Xiangkun Hu, Tianhang Zhang, Peng Shi, Shuaichen Chang, Cheng Jiayang, Cunxiang Wang, Shichao Sun, Huanyu Li, Zizhao Zhang, Binjie Wang, Jiarong Jiang, Tong He, Zhiguo Wang, Pengfei Liu, Yue Zhang and Zheng Zhang (2024) |
| Paper Title | RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation |
| Problem Addressed | Coarse RAG metrics hide whether retrieval or generation caused failure. |
| Aim / Objective | To diagnose RAG systems with fine-grained component-level metrics. |
| Privacy Risk Addressed | Diagnostics may expose private evidence if used on sensitive data. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Measures retrieval quality and generation support at a fine-grained level. |
| Key Results | Better matches human judgment and reveals RAG design trade-offs. |
| Future Work Mentioned or Implied | Future work should extend diagnostics to broader deployment settings. |
| Relevance to My Topic | Useful for finding which part of my FedRAG system fails. |
| Identified Gap for My Research | Need private diagnostics for distributed evidence and generated claims. |
| Link | https://www.semanticscholar.org/search?q=RAGChecker%20A%20Fine-grained%20Framework%20for%20Diagnosing%20Retrieval-Augmented%20Generation&sort=relevance |
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
