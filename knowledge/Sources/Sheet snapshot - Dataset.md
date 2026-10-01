---
tags: [source-snapshot]
retrieved: 2026-09-30
---

# Sheet Snapshot - Dataset

[Live tab](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=3100101). Read-only snapshot of populated cells retrieved for this update; blank trailing rows are omitted. These are source working notes, not validated findings. Cell display text is preserved, with table escaping and line breaks normalised.

| No. | Dataset | Subset actually used | Client/source setup | What it tests | Reported measures | Dataset link | Important limit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | FeB4RAG | 785 judged requests in routing study; 640 in leakage study; graded source qrels | 13 of 16 engines with local BEIR text | Whether routing reaches relevant sources; whether contacts reveal query topic | nDCG@1, MRR, captured gain, topic inference | https://github.com/ielab/FeB4RAG | FeB4RAG result pools are rankings, not full documents; the 3 non-BEIR engines were excluded. |
| 2 | BEIR corpora | Document text and qrels from selected corpora; 1,500 sampled documents per source for FeB4RAG profiles | 13 source corpora; medical/distractor nodes and simulated shards for other tests | Build local indexes/profiles; test retrieval, privacy controls, transport and scaling | Recall@K, latency, bytes, contacts | https://github.com/beir-cellar/beir | These are public corpora split into simulated nodes, not private institutions. |
| 3 | MIRAGE | 150 medical multiple-choice questions: 30 each from BioASQ, MedMCQA, MedQA, MMLU-medical and PubMedQA | 8 BEIR document nodes: 3 medical sources and 5 distractors | Check whether retrieved evidence improves generated medical answers | MCQ accuracy, contacts, generation time | https://github.com/gzxiong/MIRAGE | Only 150 of the benchmark's 7,663 questions were tested; these question subsets are not clients. Blind-mode answer accuracy is not yet reported. |
| 4 | PMC-Patients | 5,000 patient summaries and 986 evaluated patient queries | 8 simulated hospital partitions; k-means and Dirichlet splits | Main blind-unlock comparison: private queries and constant contact pattern versus retrieval quality | MRR, P@10, nDCG@10, topic inference, records opened, time, bytes | https://huggingface.co/datasets/zhengyun21/PMC-Patients | Public case-report summaries, not records from eight real hospitals; results vary with partition and probe count. |
| 5 | Project synthetic privacy cases | 200 fictional sensitive-query cases, 60 forged-profile attacks; separate fictional PII canaries for de-identification | Run over BEIR-backed simulated nodes and attack node | Check query exposure, profile hijacking and whether fake identifiers leave a node | Values exposed, attack selection/citation, identifier leakage | https://github.com/Kavishcan/fedrag-dataset/tree/main/data/processed/privacy | Generated test data, not a real patient dataset; de-identification results are not clinical validation. |

Interpretation and conflicts: [[Source reconciliation]]. Current study: [[Home]].
