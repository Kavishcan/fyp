---
tags: [literature, worksheet-import, verification-pending]
paper_no: 25
updated: 2026-09-30
---

# Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A26:N26). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 25 |
| Citation | Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel and Douwe Kiela (2020) |
| Paper Title | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks |
| Problem Addressed | LLMs struggle with knowledge-intensive tasks when knowledge is only stored in parameters. |
| Aim / Objective | To combine parametric generation with retrieved external knowledge. |
| Privacy Risk Addressed | Privacy is not studied; retrieved passages can leak if data is sensitive. |
| Federated Component / Coordination | No federated component; it assumes a central knowledge index. |
| RAG Component | Introduces the basic retrieval plus generation RAG pipeline. |
| Key Results | Improves factuality and performance on knowledge-intensive NLP tasks. |
| Future Work Mentioned or Implied | Future work focuses on better retrieval-generation integration and updateable memory. |
| Relevance to My Topic | This is the baseline architecture my FedRAG idea extends. |
| Identified Gap for My Research | Original RAG assumes centralised accessible documents, not private distributed data. |
| Link | https://www.semanticscholar.org/search?q=Retrieval-Augmented%20Generation%20for%20Knowledge-Intensive%20NLP%20Tasks&sort=relevance |
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
