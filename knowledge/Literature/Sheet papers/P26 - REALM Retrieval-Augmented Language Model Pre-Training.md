---
tags: [literature, worksheet-import, verification-pending]
paper_no: 26
updated: 2026-09-30
---

# REALM: Retrieval-Augmented Language Model Pre-Training

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A27:N27). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 26 |
| Citation | Kelvin Guu, Kenton Lee, Zora Tung, Panupong Pasupat and Ming-Wei Chang (2020) |
| Paper Title | REALM: Retrieval-Augmented Language Model Pre-Training |
| Problem Addressed | Language models need modular access to external knowledge instead of memorising facts. |
| Aim / Objective | To pretrain a model that retrieves documents during learning and inference. |
| Privacy Risk Addressed | No privacy mechanism; retrieved evidence could leak in sensitive settings. |
| Federated Component / Coordination | No federated part; uses a central Wikipedia-style corpus. |
| RAG Component | Integrates latent retrieval into pretraining and QA inference. |
| Key Results | Improves open-domain QA and makes knowledge access more modular. |
| Future Work Mentioned or Implied | Future work should improve scalable retrieval and knowledge updating. |
| Relevance to My Topic | Useful as a foundation for trainable retrievers. |
| Identified Gap for My Research | Trainable retrieval is shown, but not over private distributed corpora. |
| Link | https://www.semanticscholar.org/search?q=REALM%20Retrieval-Augmented%20Language%20Model%20Pre-Training&sort=relevance |
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
