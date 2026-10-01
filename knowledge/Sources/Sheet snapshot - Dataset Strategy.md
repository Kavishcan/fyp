---
tags: [source-snapshot]
retrieved: 2026-09-30
---

# Sheet Snapshot - Dataset Strategy

[Live tab](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=3100103). Read-only snapshot of populated cells retrieved for this update; blank trailing rows are omitted. These are source working notes, not validated findings. Cell display text is preserved, with table escaping and line breaks normalised.

| Dataset strategy: data used in my current experiments |  |  |  |  |
| --- | --- | --- | --- | --- |
| Dataset | What each client/node holds | Questions or records used | What I tested | Dataset link |
| FeB4RAG | 13 BEIR-backed source collections (not all 16 original engines) | 785 judged requests for routing; 640 for leakage | Correct source selection and what contacted sources reveal | https://github.com/ielab/FeB4RAG |
| BEIR | Local document text; sampled source profiles and simulated nodes | Selected corpora and their queries/qrels | Local retrieval, privacy controls, scaling, bytes and latency | https://github.com/beir-cellar/beir |
| MIRAGE | 8 BEIR document nodes: 3 medical, 5 distractors | 150 questions, 30 from each of 5 medical QA subsets | Final multiple-choice answer accuracy with/without retrieved evidence | https://github.com/gzxiong/MIRAGE |
| PMC-Patients | 5,000 public case-report summaries split into 8 simulated hospitals | 986 patient queries; k-means and Dirichlet partitions | Blind-unlock retrieval, query/contact leakage, disclosed records and cost | https://huggingface.co/datasets/zhengyun21/PMC-Patients |
| Synthetic privacy cases | Fictional sensitive queries and attack inputs over BEIR-backed nodes | 200 privacy cases and 60 forged-profile cases; separate fake PII canaries | Whether fake sensitive values leak or a forged source is selected | https://github.com/Kavishcan/fedrag-dataset/tree/main/data/processed/privacy |
| Important notes |  |  |  |  |
| Are these real hospitals? | No. The hospital and client labels are simulated partitions of public data. |  |  |  |
| Are BioASQ, MedQA, etc. clients? | No. They are question groups inside MIRAGE. The document nodes come from BEIR. |  |  |  |
| Did I train a router? | No. Current experiments use pretrained embeddings and training-free routing. |  |  |  |
| What is not a current result? | MultiHop-RAG is prepared locally but not evaluated here; full MedRAG corpora are not used. |  |  |  |
| What comes next? | Test blind-mode answer accuracy, finish paired comparisons and check more PMC partitions. |  |  |  |

Interpretation and conflicts: [[Source reconciliation]]. Current study: [[Home]].
