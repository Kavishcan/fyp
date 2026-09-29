# HyFedRAG-style design vs this project on PMC-Patients

## Verdict

On the dataset HyFedRAG evaluates on, with the same metrics HyFedRAG
reports, a reimplementation of HyFedRAG's **privacy-relevant design** and
this project's pipeline were measured side by side:

| Configuration | MRR | P@10 | nDCG@10 | Hospitals contacted | Question text to hospitals | Topic inference (floor 0.239) | Bytes sent / query |
|---|---:|---:|---:|---:|---:|---:|---:|
| centralized (reference) | 0.443 | 0.109 | 0.409 | — | — | — | — |
| **HyFedRAG-style** (all hospitals, raw local retrieval, server fusion) | **0.444** | 0.109 | 0.409 | **8** | **1.00** | 0.239 | 21,937 |
| normal cosine router (top-4) | 0.444 | 0.108 | 0.408 | 4 | 1.00 | **0.318** | 10,969 |
| ours: PSI to top-4, no cells | 0.382 | 0.091 | 0.342 | 4 | **0.00** | 0.318 | 768 |
| **ours: PSI + anonymity cells** | 0.350 | 0.083 | 0.305 | 4 | **0.00** | **0.254** | 768 |

| Edge de-identification on clean clinical case reports | Documents altered |
|---|---:|
| stock Presidio, PERSON + LOCATION (HyFedRAG uses Presidio) | **84.1%** |
| rules + full-name NER (this project, docs/44) | 11.7% |

(986 queries, 5,000 patients in 8 simulated hospitals, bge-base, seed 11)

**Reading:**

- **HyFedRAG-style broadcast matches centralized retrieval** (MRR 0.444)
  and leaks no topic through the contact pattern (it sits exactly at the
  floor), because it contacts every hospital. Its costs are that **every
  hospital receives every question** and contacts scale with the federation.
- **A normal router halves the contacts at no retrieval cost** but leaks the
  topic (0.318 against a 0.239 floor) and still sends the question to four
  hospitals.
- **This project removes the question from every hospital and brings topic
  inference back near the floor (0.254)**, at four contacts, for a retrieval
  cost of MRR −0.094 (21% relative). The decomposition row shows where the
  cost comes from: **−0.062 from PSI's cluster bucketing** (docs/35: a node
  can only return whole clusters, not rank) and **−0.032 from contacting a
  fixed cell** instead of the best four hospitals.
- **Stock Presidio rewrites 84% of clinical case reports** that contain no
  real identifiers (PMC-Patients is journal-de-identified) — tagging
  diseases, places and eponyms. The configuration used here alters 12%.
  HyFedRAG reports no measurement of this.

The leak on this dataset is weaker than on FeB4RAG (0.318 vs 0.454 for a
top-4 router): similar patients are spread across topic clusters, so the
contact pattern carries less topic information. Cells still remove most of
what is there.

An earlier 300-query run gave cells 0.383 — above the router. With 1,000
queries it is 0.254. With only 8 hospitals and cells of 4 there are just
two cells, and a naive-Bayes observer trained on ~150 queries is unstable;
the 1,000-query figure is the one to report, and the small-sample swing is
itself a caution about attack estimates at this scale.

## Addendum: improvement sweep with time and bytes

Same data, partition and seed; every configuration now also reports records
disclosed, compute time and bytes both ways. Compute is in-process and
sequential (device and hospitals on one core); "received" for PSI is the
full envelope table of every contacted hospital (hex on the wire).

