# Hybrid rerank on the device

## Verdict

**Adding keyword evidence to the device's ranking raises blind unlock's
MRR by +0.09–0.10 at no privacy cost** — the ranking runs over passages the
device already holds, so nothing that leaves it changes. The same ranking
raises every configuration, HyFedRAG-style included, so the fair comparison
is at matched ranking.

PMC-Patients, docs/46 setup (986 queries, 5,000 patients, 8 k-means
hospitals, bge-base, seed 11). The weight (0.5) was chosen on the first half
of the queries in a separate sweep; the second-half column is held out.

| Configuration | Ranking | MRR | MRR, held-out half | P@10 | nDCG@10 | Question to hospitals | Topic (floor 0.239) | Records / q | Device ms / q | Slowest hospital ms / q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| centralized | dense | 0.443 | 0.425 | 0.109 | 0.409 | — | — | — | 0.6 (total) | — |
| centralized | **hybrid** | **0.555** | 0.550 | 0.128 | 0.514 | — | — | — | 131 (total) | — |
| HyFedRAG-style | dense | 0.444 | 0.425 | 0.109 | 0.409 | **all 8** | 0.239 | 80 | 1.7 (total) | — |
| HyFedRAG-style | **hybrid** | **0.543** | 0.539 | 0.126 | 0.502 | **all 8** | 0.239 | 80 | 99 (total) | — |
| ours: PSI + cells | dense | 0.350 | 0.329 | 0.083 | 0.305 | 0 | 0.254 | 143 | 274 (total) | — |
| ours: PSI + cells | hybrid | 0.405 | 0.390 | 0.087 | 0.346 | 0 | 0.254 | 143 | 285 (total) | — |
| ours: blind unlock P = 8 | dense | 0.421 | 0.406 | 0.101 | 0.379 | 0 | 0.239 | 140 | 42 | 9 |
| **ours: blind unlock P = 8** | **hybrid** | **0.509** | 0.504 | 0.112 | 0.454 | **0** | **0.239** | 140 | 54 | 9 |
| ours: blind unlock P = 16 | dense | 0.431 | 0.411 | 0.105 | 0.392 | 0 | 0.239 | 269 | 83 | 17 |
| **ours: blind unlock P = 16** | **hybrid** | **0.526** | 0.518 | 0.118 | 0.477 | **0** | **0.239** | 269 | 108 | 17 |
| ours: blind unlock P = 24 | dense | 0.437 | 0.416 | 0.107 | 0.401 | 0 | 0.239 | 393 | 125 | 26 |
| **ours: blind unlock P = 24** | **hybrid** | **0.535** | 0.527 | 0.122 | 0.490 | **0** | **0.239** | 393 | 158 | 26 |

Reading:

- **Hybrid ranking lifts everything by a similar amount** (+0.09 to +0.11
  MRR): case reports share rare clinical terms (syndromes, drugs, gene
  names) that a general-purpose dense encoder under-weights.
- **At matched ranking, blind unlock keeps 94% (P = 8) to 98.5% (P = 24)
  of HyFedRAG-style MRR** (0.509 / 0.535 vs 0.543), while no hospital sees
  the question and the contact pattern carries nothing. On the held-out
  half: 0.504 / 0.527 vs 0.539.
- **Blind unlock with hybrid ranking beats HyFedRAG-style with the dense
  ranking HyFedRAG describes** (0.509 vs 0.444) — true, but only a fair
  claim when the ranker difference is stated; the matched comparison above
  is the one to lead with.
- **Cost:** +12 ms on the device at P = 8 (tokenising and scoring ~140
  passages); hospitals unchanged.
- PSI + cells gains less (+0.055): its pool is fixed by the cell, not chosen
  across hospitals, so there is less for the ranker to reorder.

## Method

`router/hybrid_rerank.py`: score = z(cosine) + w·z(BM25), z within the
pool; BM25 k1 = 1.2, b = 0.75, statistics (IDF, average length) from the
pool the device holds — never from a node's whole corpus, which the device
cannot see. Simple word tokens, English function words dropped.
HyFedRAG-style hybrid: each hospital ranks its own index by hybrid (it
receives the question, so it may, using its own statistics) and returns its
top 10; the server re-ranks the union by hybrid. Centralized hybrid: one
index, corpus statistics. One weight for every configuration.

API: `rerank="dense" | "hybrid"` (default dense — every earlier result is
unchanged), `hybrid_weight` (default 0.5); applies to blind mode's pool
ranking and to the cross-node evidence rerank in every mode. The studio
defaults to hybrid.

## What this does not establish

- The weight was chosen on the first half of this dataset's queries
  (with a slightly different tokeniser in the exploratory sweep); the
  held-out-half column is the honest number, and a new dataset needs its own
  check.
- One dataset and task (patient-to-patient similarity, which rewards
  lexical overlap more than many QA tasks). Not measured on FeB4RAG or
  MIRAGE answer accuracy.
- No significance test yet (paired bootstrap between matched rows is the
  next check).
- A learned reranker (e.g. a medical cross-encoder) was not tested; it
  needs a model download.

## Reproduce

```
python -m eval.run_hyfedrag_compare --queries 1000 --skip-stock-deid --only \
    centralized centralized_hybrid hyfedrag_style hyfedrag_style_hybrid \
    ours_psi_cells ours_psi_cells_hybrid ours_blind_P8 ours_blind_P8_hybrid \
    ours_blind_P16 ours_blind_P16_hybrid ours_blind_P24 ours_blind_P24_hybrid
```

Tests: `tests/test_hybrid_rerank.py` (tokeniser, BM25 ordering, weight 0 is
exactly the dense cosine, lexical evidence breaks a dense tie, the option
changes no node's traffic). Test counts are not retrieval results.
