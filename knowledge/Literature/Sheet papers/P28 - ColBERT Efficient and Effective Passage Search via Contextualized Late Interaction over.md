---
tags: [literature, worksheet-import, verification-pending]
paper_no: 28
updated: 2026-09-30
---

# ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A29:N29). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 28 |
| Citation | Omar Khattab and Matei Zaharia (2020) |
| Paper Title | ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT |
| Problem Addressed | Cross-encoder retrieval is accurate but expensive for large-scale search. |
| Aim / Objective | To make neural passage retrieval efficient with late interaction. |
| Privacy Risk Addressed | Token embeddings may leak document content in private deployments. |
| Federated Component / Coordination | No federated component; central searchable corpus is assumed. |
| RAG Component | Uses late-interaction dense retrieval/reranking. |
| Key Results | Gives strong retrieval effectiveness with lower query cost. |
| Future Work Mentioned or Implied | Future work should improve scalable neural retrieval. |
| Relevance to My Topic | Useful as a retrieval/reranking baseline. |
| Identified Gap for My Research | High-quality retrieval still needs adaptation to private federated indexes. |
| Link | https://www.semanticscholar.org/search?q=ColBERT%20Efficient%20and%20Effective%20Passage%20Search%20via%20Contextualized%20Late%20Interaction%20over%20BERT&sort=relevance |
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
