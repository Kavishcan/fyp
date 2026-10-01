---
tags: [literature, worksheet-import, verification-pending]
paper_no: 12
updated: 2026-09-30
---

# FRAG: Toward Federated Vector Database Management for Collaborative and Secure Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A13:N13). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training; Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 12 |
| Citation | Dongfang Zhao (2024) |
| Paper Title | FRAG: Toward Federated Vector Database Management for Collaborative and Secure Retrieval-Augmented Generation |
| Problem Addressed | Distributed vector search for RAG can leak query vectors and document vectors. |
| Aim / Objective | To enable secure federated vector database search for collaborative RAG. |
| Privacy Risk Addressed | Protects query vectors, data vectors, and cross-party inference risks. |
| Federated Component / Coordination | Multiple parties keep their own vector databases and perform secure search. |
| RAG Component | Secure retrieval layer supplies results for downstream RAG generation. |
| Key Results | Encrypted federated ANN search can be practical with caching optimisations. |
| Future Work Mentioned or Implied | Future work should connect secure retrieval with full RAG generation and policy control. |
| Relevance to My Topic | Useful for my privacy-preserving retrieval component. |
| Identified Gap for My Research | It protects retrieval, but not full prompt, output, and routing privacy. |
| Link | https://www.semanticscholar.org/search?q=FRAG%20Toward%20Federated%20Vector%20Database%20Management%20for%20Collaborative%20and%20Secure%20Retrieval-Augmented%20Generation&sort=relevance |
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
