# Robustness, significance, sessions and answers

## Verdict

The privacy results hold on every hospital split and over sessions; the
retrieval cost of blind unlock depends on the probe budget P and on how
topic-focused the hospitals are.

- **Pattern leakage** is at the inference floor for blind unlock on all three
  splits and at every session length (1–5 linked questions). The cosine
  router, topic-stable decoys and random decoys climb to 0.50–0.57 over a
  five-question session; cells stay near the floor on k-means but leak on
  the Dirichlet split (0.294 vs floor 0.210).
- **Retrieval** at matched (hybrid) ranking, as a share of the local
  HyFedRAG-style baseline: **P = 8: 94% / 86% / 81%** on k-means / Dirichlet /
  random hospitals; **P = 24: 98% / 97% / 97%**. P = 24 is statistically
  indistinguishable from the baseline on the k-means split only.
- Blind unlock beats per-query PSI + cells by +0.067 to +0.073 MRR on every
  split (all p < 0.001).
- **Answers** (MIRAGE, 150 questions, local Qwen3.5-9B): blind unlock
  0.613 vs closed-book 0.547, **+0.067, 95% CI [+0.007, +0.133], p = 0.035**
  — the first statistically significant answer-level gain in this project.

## 1. Robustness across hospital splits (docs/46 setup, 986 queries)

The same 5,000 PMC-Patients patients split three ways: k-means in the
routing embedding (topic-focused hospitals, docs/46), Dirichlet(α = 0.5)
over the k-means topics (the usual non-IID federated split), and uniform
random (IID). MRR; topic inference against the split's majority floor.

| Configuration | k-means MRR | Dirichlet MRR | Random MRR | Topic (floor) k-means / Dirichlet / random |
|---|---:|---:|---:|---|
| HyFedRAG-style, dense | 0.444 | 0.444 | 0.444 | 0.239 (0.239) / 0.210 (0.210) / 0.141 (0.141) |
| HyFedRAG-style, hybrid | 0.543 | 0.542 | 0.535 | same |
| cosine router top-4, dense | 0.444 | 0.413 | 0.334 | **0.318** / **0.290** / 0.164 |
| PSI + cells, dense | 0.350 | 0.320 | 0.306 | 0.253 / **0.294** / 0.135 |
| PSI + cells, hybrid | 0.405 | 0.375 | 0.356 | same |
| blind unlock P = 8, dense | 0.421 | 0.393 | 0.373 | **at floor on all three** |
| **blind unlock P = 8, hybrid** | **0.509** | **0.465** | **0.432** | at floor |
| blind unlock P = 16, hybrid | 0.526 | 0.514 | 0.499 | at floor |
| **blind unlock P = 24, hybrid** | **0.535** | **0.528** | **0.519** | at floor |
| centralized, hybrid (ceiling) | 0.555 | 0.555 | 0.555 | — |

Reading: selective routing (cosine top-4) collapses as hospitals stop being
topic-focused (0.444 → 0.334), because the relevant patients are spread over
all eight. Blind unlock also degrades at small P for the same reason — P
clusters must cover patients scattered across every hospital — but recovers
with P: at P = 24 it is within 3% of the baseline on every split. Contacting
every hospital is exactly what makes it robust to the split.

## 2. Significance (paired bootstrap over queries, 10,000 resamples)

`eval/bootstrap_compare.py` on the per-query MRR written by the harness.
Ratio = blind / baseline, 95% interval.

| Comparison | k-means | Dirichlet | Random |
|---|---|---|---|
| blind P=8 hybrid vs HyFedRAG hybrid | 0.936 [0.910, 0.961] | 0.858 [0.824, 0.892] | 0.807 [0.768, 0.847] |
| **blind P=24 hybrid vs HyFedRAG hybrid** | **0.984 [0.966, 1.002], p = 0.08 (n.s.)** | 0.974 [0.952, 0.995], p = 0.01 | 0.969 [0.945, 0.992], p = 0.01 |
| blind P=8 hybrid vs HyFedRAG dense (as described) | 1.147, p < 0.001 | 1.049, p = 0.05 (n.s.) | 0.974, p = 0.34 (n.s.) |
| blind P=8 dense vs PSI + cells dense | +0.071, p < 0.001 | +0.073, p < 0.001 | +0.067, p < 0.001 |

