---
tags: [literature, worksheet-import, verification-pending]
paper_no: 24
updated: 2026-09-30
---

# Securing Retrieval-Augmented Generation: A Taxonomy of Attacks, Defenses, and Future Directions

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A25:N25). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection; Integrity, malicious sources and poisoning.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 24 |
| Citation | Yuming Xu, Mingtao Zhang, Zhuohan Ge, Haoyang Li, Nicole Hu, Jason Chen Zhang, Qing Li and Lei Chen (2026) |
| Paper Title | Securing Retrieval-Augmented Generation: A Taxonomy of Attacks, Defenses, and Future Directions |
| Problem Addressed | RAG has security risks across indexing, retrieval, context use, and output. |
| Aim / Objective | To organise RAG attacks, defenses, and future directions into a taxonomy. |
| Privacy Risk Addressed | Covers knowledge corruption, access manipulation, context exploitation, and exfiltration. |
| Federated Component / Coordination | No FL component, but the trust boundaries apply strongly to FedRAG. |
| RAG Component | Covers the full RAG knowledge-access pipeline. |
| Key Results | Shows RAG defenses are fragmented and need layered protection. |
| Future Work Mentioned or Implied | Future work should build boundary-aware protection across the whole RAG lifecycle. |
| Relevance to My Topic | Very useful for my threat-model section. |
| Identified Gap for My Research | It gives security taxonomy, but not a tested privacy-aware FedRAG framework. |
| Link | https://www.semanticscholar.org/paper/Securing-Retrieval-Augmented-Generation%3A-A-Taxonomy-Xu-Zhang/c86436c4dd86c430660038321482d6e97c810b5d |
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