| Configuration | MRR | nDCG@10 | Contacts | Question to hospitals | Topic (floor 0.239) | Records disclosed / q | ms / q (p95) | Sent / q | Received / q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| centralized | 0.443 | 0.409 | — | — | — | — | 0.6 (0.7) | — | — |
| HyFedRAG-style | 0.444 | 0.409 | 8 | **all 8** | 0.239 | 80 | 1.6 (1.7) | 22.0 KB | 0.24 MB |
| cosine router top-4 | 0.444 | 0.408 | 4 | 4 | 0.318 | 40 | 0.9 (1.0) | 11.0 KB | 0.13 MB |
| cosine router top-4, fine routing | 0.442 | 0.407 | 4 | 4 | 0.345 | 40 | 0.9 (1.0) | 11.0 KB | 0.13 MB |
| PSI top-4 | 0.382 | 0.342 | 4 | 0 | 0.318 | 143 | 272 (350) | 768 B | 105 MB |
| PSI + cells (docs/41 default) | 0.350 | 0.305 | 4 | 0 | 0.254 | 143 | 268 (357) | 768 B | 103 MB |
| PSI + cells, fine routing | 0.361 | 0.318 | 4 | 0 | 0.304 | 142 | 269 (359) | 768 B | 103 MB |
| PSI + cells, fine, nprobe 3 | 0.385 | 0.345 | 4 | 0 | 0.304 | 209 | 403 (526) | 1.0 KB | 103 MB |
| PSI + cells, fine, nprobe 4 | 0.394 | 0.351 | 4 | 0 | 0.304 | 276 | 539 (688) | 1.3 KB | 103 MB |
| PSI + 2×2 cells, fine, nprobe 3 | 0.400 | 0.360 | 3.6 | 0 | 0.318 | 192 | 370 (502) | 934 B | 93 MB |
| PSI to all 8, nprobe 2 | 0.384 | 0.344 | 8 | 0 | 0.239 | 285 | 534 (623) | 1.5 KB | 198 MB |
| PSI to all 8, nprobe 3 | 0.409 | 0.373 | 8 | 0 | 0.239 | 426 | 789 (898) | 2.0 KB | 198 MB |
| **blind unlock, P = 8 (docs/47)** | **0.421** | 0.379 | 8 | **0** | **0.239** | 140 | 116 (125) | 4.6 KB | 4.6 KB |

Reading:

- **More probes recover most of PSI's bucketing loss** (nprobe 2 → 4: MRR
  0.361 → 0.394 inside cells) at the price of more records disclosed.
- **Fine routing (a hospital's best public cluster) helps retrieval but
  raises the topic leak** under cells (0.254 → 0.304): with 8 hospitals
  there are only two cells, and a sharper top-1 choice makes the cell
  choice more topic-correlated.
- **PSI to every hospital closes the pattern leak** (floor) with better
  retrieval than cells, but costs ~200 MB and ~0.8 s per question — the
  per-query table download, not the cryptography.
- **Blind unlock (docs/47) removes that cost**: tables downloaded once
  (83 MB for all 8), then every hospital gets the same number of real or
  dummy points. Both leaks at zero, MRR 0.421 at P = 8, a few KB per
  question.

## Setup

`eval/run_hyfedrag_compare.py`. PMC-Patients CSV (Zhao et al., 167k patient
summaries from PubMed Central case reports; downloaded with the user's
approval, 545 MB). Task: patient-to-patient retrieval. Query = a patient
summary; relevant = its annotated **cross-article** similar patients
(same-article siblings, score 2 in the dataset, are trivially similar and are
removed from the corpus). 5,000 corpus patients (all relevant ones plus
random filler), 986 queries with ≥1 relevant patient in the corpus
(mean 2.32). Eight hospitals by spherical k-means on bge-base embeddings
(296–987 patients each). Topic label = the hospital holding most of a
query's relevant patients; learned observer as docs/39, trained on one half
of the queries, tested on the other.

HyFedRAG-style: every hospital retrieves its top-10 over its raw local index
(HyFedRAG's edge retriever sees raw data) and the server fuses by score; the
question text reaches every hospital. Its stock-Presidio edge
de-identification is measured separately as damage to the delivered text.
Ours: cosine rank over public profiles → the fixed cell (size 4) of the top
hospital → PSI (nprobe 2) at each → decrypted passages reranked on the
device → top 10. Bytes in the first table are the request payload only; the addendum
reports both directions.

## What this does not establish

- **This is not HyFedRAG.** It publishes no code. Its heterogeneous-data
  handling (SQL, knowledge graphs), its summarisation step, its three-tier
  cache and its LLM-judge privacy score are not reproduced; only its
  privacy-relevant design (broadcast, raw edge retrieval, Presidio, trusted
  fusion) is.
- **Not comparable to HyFedRAG's published numbers** (e.g. MRR 39.63%): its
  client count, split and task construction are not stated precisely enough
  to replicate.
- One seed; one partition; 8 hospitals. Answer quality was not measured on
  PMC-Patients (no QA labels).
- HyFedRAG's server-side trust assumption is argued in docs/41 and the
  thesis text, not measured here.
- The 8-hospital partition is k-means in the routing embedding, which makes
  both routing and topic inference easier than in a real federation; a
  random or Dirichlet partition is the stated robustness check, not run.

## Reproduce

```
python -m eval.run_hyfedrag_compare --queries 1000
```

Tests: `tests/test_hyfedrag_compare.py` (MRR, P@10, nDCG@10). Test counts are
not retrieval or privacy results.
