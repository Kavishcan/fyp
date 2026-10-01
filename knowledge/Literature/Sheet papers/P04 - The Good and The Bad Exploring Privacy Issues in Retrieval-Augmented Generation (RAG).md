---
tags: [literature, worksheet-import, verification-pending]
paper_no: 4
updated: 2026-09-30
---

# The Good and The Bad: Exploring Privacy Issues in Retrieval-Augmented Generation (RAG)

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A5:N5). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 4 |
| Citation | Shenglai Zeng, Jiankun Zhang, Pengfei He, Yue Xing, Yiding Liu, Han Xu, Jie Ren, Shuaiqiang Wang, Dawei Yin, Yi Chang and Jiliang Tang (2024) |
| Paper Title | The Good and The Bad: Exploring Privacy Issues in Retrieval-Augmented Generation (RAG) |
| Problem Addressed | RAG can leak private retrieval database content through prompts and generated answers. |
| Aim / Objective | To study the good and bad privacy effects of using retrieval with LLMs. |
| Privacy Risk Addressed | Covers retrieval database leakage, prompt leakage, output leakage, and training data leakage. |
| Federated Component / Coordination | No federated part; it studies privacy mainly in a normal RAG setting. |
| RAG Component | Looks at how retrieved context affects generation and privacy leakage. |
| Key Results | Shows that RAG can reduce some model-memory leakage but can also expose private retrieved data. |
| Future Work Mentioned or Implied | Future work should build stronger privacy protection for RAG systems. |
| Relevance to My Topic | Important for my topic because it gives the privacy threat model for RAG. |
| Identified Gap for My Research | Privacy risks are shown clearly, but there is no complete federated privacy-aware solution. |
| Link | https://www.semanticscholar.org/search?q=The%20Good%20and%20The%20Bad%3A%20Exploring%20Privacy%20Issues%20in%20Retrieval-Augmented%20Generation%20RAG&sort=relevance |
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
