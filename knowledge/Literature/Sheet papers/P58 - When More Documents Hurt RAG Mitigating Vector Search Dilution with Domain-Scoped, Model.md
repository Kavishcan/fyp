---
tags: [literature, worksheet-import, verification-pending]
paper_no: 58
updated: 2026-09-30
---

# When More Documents Hurt RAG: Mitigating Vector Search Dilution with Domain-Scoped, Model-Agnostic Retrieval

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A59:N59). Original wording is preserved below, including any errors. 

**Reading themes:** RAG foundations and evidence organisation; Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 58 |
| Citation | Nabaraj Subedi, Ahmed Abdelaty and Shivanand Venkanna Sheshappanavar (2026) |
| Paper Title | When More Documents Hurt RAG: Mitigating Vector Search Dilution with Domain-Scoped, Model-Agnostic Retrieval |
| Problem Addressed | Large mixed document stores can return similar but wrong chunks; more documents can hurt answer quality. |
| Aim / Objective | To use domain scoping so RAG searches the right part of a large corpus. |
| Privacy Risk Addressed | Privacy is not evaluated; explicit organizational metadata and chosen scope could reveal source interests if used across silos. |
| Federated Component / Coordination | No federated nodes; scoping is inside a managed corpus. |
| RAG Component | Uses metadata-based domain scoping and compares routing/orchestration variants before synthesis. |
| Key Results | On 200 expert-validated queries, domain scoping improves P@10 from 0.77 to 0.86. |
| Future Work Mentioned or Implied | Authors note that manual scopes and available metadata limit generalization; larger models remain untested. |
| Relevance to My Topic | Shows why good source selection matters, but also warns that more agent steps can hurt faithfulness. |
| Identified Gap for My Research | It tests scoping quality, not private matching or hiding which independent node was selected. |
| Link | https://arxiv.org/abs/2606.11350 |
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
