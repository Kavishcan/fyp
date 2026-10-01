---
tags: [literature, worksheet-import, verification-pending]
paper_no: 18
updated: 2026-09-30
---

# An Efficient and Privacy-Preserving Architecture for Cross-Institutional Collaborative RAG

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A19:N19). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training; Private retrieval and input protection; Healthcare and sensitive-domain applications.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 18 |
| Citation | Chenxin Mao, Shangyu Liu, Zhenzhe Zheng, Fan Wu, Jie Wu and Guihai Chen (2026) |
| Paper Title | An Efficient and Privacy-Preserving Architecture for Cross-Institutional Collaborative RAG |
| Problem Addressed | Cross-institution RAG needs private distributed inference without exposing context. |
| Aim / Objective | To support efficient privacy-preserving collaborative RAG without special hardware. |
| Privacy Risk Addressed | Protects against plaintext context leakage and intermediate-state inversion. |
| Federated Component / Coordination | Institutions collaborate in distributed inference and RAG processing. |
| RAG Component | Combines distributed retrieval with privacy-preserving LLM inference. |
| Key Results | Reports very small utility loss and much lower latency than secure baselines. |
| Future Work Mentioned or Implied | Future work needs broader adversary testing and real institutional workflows. |
| Relevance to My Topic | Relevant because it protects the generation/inference stage of FedRAG. |
| Identified Gap for My Research | It protects inference, but needs to be combined with secure retrieval and routing privacy. |
| Link | https://www.semanticscholar.org/search?q=An%20Efficient%20and%20Privacy-Preserving%20Architecture%20for%20Cross-Institutional%20Collaborative%20RAG&sort=relevance |
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
