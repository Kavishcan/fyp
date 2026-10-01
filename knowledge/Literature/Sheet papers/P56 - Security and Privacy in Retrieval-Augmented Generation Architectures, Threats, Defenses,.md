---
tags: [literature, worksheet-import, verification-pending]
paper_no: 56
updated: 2026-09-30
---

# Security and Privacy in Retrieval-Augmented Generation: Architectures, Threats, Defenses, and Future Directions for Building Trustworthy Systems

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A57:N57). Original wording is preserved below, including any errors. 

**Reading themes:** Private retrieval and input protection; Integrity, malicious sources and poisoning.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 56 |
| Citation | Balamurugan Palanisamy, G S S Chalapathi, Vikas Hassija and Rajkumar Buyya (2026) |
| Paper Title | Security and Privacy in Retrieval-Augmented Generation: Architectures, Threats, Defenses, and Future Directions for Building Trustworthy Systems |
| Problem Addressed | RAG has privacy and security risks at retrieval, context construction and generation, including federated settings. |
| Aim / Objective | To organize RAG architectures, attacks, defenses and open problems in one survey. |
| Privacy Risk Addressed | Discusses query logs, index/membership inference, poisoning, gradient leakage and collusion. |
| Federated Component / Coordination | Reviews centralized, on-device, federated and hybrid designs; does not propose a new coordinator. |
| RAG Component | Surveys threats and defenses across the full retrieval-to-answer pipeline. |
| Key Results | Provides a threat taxonomy and trade-off discussion; no new end-to-end system results. |
| Future Work Mentioned or Implied | Calls for trustworthy, resilient RAG and stronger evaluation across deployment settings. |
| Relevance to My Topic | Useful for justifying my threat model and choosing leakage and attack tests. |
| Identified Gap for My Research | A survey maps the risks, but does not experimentally validate a private source router. |
| Link | https://arxiv.org/abs/2606.25533 |
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