The honest retrieval sentence: **86–94% of a local HyFedRAG-style baseline at
P = 8 on topic-focused splits (81% on IID), 97–98% at P = 24 on all
splits.** "Beats HyFedRAG" is true only against its dense ranker, and only
on the k-means split.

## 3. Session attack (docs/51 claims, `eval/run_session_attack.py`)

An observer links five follow-up questions about one patient (967 PMC query
patients with ≥ 5 sentences, split into five chunks; k-means split). Topic
inference (floor 0.238) and the source attack (most-contacted hospital,
chance 0.125):

| Policy | Topic, 1 → 5 questions | Source, 1 → 5 questions |
|---|---|---|
| cosine top-4 | 0.314 → **0.543** | 0.228 → **0.477** |
| topic-stable decoys | 0.469 → **0.570** | 0.190 → 0.252 |
| random decoys | 0.258 → **0.504** | 0.189 → **0.492** |
| fixed cells | 0.256 → 0.283 | 0.183 → 0.200 |
| **blind unlock** | **0.238 → 0.238** | **0.125 → 0.125** |

Decoys are worse than no decoys at one question (topic-stable 0.469 vs router
0.314): a cover set keyed by topic is a topic fingerprint (docs/39). Random
decoys fall to intersection within a few questions. Cells hold because the
cover set is fixed; blind unlock holds because there is no cover set to
learn from — every hospital, every time.

## 4. Answer quality (MIRAGE, extends docs/38)

150 questions (medqa, medmcqa, pubmedqa, bioasq, mmlu-medical; 30 each), six
nodes (three medical BEIR corpora, three distractors), local Qwen3.5-9B via
Ollama, two passages to the generator.

| Condition | Accuracy | vs closed-book (paired bootstrap) |
|---|---:|---|
| closed-book | 0.547 | — |
| PSI + cells + rerank | 0.593 | +0.047 [−0.007, +0.100], p = 0.10 |
| **blind unlock (P = 8), dense** | **0.613** | **+0.067 [+0.007, +0.133], p = 0.035** |
| blind unlock, hybrid | 0.573 | vs blind dense −0.040, p = 0.07 |
| broadcast | 0.540 | **not comparable** — see below |

- Blind unlock vs PSI + cells: +0.020, p = 0.34 — "at least as good", not
  better.
- **Hybrid ranking does not help MIRAGE** (−0.040, borderline): its gain is
  task-dependent — large for patient-to-patient similarity (docs/48), none
  for exam-style questions whose options, not keywords, carry the answer.
  The studio default of hybrid is right for case retrieval, not universally.
- The broadcast run (12 passages per question) generated in 9 s median with
  12 abstentions while three other experiments shared the machine, against
  0.627 in docs/38; it is reported as not comparable, not as a result.

## What this does not establish

- One retrieval dataset (PMC-Patients) for the split and significance
  results; MIRAGE is answer-level on BEIR samples, not MedRAG.
- The HyFedRAG-style baseline is a local reimplementation of the described
  design (docs/46).
- The session attack was run on the k-means split only.
- MIRAGE is 150 questions, one model, one seed.

## Reproduce

```
cd backend
for p in kmeans dirichlet random; do
  python -m eval.run_hyfedrag_compare --queries 1000 --skip-stock-deid --partition $p --only \
    centralized centralized_hybrid hyfedrag_style hyfedrag_style_hybrid cosine_router ours_psi_cells \
    ours_psi_cells_hybrid ours_blind_P8 ours_blind_P8_hybrid ours_blind_P16_hybrid ours_blind_P24 ours_blind_P24_hybrid
done
python -m eval.bootstrap_compare <perquery.json> ours_blind_P24_hybrid:hyfedrag_style_hybrid ...
python -m eval.run_session_attack
LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3.5:9b python -m eval.run_answer_quality \
    --conditions closed_book psi_cells blind blind_hybrid broadcast
```

The exact result files behind every number here are archived in
`docs/results/` (the working copies under `data/eval_results/` are not
tracked by git).
