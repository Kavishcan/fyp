---
tags: [literature, worksheet-import, verification-pending]
paper_no: 61
updated: 2026-09-30
---

# Private Web Search with Tiptoe

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A62:N62). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 61 |
| Citation | Alexandra Henzinger, Emma Dauterman, Henry Corrigan-Gibbs and Nickolai Zeldovich (2023) |
| Paper Title | Private Web Search with Tiptoe |
| Problem Addressed | Normal semantic search reveals what a user searched for to the search provider. |
| Aim / Objective | To run private semantic search at web scale without trusted hardware or non-colluding servers. |
| Privacy Risk Addressed | Hides the query from search servers; the web corpus itself is not treated as private node-owned data. |
| Federated Component / Coordination | A 45-server search cluster, not multiple independent federated knowledge holders. |
| RAG Component | Encrypted nearest-neighbor scoring retrieves search results; no answer-generation stage is studied. |
| Key Results | Searches 360 million pages with 2.7-second end-to-end latency in the reported setup, but ranks below a non-private neural search baseline. |
| Future Work Mentioned or Implied | Implied: improve exact-match quality and adapt private search to full-content RAG and independent source owners. |
| Relevance to My Topic | Important cryptographic comparison for hiding query meaning during retrieval. |
| Identified Gap for My Research | Tiptoe does not by itself solve private source routing, document authorization or RAG generation. |
| Link | https://doi.org/10.1145/3600006.3613134 |
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
