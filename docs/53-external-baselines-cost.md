# Published federated-RAG systems vs blind unlock: quality, privacy and cost

## Verdict

Measured on PMC-Patients (the docs/46 setup) against two systems whose
code is public, RAGRoute and Flower FedRAG, plus the HyFedRAG-style design.

| Claim | Holds? | Evidence (8 hospitals, k-means, unless stated) |
|---|---|---|
| Contacting every hospital is costly **when each hospital embeds the question and returns passages** | ✅ | bge broadcast: 287 → 542 → 1,112 ms of hospital CPU and 275 KB → 1.1 MB per question at 8 → 16 → 32 hospitals |
| Blind unlock contacts every hospital but each contact is cheap | ✅ | about 9 ms of OPRF work and 1.2 KB per hospital; total 68 → 137 → 274 ms and 9 → 18 → 37 KB at 8 → 16 → 32 |
| Blind uses less hospital CPU than bge broadcast | ✅ | about 4× less at every size |
| Blind uses less traffic than every baseline | ✅ | about 30× less than bge broadcast; 8× (k-means) to 280× (random) less than RAGRoute |
| Blind is the cheapest in hospital CPU | ❌ | RAGRoute's hospitals only search (its coordinator embeds the question and sends the vector): ~0.1 ms |
| Blind is the fastest | ❌ | modelled 112–148 ms (P=8) vs 50–114 ms for broadcast; the device-side unlock is the cost |
| Selective routing (RAGRoute) is cheaper and still private | ❌ | it sends the question text **and** its embedding to the hospitals it picks; topic inference 0.562 vs floor 0.226 |
| Selective routing stays selective | ❌ off k-means | the router learns little on Dirichlet / random splits (val AUC 0.852 / 0.583) and contacts 5.5 / 7.4 of 8 hospitals, each returning 50 records (0.95–1.28 MB per question) |
| Blind's quality beats RAGRoute's | split-dependent | P=8 hybrid: +0.041 to +0.061 on k-means (8/16/32 hospitals, p < 0.001); −0.052 (Dirichlet) and −0.089 (random). P=24 hybrid: +0.073 (k-means), +0.019 (Dirichlet, p = 0.054), +0.005 (random, n.s.) |
| Blind discloses fewer records to the device | ❌ vs broadcast | P=8 unlocks ~139 records per question; broadcast returns 80; RAGRoute 98 (k-means) to 369 (random) |

**Safe sentence:** "Blind unlock gives privacy from the hospitals at
comparable cost: about 4× less hospital CPU and about 30× less traffic than
a broadcast design in which hospitals embed the question, at slightly
higher latency. A selective router (RAGRoute) used less hospital CPU but
revealed the question to the hospitals it chose. Its contact pattern
revealed the topic (0.562 vs a 0.226 floor), and on non-topical splits it
contacted nearly every hospital."

Do not write "cheapest", "fastest" or "beats RAGRoute" without the split.

## What was reproduced

`backend/baselines/external_fedrag.py` (provenance in its docstring).

| | RAGRoute (EPFL, MIT) | Flower FedRAG (Apache-2.0) |
|---|---|---|
| Source | github.com/sacs-epfl/ragroute | flower examples/fedrag |
| Copied | `CorpusRoutingNN` (128-64-32, LayerNorm, Dropout 0.4); features = query embedding ‖ source centroid ‖ one-hot id, StandardScaler; BCE (pos_weight computed but unused, as in the script); Adam 1e-3, wd 3e-5, batch 128, CyclicLR then StepLR, 150 epochs, best validation AUC; route if p > 0.5; label = hospital holds one of the global top-15; top-50 per hospital | `merge_documents` (sort by L2, RRF k = 60); client index FAISS `IndexIVFFlat`, L2, nlist = √N, FAISS default nprobe 1; client embeds the question with all-MiniLM-L6-v2 |
| Message to a hospital | question text **and** embedding (as in `ragroute/http_server.py`) | question text |
| Not reproduced | bge-reranker-v2-m3 cross-encoder (~2 GB, over the download limit) — replaced by our dense or hybrid ranking | SmolLM2 generation; MedRAG corpora (over the limit) |
| Changed | — | k-nn 8 → 10, so every configuration is scored on the same top-10 |

`flower_fedrag_bge` swaps in bge-base to separate the embedder from the design.

