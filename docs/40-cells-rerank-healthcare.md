# Anonymity cells, cross-node evidence rerank, and the same-domain hard case

## Verdict

Three things the docs/39 table and the supervisor review asked for, each
with a number.

**1. Fixed anonymity cells reduce both leaks at once — the first decoy
policy that does.** Partition the sources once into small cells that span
verticals; dispatch the *whole cell* of the top-ranked source, every time.
The contacted set is then stable (nothing to intersect away) and a function
of the cell, not the topic. On FeB4RAG:

| Policy | Contacts | Origin reached | Graded gain | Topic attack (13) | Macro-F1 | Source attack | Decoy Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|
| cosine top-4, no decoys | 4.0 | 0.817 | 0.772 | 0.454 | 0.408 | 0.744 | — |
| topic-stable decoys (v2/psi) | 4.0 | 0.787 | 0.720 | 0.495 | 0.459 | 0.564 | 0.23 |
| random decoys, any engine | 4.0 | 0.730 | 0.677 | 0.367 | 0.332 | 0.641 | 0.12 |
| **cells, 1 genuine × size 4** | 4.4 | 0.718 | 0.655 | **0.201** | **0.079** | **0.231** | 0.61 |
| cells, 1 genuine × size 3 | 3.3 | 0.667 | 0.660 | 0.265 | 0.131 | 0.308 | 0.55 |
| cells, 2 genuine × size 2 | 4.2 | 0.744 | 0.722 | 0.406 | 0.340 | 0.462 | 0.51 |

Cells of four cut topic inference from 0.454 to 0.201 (macro-F1 0.079 —
chance is 0.077) and the source attack from 0.744 to 0.231, for 0.07 of
origin-reached and 0.12 of graded gain at the same fan-out. Topic-stable
decoys, by comparison, cost 0.05 of gain and bought nothing against the
topic attack. Cells trade one genuine contact for a stable, topic-blind
cover: `genuine_k` drops to 1 and the cell supplies the rest.

**2. Cross-node evidence rerank removes a planted passage from the prompt.**
`AppState._rerank_evidence` re-embeds every returned passage in the shared
routing space and keeps `evidence_top_k`. On the 60 attack cases, with the
forged-profile attacker still selected 100% of the time:

| Evidence kept | Malicious passage in final evidence | Attacker's mean rank among returned passages |
|---|---:|---:|
| all (docs/37 behaviour) | 1.000 | 4.2 of 4–5 |
| top-2 by rerank | **0.067** | 4.2 |

Same in every mode. The attacker wins routing and loses the prompt: its
"TEST ATTACK" text scores last against the query. This is the first A3
number that moved. It is a content filter, not a routing defence — a
malicious source that returns on-topic bait would pass it, and its
selection rate is unchanged.

**3. Same-domain healthcare federation: the leak is larger and stable
decoys stop working; cells still work.** Eight semantic clients carved by
k-means from pooled nfcorpus + scifact + trec-covid (12.5k documents,
uneven sizes 800–2,800), 350 judged queries, topic = the client holding
most relevant documents. Majority-class rate 0.27–0.31 is the honest
floor (broadcast reaches it; 1/8 = 0.125 is not attainable by a
learned attacker on skewed labels).

| Condition | Contacts | Topic client reached | Rel. doc coverage | Topic attack (8) | Macro-F1 | Source attack | Decoy Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|
| random | 4.0 | 0.488 | 0.484 | 0.272 | 0.084 | 0.083 | — |
| broadcast | 8.0 | 1.000 | 1.000 | 0.309 | 0.059 | 0.125 | — |
| cosine top-2 | 2.0 | 0.869 | 0.842 | **0.604** | 0.403 | 0.958 | — |
| cosine top-4 | 4.0 | 0.962 | 0.951 | 0.615 | 0.446 | 0.875 | — |
| topic-stable decoys | 4.0 | 0.940 | 0.921 | 0.558 | 0.373 | **1.000** | 0.28 |
| random decoys, any | 4.0 | 0.912 | 0.894 | 0.432 | 0.261 | 0.958 | 0.21 |
| **cells, 1 × 3** | 4.3 | 0.834 | 0.816 | **0.272** | **0.113** | **0.250** | 0.68 |
| cells, 1 × 4 | 4.0 | 0.820 | 0.798 | 0.343 | 0.122 | 0.250 | 0.67 |
| cells, 2 × 2 | 3.8 | 0.904 | 0.885 | 0.474 | 0.292 | 0.458 | 0.53 |
| oracle | 1.0 | 1.000 | 0.886 | 0.979 | 0.928 | 1.000 | — |

In a same-domain federation the normal router's pattern names the
speciality 0.60 of the time, and topic-stable decoys **do not hide the
genuine source at all** (source attack 1.000): with six candidates of
eight, the cover varies and the genuine client is the constant. Cells of
three bring topic inference to the majority-class floor (0.272) and the
source attack to 0.250, at 0.13 of document coverage. Cells cannot be
made vertical-diverse here (one vertical), so the cover is a fixed
partition of specialities — and it still works, because stability plus
topic-independence is the property, not the diversity.

## Reading

- The docs/39 tension is resolvable: a cover set must be **stable** (defeats
  intersection) and **not a function of the topic** (defeats the learned
  observer). Per-topic decoys satisfy the first, random decoys neither, a
  fixed partition of sources both.
- The cost is real and stated: one fewer genuine contact and 0.12–0.13 of
  utility. Whether that is acceptable is a deployment choice; the table
  gives the price.
- Cells are the design v2/psi should adopt for the `decoy` role; the PSI
  stage is unaffected (it acts on ids). Not yet wired into
  `select_dispatch`; measured in `eval/run_leakage.py` and
  `eval/run_healthcare.py` only.
- The healthcare federation is public literature partitioned by topic, not
  institutional data; it stands in for speciality structure and nothing
  else.

## Setup

Cells: `router/anonymity.build_cells` (round-robin across verticals, short
final cell merged) and `cell_cover` (whole cells only; cap = genuine ×
largest cell, so contacts can exceed the nominal size slightly).
Conditions and attackers as docs/39; FeB4RAG run with `--conditions
cosine@K sticky_decoys random_any cells_1x3 cells_1x4 cells_2x2`, 3 seeds.

Rerank: `eval/run_privacy_cases.py` attack section; honest nodes return
their best passage by cosine in the shared space, the attacker returns its
planted text; `evidence_top_k` ∈ {all, 2}; 13 engines, cap 6.

Healthcare: `eval/run_healthcare.py`, 150 queries per corpus, at most 20
highest-graded relevant documents per query, 4,000 further documents per
corpus, spherical k-means into 8 clients, bge-base, seeds 11/22/33, cap 4,
`genuine_k=2`, `coarse_k=6`.

## What this does not establish

- Cells against an attacker who also sees timing, sizes, or the query.
- Cells with more than one genuine source per query at a fixed cap: 2 × 2
  is measurably weaker than 1 × 4.
- Any end-to-end answer-quality effect of cells or of the rerank cap (E10
  used neither); the rerank's effect on genuine off-topic decoy passages is
  measured only through the attack cases.
- A routing-level A3 defence: the attacker is still selected 1.000.

## Reproduce

```
python -m eval.run_leakage --conditions cosine@K sticky_decoys random_any cells_1x3 cells_1x4 cells_2x2
python -m eval.run_privacy_cases
python -m eval.run_healthcare
```

Tests: `tests/test_anonymity.py` (cells), `tests/test_psi_api.py` (rerank).
Test counts are not privacy results.
