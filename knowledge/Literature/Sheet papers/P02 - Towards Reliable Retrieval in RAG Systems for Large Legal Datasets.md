---
tags: [literature, worksheet-import, verification-pending]
paper_no: 2
updated: 2026-09-30
---

# Towards Reliable Retrieval in RAG Systems for Large Legal Datasets

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A3:N3). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Evaluation, failures and domain benchmarks; Healthcare and sensitive-domain applications.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 2 |
| Citation | Markus Reuter, Tobias Lingenberg, Rūta Liepiņa, Francesca Lagioia, Marco Lippi, Giovanni Sartor, Andrea Passerini and Burcu Sayin (2025) |
| Paper Title | Towards Reliable Retrieval in RAG Systems for Large Legal Datasets |
| Problem Addressed | legal docs can be similar so in rag systems mismatch can happen |
| Aim / Objective | make retrieval more reliable for large legal datasets. |
| Privacy Risk Addressed | Main risk is wrong retrieval and hallucination, so cant trust the data |
| Federated Component / Coordination | No federated component. |
| RAG Component | improving the retrieval part for legal data. |
| Key Results | Summary Augmented Chunking (SAC) improves Document-Level Retrieval<br>Mismatch (DRM) |
| Future Work Mentioned or Implied | (i) Extending the presented principle of summa-<br>rization hierarchically, with summaries at the para-<br>graph, section, and document level to provide con-<br>text at multiple granularities. (ii) Applying query<br>optimization methods (e.g., transformation, expan-<br>sion, or routing) to bridge the semantic gap between<br>user questions and the formal language of legal text<br>chunks. (iii) Adding a reranking step where a more<br>powerful model re-evaluates and re-orders the top-<br>k retrieved chunks to improve the final selection<br>before generation. |
| Relevance to My Topic | Useful because my system also needs reliable retrieval, not only privacy.No federated component, but the idea can be useful for legal data silos. |
| Identified Gap for My Research | reliable legal retrieval is studied, but not in a federated privacy-aware setup. |
| Link | https://www.semanticscholar.org/search?q=Towards%20Reliable%20Retrieval%20in%20RAG%20Systems%20for%20Large%20Legal%20Datasets&sort=relevance |
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
