---
tags: [literature, worksheet-import, verification-pending]
paper_no: 60
updated: 2026-09-30
---

# GoldenRetriever: Non-Interactive Homomorphic Encrypted Retrieval for Privacy-Preserving RAG

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A61:N61). Original wording is preserved below, including any errors. 

**Reading themes:** Source routing, budgets and efficiency; Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 60 |
| Citation | Yang Gao, Gang Quan, Scott Piersall, Qian Lou, Dongdong Wang and Liqiang Wang (2026) |
| Paper Title | GoldenRetriever: Non-Interactive Homomorphic Encrypted Retrieval for Privacy-Preserving RAG |
| Problem Addressed | Encrypted top-k ranking can be slow, and sending plaintext queries or selected document IDs leaks information. |
| Aim / Objective | To select useful documents under encryption without an interactive ranking protocol. |
| Privacy Risk Addressed | Protects query, similarity scores and selected indices against an honest-but-curious retrieval server; the server's corpus remains plaintext. |
| Federated Component / Coordination | No federated coordination; evaluation uses candidate sets held by a retrieval server. |
| RAG Component | CKKS computes encrypted similarity and threshold selection, then returns masked document representations. |
| Key Results | Reports competitive retrieval quality and lower latency than ranking-based encrypted methods on tested benchmarks. |
| Future Work Mentioned or Implied | Implied: test malicious servers, larger candidate sets and distributed private corpora. |
| Relevance to My Topic | Useful secure-selection building block, but its trust and corpus assumptions differ from private federated nodes. |
| Identified Gap for My Research | It does not protect node-owned documents from the server or conceal which federated node is contacted. |
| Link | https://arxiv.org/abs/2607.29019 |
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
