---
tags: [literature, worksheet-import, verification-pending]
paper_no: 27
updated: 2026-09-30
---

# Dense Passage Retrieval for Open-Domain Question Answering

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A28:N28). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 27 |
| Citation | Vladimir Karpukhin, Barlas Oğuz, Sewon Min, Patrick Lewis, Ledell Wu, Sergey Edunov, Danqi Chen and Wen-tau Yih (2020) |
| Paper Title | Dense Passage Retrieval for Open-Domain Question Answering |
| Problem Addressed | Sparse keyword retrieval can miss semantic matches in open-domain QA. |
| Aim / Objective | To train dense passage retrievers for better semantic retrieval. |
| Privacy Risk Addressed | Embeddings and retrieved passages may leak meaning in private systems. |
| Federated Component / Coordination | No federated component; uses a central passage index. |
| RAG Component | Dense vector retrieval provides top-k passages for QA/RAG. |
| Key Results | Dense retrieval improves passage retrieval and downstream QA accuracy. |
| Future Work Mentioned or Implied | Future work should improve retriever training and robustness. |
| Relevance to My Topic | Important because many RAG systems use dense retrieval. |
| Identified Gap for My Research | Need privacy-preserving dense retrieval and embedding protection in FedRAG. |
| Link | https://www.semanticscholar.org/search?q=Dense%20Passage%20Retrieval%20for%20Open-Domain%20Question%20Answering&sort=relevance |
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
