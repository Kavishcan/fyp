---
tags: [literature, worksheet-import, verification-pending]
paper_no: 14
updated: 2026-09-30
---

# FedRAG: A Framework for Fine-Tuning Retrieval-Augmented Generation Systems

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A15:N15). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 14 |
| Citation | Val Andrei Fajardo, David B. Emerson, Amandeep Singh, Veronica Chatrath, Marcelo Lotif, Ravi Theja, Alex Cheung and Izuki Matsubi (2025) |
| Paper Title | FedRAG: A Framework for Fine-Tuning Retrieval-Augmented Generation Systems |
| Problem Addressed | There is limited tooling for fine-tuning RAG systems in federated settings. |
| Aim / Objective | To provide a framework for centralised and federated RAG fine-tuning. |
| Privacy Risk Addressed | Main risk is model update leakage during federated tuning. |
| Federated Component / Coordination | Supports federated training for retriever and generator modules. |
| RAG Component | Covers fine-tuning of retrieval and generation components. |
| Key Results | Helps convert centralised RAG tuning into federated training tasks. |
| Future Work Mentioned or Implied | Future work should add stronger privacy mechanisms and real multi-client benchmarks. |
| Relevance to My Topic | Useful if my project needs an implementation framework. |
| Identified Gap for My Research | It focuses on fine-tuning, not privacy-aware runtime routing or leakage evaluation. |
| Link | https://www.semanticscholar.org/search?q=FedRAG%20A%20Framework%20for%20Fine-Tuning%20Retrieval-Augmented%20Generation%20Systems&sort=relevance |
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
