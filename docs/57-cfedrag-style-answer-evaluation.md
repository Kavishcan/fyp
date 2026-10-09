# C-FedRAG-style answer evaluation: MIRAGE PubMedQA + BioASQ

Status: measured 2026-10-09. Secondary evidence (answer accuracy); retrieval
and leakage remain the headline metrics (scope note, 2026-10-08).

## Verdict

All 1,118 MIRAGE PubMedQA (500) and BioASQ (618) questions, the question
sets C-FedRAG evaluates (Addison et al., 2024, p.7). 8 simulated hospitals,
local Qwen3.5-9B, 8 passages per answer, dense bge-base ranking everywhere.

| Claim | Holds? | Evidence |
|---|---|---|
| Retrieval without any hospital reading the question improves answers | ✅ | FedSafeRAG P=8 vs closed-book +13.2 points [+10.6, +16.0]; P=24 +14.5 [+11.9, +17.3] |
| FedSafeRAG P=8 answers as well as broadcast (C-FedRAG's setup) | ❌ | −2.0 points [−3.1, −0.9], p < 0.001 (PubMedQA −2.4, BioASQ −1.7, both significant) |
| FedSafeRAG P=24 answers as well as broadcast | ✅ (n.s.) | −0.7 points [−1.5, +0.1], p ≈ 0.11; BioASQ −0.3 (p ≈ 0.65) |
| No hospital reads the question | ✅ | 0 of 8 for FedSafeRAG vs 8 of 8 broadcast, 2 of 8 selective |
| The contact pattern reveals nothing | ✅ | Topic inference 0.166 vs majority floor 0.184 (broadcast and FedSafeRAG: identical traffic to every hospital); selective router **0.637** |
| FedSafeRAG releases fewer records | ❌ | 124 (P=8) and 362 (P=24) per question vs 64 broadcast, 16 selective |
| Retrieval time matters to the user | ❌ (it is small) | Modelled retrieval 89 ms (P=8) / 160 ms (P=24) vs 53 ms broadcast; generation ~6.3–7.9 s median |

**Safe sentence:** "On the 1,118 PubMedQA and BioASQ questions C-FedRAG
evaluates, FedSafeRAG with 24 probes answers within 0.7 points of
broadcasting the question to every hospital (not significant), while no
hospital receives the question and the contact pattern carries no topic
signal. With 8 probes it is 2.0 points lower (significant) and keeps 87%
of broadcast's gain over no retrieval. The cost is records released: 124
(P=8) or 362 (P=24) per question against 64 for broadcast."

Never compare these accuracies with C-FedRAG's published 72.51 average: the
corpus subset, generator and ranker differ. Compare conditions within this
run only.

## Results (8 hospitals, 1,118 questions)

| Condition | PubMedQA | BioASQ | Avg | Source abstract in the 8 passages | Hospitals reading the question | Topic leakage (floor 0.184) | Records released (p95) | KB per question | Hospital CPU ms per question | Retrieval ms, measured / modelled (median) | Generation ms median (p95) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Closed-book | 0.566 | 0.806 | 0.686 | — | 0 | — | 0 | 0 | 0 | — | 853 (1,636) |
| Centralized (one index) | 0.758 | 0.926 | 0.842 | 0.940 | 1 (server) | — | 8 | 12.6 | 6.8 | 15 / 56 | 6,852 (9,522) |
| Broadcast (C-FedRAG-style) | 0.758 | 0.926 | 0.842 | 0.939 | 8 | 0.166 | 64 (64) | 102.5 | 18.5 (103 incl. embedding) | 12 / 53 | 7,950 (9,014)* |
| Selective router (top-2) | 0.746 | 0.921 | 0.833 | 0.905 | 2 | **0.637** | 16 (16) | 24.5 | 11.0 (33 incl. embedding) | 12 / 53 | 6,538 (9,068) |
| **FedSafeRAG P=8** | 0.734 | 0.909 | 0.822 | 0.899 | **0** | 0.166 | 124 (162) | **9.2** | 71.9 | 49 / 89 | 6,258 (8,658) |
| **FedSafeRAG P=24** | 0.746 | 0.922 | 0.834 | 0.922 | **0** | 0.166 | 362 (425) | 25.6 | 211.4 | 120 / 160 | 6,363 (8,785) |

\* Broadcast retrieves the same 8 passages as centralized for 1,106 of 1,118
questions, so those answers are reused (temperature 0 gives the same output);
its generation time comes from the 12 fresh answers.

FedSafeRAG one-time table download: 96.3 MB for 8 hospitals (3,121
clusters, int8 embeddings), once per key epoch, not charged per question.
No question was left unanswered (abstention 0 in every condition).

### Paired bootstrap (5,000 resamples, per question)

| Comparison | All | PubMedQA | BioASQ |
|---|---|---|---|
| FedSafeRAG P=8 − broadcast | −0.020 [−0.031, −0.009], p < 0.001 | −0.024 [−0.042, −0.008], p ≈ 0.004 | −0.016 [−0.031, −0.002], p ≈ 0.04 |
| FedSafeRAG P=24 − broadcast | −0.007 [−0.015, +0.001], p ≈ 0.11 | −0.012 [−0.026, 0.000], p ≈ 0.06 | −0.003 [−0.015, +0.006], p ≈ 0.65 |
| Selective − broadcast | −0.008 [−0.016, 0.000], p ≈ 0.06 | −0.012, p ≈ 0.10 | −0.005, p ≈ 0.40 |
| FedSafeRAG P=24 − P=8 | +0.013 [+0.004, +0.021], p ≈ 0.003 | | |
| Broadcast − closed-book | +0.152 [+0.126, +0.180] | | |
| FedSafeRAG P=8 − closed-book | +0.132 [+0.106, +0.160] | +0.168 | +0.104 |
| FedSafeRAG P=24 − closed-book | +0.145 [+0.119, +0.173] | | |

## Reading the results

- **Accuracy follows whether the source abstract reaches the context.**
  FedSafeRAG P=8 finds it for 89.9% of questions against 93.9% for broadcast;
  P=24 raises that to 92.2% and closes most of the accuracy gap.
- **P is a quality-versus-release dial, not a privacy dial.** Every hospital
  receives exactly P blinded points whatever the question, so leakage is the
  same at P=8 and P=24; records released (124 → 362) and hospital CPU
  (72 → 211 ms) rise.
- **Hospital compute is comparable, not lower.** In C-FedRAG each provider
  embeds the query itself (p.6). Adding that (9.1 ms median per question per
  hospital on this machine) to broadcast gives 103 ms of hospital CPU per
  question across 8 hospitals, against 72 ms for FedSafeRAG P=8 and 211 ms
  for P=24. The raw column (18.5 ms) assumes hospitals receive a ready-made
  embedding, which C-FedRAG's design does not.
- **Traffic per question is 11× lower at P=8** (9.2 vs 102.5 KB), but
  FedSafeRAG needs the one-time 96 MB table download, which broadcast does not.
- **The selective router shows Gap 2 on this data:** contacting the 2
  best-matching hospitals keeps accuracy (−0.8, n.s.) and cuts traffic, but an
  observer who sees only which hospitals were contacted names the topic 63.7%
  of the time against an 18.4% floor.
- **Retrieval time is negligible next to generation:** the extra 36 ms (P=8)
  or 107 ms (P=24) of modelled retrieval is about 1% of the 6–8 s answer.

## Setup

| Item | Value |
|---|---|
| Questions | MIRAGE PubMedQA 500 (yes/no/maybe) + BioASQ 618 (yes/no), all of them |
| PubMed corpus | `eval/build_pubmed_subset.py`: every question's source abstract (3,967 PMIDs, all with text) + relevance-ranked distractors from NCBI E-utilities (20 per question; OR-keyword fallback when the sentence search returned fewer): 23,247 abstracts, 41 MB, manifest in `docs/results/pubmed_subset_manifest_20261008.json` |
| Textbook corpus | MedRAG Textbooks (125,829 snippets) narrowed as C-FedRAG narrowed each corpus: top 20 Okapi BM25 snippets per question, 17,277 snippets |
| Excluded | StatPearls (2.0 GB download, not redistributable) and Wikipedia (size). C-FedRAG's Table 1 shows PubMed alone gives nearly all the gain on these tasks (70.74 vs 70.90 for all four corpora) |
| Hospitals | 8, spherical k-means over all 40,524 snippets (3,728–6,026 each) |
| Ranking | Dense bge-base-en-v1.5 cosine in every condition; 8 passages per answer (C-FedRAG's context size); no cross-encoder |
| FedSafeRAG | `routing_mode="blind"` code path: clusters of ~10 (minimum 5), int8 table embeddings, rule de-identification at load (docs/44), P = 8 and 24 |
| Generator | Qwen3.5-9B via Ollama, thinking off, temperature 0, answers capped at 16 tokens, harness prompt with the instruction after the passages |
| Leakage | Topic = hospital holding the question's source abstract; naive-Bayes observer trained on the contact patterns of the first half of the (shuffled) questions, tested on the second half; floor = majority class of the test half |
| Timing | Retrieval timed for all questions before any generation; network modelled (RTT 40 ms, 100 Mbps, contacts in parallel, as docs/53); hospital CPU and device time measured on one Apple M5 |

## Limits

- One model, one seed, one split (k-means). Dirichlet/random splits and more
  seeds are not run here (docs/50 covers them for retrieval on PMC-Patients).
- The corpus is a subset built around the questions, as C-FedRAG's was; the
  source abstract is always present, and PubMed abstracts keep their
  conclusion sections (as MedRAG's do), so retrieval is easier than open search.
- Records released counts records, not identifiers; textbooks and abstracts
  hold no patient identifiers, so de-identification here changes nothing
  measurable (docs/54 measures it).
- Latency is a model; all hospitals ran on one machine.
- The selective router is a similarity top-2 stand-in, not RAGRoute (RAGRoute
  is reproduced on PMC-Patients in docs/53).

## Run

```
python -m eval.build_pubmed_subset                       # once, ~45 min, 41 MB
OLLAMA_MODEL=qwen3.5:9b python -m eval.run_cfedrag_style --topology 8hosp --run-id full_8hosp
```

Wall time 2026-10-08 22:55 → 2026-10-09 ~03:50 (setup 8 min, closed-book
17 min, centralized 2.2 h, broadcast 2 min, selective 33 min, P=8 72 min,
P=24 33 min). Results: `docs/results/cfedrag_style_full_8hosp_20261009.csv` and
`.perquestion.jsonl`; pilot (50 questions) `cfedrag_style_pilot50_8hosp_20261008.csv`.
