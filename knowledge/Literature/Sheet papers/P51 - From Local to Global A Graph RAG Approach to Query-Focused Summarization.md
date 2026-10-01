---
tags: [literature, worksheet-import, verification-pending]
paper_no: 51
updated: 2026-09-30
---

# From Local to Global: A Graph RAG Approach to Query-Focused Summarization

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A52:N52). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 51 |
| Citation | Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt and Jonathan Larson (2024) |
| Paper Title | From Local to Global: A Graph RAG Approach to Query-Focused Summarization |
| Problem Addressed | Normal vector RAG struggles with broad questions about the main themes of a whole document collection. |
| Aim / Objective | To build GraphRAG using entity graphs, community summaries and query-focused summarisation. |
| Privacy Risk Addressed | It works with private corpora, but gives no formal privacy protection for extracted entities or summaries. |
| Federated Component / Coordination | No federated component; the graph and summaries are built centrally. |
| RAG Component | Uses graph indexing, community detection, partial answers and final answer aggregation. |
| Key Results | Improves the comprehensiveness and diversity of answers to global questions compared with naive RAG. |
| Future Work Mentioned or Implied | Future work should reduce indexing cost and support changing, larger and more private corpora. |
| Relevance to My Topic | Useful for combining higher-level summaries returned by several clients. |
| Identified Gap for My Research | Building one central graph may expose private client documents, entities and relationships. |
| Link | https://www.semanticscholar.org/search?q=From%20Local%20to%20Global%20A%20Graph%20RAG%20Approach%20to%20Query-Focused%20Summarization&sort=relevance |
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