Protocol (`backend/eval/run_external_baselines.py`):
- 986 PMC queries, split once by query: 30% train, 10% validation (RAGRoute's router only), 60% test (593).
- **Every configuration is scored on the same 593 test queries.** MRR values are therefore not the docs/46–50 full-set numbers.
- Baselines run on raw hospital indexes. Blind runs on de-identified nodes (rules + NER), as in docs/46.

Cost accounting:
- **Hospital CPU** is measured on this machine (Apple M5).
  - A hospital that receives text must embed it. The uncached single-question embedding time (bge 34–36 ms, MiniLM 6 ms) is measured once per question and charged to every hospital that embeds it (same hardware assumed).
  - Search and OPRF evaluation are measured per contact.
- **Bytes** are JSON payload sizes. Blind uses hex points, as in the docs/46 harness.
- **Latency** is a model: device time + the slowest contact (40 ms RTT + hospital time + bytes at 100 Mbps), with contacts in parallel. It is not a network measurement.

## Results, 8 hospitals, three splits (593 test queries)

| Configuration | MRR k-means / Dirichlet / random | Hospitals reading the question | Topic inference (floor) k-means | Hospital CPU total / slowest (ms) | Up / down per question | Modelled latency | Records to device |
|---|---|---|---|---|---|---|---|
| centralized (hybrid) | 0.445 (0.565) | — | — | — | — | — | — |
| flower_fedrag (MiniLM) | 0.262 / 0.277 / 0.266 | 8 | 0.128 (0.226) | 49 / 6 | 22 / 236 KB | 50 ms | 77 |
| flower_fedrag_bge | 0.363 / 0.388 / 0.388 | 8 | 0.128 | 286 / 36 | 22 / 241 KB | 79 ms | 79 |
| hyfedrag_style | 0.445 / 0.445 / 0.445 | 8 | 0.128 | 287 / 36 | 22 / 253 KB | 79 ms | 80 |
| hyfedrag_style_hybrid | 0.552 / 0.554 / 0.544 | 8 | 0.128 | 377 / 54 | 22 / 303 KB | 105 ms | 80 |
| ragroute | 0.401 / 0.424 / 0.433 | 1.97 / 5.48 / 7.37 | **0.562** | 0.1 / 0.1 | 39 / 310 KB (k-m) · 108 / 846 (Dir) · 146 / 1,137 (rand) | 88 ms | 98 / 274 / 369 |
| ragroute_hybrid | 0.474 / 0.520 / 0.524 | same | **0.562** | 0.2 / 0.1 | same | 97 ms | same |
| ours_blind_P8 | 0.420 / 0.403 / 0.371 | **0** | 0.128 | 68 / 9 | 4.6 / 4.6 KB | 112 ms | 139 |
| ours_blind_P8_hybrid | 0.515 / 0.469 / 0.435 | **0** | 0.128 | 68 / 9 | 4.6 / 4.6 KB | 123 ms | 139 |
| ours_blind_P24_hybrid | 0.547 / 0.540 / 0.529 | **0** | 0.128 | 206 / 27 | 12.8 / 12.8 KB | 218 ms | 390 |

Topic inference on the other splits:

| Split | Broadcast / blind | RAGRoute | Floor |
|---|---|---|---|
| Dirichlet | 0.165 | 0.246 | 0.165 |
| random | 0.131 | 0.125 | 0.152 |

RAGRoute contacted no hospital for 4.9% of k-means questions (MRR 0 on those), as its rule does when no score exceeds 0.5.

Blind's one-time table download is 15.1–15.9 MB per key epoch for the whole federation. It is not charged to any question. Cover rounds (docs/52) cost the same as a real round per tick and are not included here.

## Scaling: 8, 16, 32 hospitals (k-means, same 5,000 patients)

| Configuration | MRR 8 / 16 / 32 | Hospital CPU total (ms) 8 / 16 / 32 | Traffic up+down 8 / 16 / 32 | Modelled latency 8 / 16 / 32 | Topic inference / floor at 32 |
|---|---|---|---|---|---|
| flower_fedrag (MiniLM) | 0.262 / 0.255 / 0.260 | 49 / 94 / 188 | 258 KB / 498 KB / 949 KB | 50 / 49 / 50 ms | 0.051 / 0.077 |
| hyfedrag_style | 0.445 / 0.445 / 0.445 | 287 / 542 / 1,113 | 275 KB / 552 KB / 1.10 MB | 79 / 78 / 79 ms | 0.051 / 0.077 |
| hyfedrag_style_hybrid | 0.552 / 0.554 / 0.556 | 377 / 631 / 1,199 | 325 KB / 650 KB / 1.27 MB | 105 / 105 / 114 ms | 0.051 / 0.077 |
| ragroute_hybrid (contacts 1.97 / 2.29 / 2.49) | 0.474 / 0.462 / 0.464 | ~0.1 at every size | 349 / 411 / 435 KB | 97 / 97 / 99 ms | **0.337** / 0.077 |
| ours_blind_P8_hybrid | 0.515 / 0.522 / 0.520 | 68 / 135 / 272 | 9 / 18 / 37 KB | 123 / 129 / 148 ms | 0.051 / 0.077 |
| ours_blind_P24_hybrid | 0.547 / 0.548 / 0.544 | 206 / 404 / 817 | 26 / 51 / 102 KB | 218 / 236 / 292 ms | 0.051 / 0.077 |

RAGRoute's topic inference falls as hospitals are added (0.562 → 0.505 → 0.337) but stays 3–7× its floor (0.226 / 0.125 / 0.077).

How each design grows with the number of hospitals N:
- **Broadcast:** per-hospital cost is fixed (one embedding + one search + 10 passages), so totals grow as N.
- **Blind:** per-hospital cost is also fixed (P points), so totals grow as N, at about a quarter of bge broadcast's CPU and about 1/30 of its traffic. The device's unlock time grows too (63 → 87 ms at P = 8, dense).
- **RAGRoute:** contacts depend on the data, not on N. On k-means splits they stayed at 2–2.5.

Caveat: the corpus is fixed, so hospitals shrink as N grows. Real hospitals would each hold more data, which raises table size and search time but not question-embedding time.

## Significance (paired bootstrap, 10,000 resamples, 593 test queries)

`python -m eval.bootstrap_compare <perquery.json> A:B ...`

| Comparison | k-means 8 | k-means 16 | k-means 32 | Dirichlet 8 | random 8 |
|---|---|---|---|---|---|
| blind P8 hybrid − RAGRoute hybrid | **+0.041** (p < 0.001) | **+0.061** | **+0.057** | **−0.052** | **−0.089** |
| blind P24 hybrid − RAGRoute hybrid | **+0.073** | **+0.087** | **+0.080** | +0.019 (p = 0.054) | +0.005 (p = 0.62) |
| blind P8 dense − RAGRoute dense | +0.019 (p = 0.081) | **+0.042** | **+0.044** | **−0.021** (p = 0.027) | **−0.063** |
| blind P24 hybrid − HyFedRAG-style hybrid | −0.006 (p = 0.33) | −0.006 (p = 0.36) | −0.013 (p = 0.050) | −0.014 (p = 0.058) | −0.016 (p = 0.067) |
| blind P8 hybrid − HyFedRAG-style hybrid | **−0.038** | **−0.032** | **−0.036** | **−0.085** | **−0.109** |
| blind P8 hybrid − Flower (MiniLM) | **+0.252** | **+0.267** | **+0.261** | **+0.192** | **+0.170** |
| blind P8 hybrid − Flower (bge) | **+0.152** | **+0.138** | **+0.133** | **+0.081** | **+0.048** |

Bold means the 95% interval excludes zero.

## What this does not establish

- It is not the authors' full systems: RAGRoute runs without its cross-encoder, and Flower without its LLM evaluation, both on this project's hospitals.
  - Flower's low MRR is partly its defaults: MiniLM truncates long patient summaries, and IVF with nprobe 1 is approximate. `flower_fedrag_bge` vs `hyfedrag_style` (0.363 vs 0.445 on k-means) is the cost of the IVF approximation. The defaults were not tuned.
- Hospital CPU is on one Apple M5 machine for every party. A CPU-only hospital server would embed more slowly, which would widen the broadcast gap; this was not measured.
- Latency is modelled, not measured on a network; contacts are assumed parallel.
- RAGRoute's training labels come from a centralized top-15, which requires the training questions to be answered over all hospitals' data in the clear. That training-time exposure is not counted above.
- Records disclosed to the device are higher for blind than for broadcast. This is the source-data axis, and it is not solved here.
- One seed, one corpus size.

## Reproduce

```
cd backend
OMP_NUM_THREADS=1 python -m eval.run_external_baselines --queries 1000 --partition kmeans --clients 8
# --partition dirichlet|random; --clients 16|32; --rtt-ms, --mbps for the latency model
python -m eval.bootstrap_compare ../docs/results/external_baselines_kmeans_c8_20261001-162602.perquery.json \
    ours_blind_P8_hybrid:ragroute_hybrid ours_blind_P24_hybrid:hyfedrag_style_hybrid
```

`OMP_NUM_THREADS=1` is required on macOS: FAISS and torch each link an OpenMP runtime.

Result files: `docs/results/external_baselines_{kmeans_c8,dirichlet_c8,random_c8,kmeans_c16,kmeans_c32}_*.csv`, each with a `.perquery.json`.

Tests: `tests/test_external_baselines.py` checks the copied merge, the FAISS client index and that the router learns. These are not results.
