---
tags: [literature, worksheet-import, verification-pending]
paper_no: 62
updated: 2026-09-30
---

# Fair and Budget-Controlled Federated Retrieval-Augmented Generation for Open-Domain QA

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A63:N63). Original wording is preserved below, including any errors. 

**Reading themes:** Source routing, budgets and efficiency; Evaluation, failures and domain benchmarks.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 62 |
| Citation | Mingyu Ding, Zifeng Gu, Junnan Yang, Qilong Wu and Xin Wang (2026) |
| Paper Title | Fair and Budget-Controlled Federated Retrieval-Augmented Generation for Open-Domain QA |
| Problem Addressed | Federated RAG can look better simply because it sends more candidates to global reranking than a centralized baseline. |
| Aim / Objective | To compare centralized and federated RAG using matched candidate budgets. |
| Privacy Risk Addressed | Raw client data stays local during federated tuning, but query and source-contact privacy are not evaluated. |
| Federated Component / Coordination | Five uneven non-IID SQuAD clients; local retrieval, server reranking and FedAvg of LoRA updates. |
| RAG Component | Each client uses BM25 plus FAISS; fair/expanded settings send 1 or 3 candidates per client before top-5 generation. |
| Key Results | Matched budget: federated Recall@5 69.5 vs centralized 71.3; expanded federated budget reaches 82.4. Fragmented evidence performs worse. |
| Future Work Mentioned or Implied | Authors suggest adaptive budget allocation, query-aware client selection and larger, more diverse federated studies. |
| Relevance to My Topic | Useful for designing fair retrieval comparisons and tests for evidence split across clients. |
| Identified Gap for My Research | All five clients are queried; selective private routing and exposure per contacted client remain open. |
| Link | https://doi.org/10.1109/ICICC71012.2026.11637874 |
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
