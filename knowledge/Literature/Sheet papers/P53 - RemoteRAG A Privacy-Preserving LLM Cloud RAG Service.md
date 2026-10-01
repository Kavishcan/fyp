---
tags: [literature, worksheet-import, verification-pending]
paper_no: 53
updated: 2026-09-30
---

# RemoteRAG: A Privacy-Preserving LLM Cloud RAG Service

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A54:N54). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Source routing, budgets and efficiency; Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 53 |
| Citation | Yihang Cheng, Lan Zhang, Junyang Wang, Mu Yuan and Yunhao Yao (2024) |
| Paper Title | RemoteRAG: A Privacy-Preserving LLM Cloud RAG Service |
| Problem Addressed | Sending a query or query embedding to a cloud RAG service can reveal the user's private intent. |
| Aim / Objective | To protect cloud RAG queries while keeping retrieval accurate and efficient. |
| Privacy Risk Addressed | Query leakage and embedding inversion, including information inferred from the returned relevant documents. |
| Federated Component / Coordination | No federated source routing; it is a user-to-cloud RAG service. |
| RAG Component | Perturbs the query embedding with DistanceDP, searches a reduced document range, and then performs normal RAG retrieval and generation. |
| Key Results | Reports resistance to embedding-inversion attacks with no retrieval loss in the tested settings, using about 0.67 seconds and 46.66 KB. |
| Future Work Mentioned or Implied | It should be extended to multiple distributed sources and evaluated for source identity and routing-pattern leakage. |
| Relevance to My Topic | Useful for defining and testing query exposure before my router contacts distributed clients. |
| Identified Gap for My Research | It protects one cloud retrieval service, but does not select among many sources or handle source trust and profile hijacking. |
| Link | https://www.semanticscholar.org/search?q=RemoteRAG%20A%20Privacy-Preserving%20LLM%20Cloud%20RAG%20Service&sort=relevance |
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
