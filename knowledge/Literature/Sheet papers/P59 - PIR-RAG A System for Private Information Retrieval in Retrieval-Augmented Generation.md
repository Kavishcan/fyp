---
tags: [literature, worksheet-import, verification-pending]
paper_no: 59
updated: 2026-09-30
---

# PIR-RAG: A System for Private Information Retrieval in Retrieval-Augmented Generation

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A60:N60). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 59 |
| Citation | Baiqiang Wang, Qian Lou, Mengxin Zheng and Dongfang Zhao (2025) |
| Paper Title | PIR-RAG: A System for Private Information Retrieval in Retrieval-Augmented Generation |
| Problem Addressed | A RAG server normally sees the user's query or embedding, while private retrieval can be too slow when full document text is needed. |
| Aim / Objective | To retrieve RAG-ready content without revealing the chosen cluster to an honest-but-curious server. |
| Privacy Risk Addressed | Query and selected-cluster privacy; it does not claim to hide which independent organization is contacted. |
| Federated Component / Coordination | No federation: one server holds a clustered document collection; the user chooses a cluster locally. |
| RAG Component | Public centroids guide local cluster choice, then lattice-based PIR fetches the whole cluster for local reranking. |
| Key Results | The paper reports better RAG-ready latency than its graph-PIR and Tiptoe-style implementations because content arrives in one private fetch. |
| Future Work Mentioned or Implied | Implied: test multiple independent data holders and reduce the cost of fetching a whole cluster. |
| Relevance to My Topic | Very relevant to private retrieval after my router chooses a source; it gives a concrete PIR design and cost baseline. |
| Identified Gap for My Research | It protects selection within one collection, but not federated source selection or visible node-contact patterns. |
| Link | https://arxiv.org/abs/2509.21325 |
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
