# Gap 3: source content released beyond what retrieval needs

## Verdict

PMC-Patients, docs/46 setup: 5,000 patients, 8 k-means hospitals, rules + NER de-identification, all 986 queries, hybrid ranking.

The retrieval output is the top-10. "Released" means records whose text and embedding reach the device.

| Claim | Holds? | Evidence |
|---|---|---|
| Blind unlock releases more than retrieval needs | ✅ (measured) | Default P = 8: 140 records per question for a top-10 (14×); release precision 1.2% |
| Release can be cut without losing retrieval quality | ✅ | 5-patient clusters (min 5) at P = 16: MRR 0.5274 vs 0.5248 for the default clusters at P = 16 (n.s., p = 0.64), with **218 instead of 268 records (−19%)**, same minimum of 5 patients per centroid |
| At the default's release budget, finer clusters retrieve better | ✅ | 3/2 clusters at P = 24: 159 records, MRR 0.5248 vs default P = 8: 140 records, MRR 0.4997 (+0.025, p < 0.001) |
| Finer clusters are free | ❌ | Centroids within cosine 0.95 of a single patient: 3.6% (10/5) → 7.2% (5/5) → 17.2% (5/3) → 49.4% (3/2). At 0.97: 0.0% → 0.2% → 1.2% → 3.7%. No centroid within 0.99 at any setting |
| Blind releases less than broadcast | ❌ at equal quality | Broadcast (HyFedRAG-style hybrid) returns 80 records at MRR 0.5428 but every hospital reads the question. Blind's closest quality: 237–392 records (MRR 0.534–0.536, n.s. vs broadcast) |

**Safe sentence:** "Evidence release is measured as records unlocked per
question against the top-10 the retriever returns. With the default
clusters blind unlock releases 14× the top-10. Halving the cluster size at
the same 5-patient minimum keeps MRR (0.527 vs 0.525, n.s.) with 19% fewer
records. Smaller minimums cut release further but make published centroids
closer to individual patients. Release is a tunable trade-off against
centroid disclosure, not eliminated."

## Results

### Release frontier (986 queries, hybrid ranking)

| Granularity (docs per cluster / minimum) | P | Records unlocked (p95) | × top-10 | Release precision | MRR |
|---|---|---|---|---|---|
| broadcast, HyFedRAG-style hybrid | — | 80 (80) | 8× | 1.9% | 0.5428 |
| **10 / 5 (default, all earlier results)** | 4 | 73 (113) | 7× | 1.9% | 0.4579 |
| | **8** | **140 (197)** | **14×** | 1.2% | **0.4997** |
| | 16 | 268 (352) | 27× | 0.7% | 0.5248 |
| | 24 | 392 (497) | 39× | 0.5% | 0.5357 |
| **5 / 5** | 4 | 59 (92) | 6× | 2.5% | 0.4634 |
| | 8 | 113 (158) | 11× | 1.5% | 0.4942 |
| | **16** | **218 (285)** | **22×** | 0.9% | **0.5274** |
| | 24 | 321 (407) | 32× | 0.6% | 0.5330 |
| 5 / 3 | 4 | 44 (68) | 4× | 3.1% | 0.4660 |
| | 8 | 84 (119) | 8× | 1.9% | 0.4915 |
| | 16 | 162 (212) | 16× | 1.1% | 0.5208 |
| | 24 | 237 (299) | 24× | 0.8% | 0.5335 |
| 3 / 2 | 4 | 30 (46) | 3× | 4.1% | 0.4385 |
| | 8 | 57 (78) | 6× | 2.6% | 0.4898 |
| | 16 | 108 (140) | 11× | 1.5% | 0.5150 |
| | 24 | 159 (198) | 16× | 1.1% | 0.5248 |

### What finer clusters publish (all 8 hospitals)

| Granularity | Centroids | Cluster size min / median | Within 0.95 of one patient | Within 0.97 | Within 0.99 | Tables |
|---|---|---|---|---|---|---|
| 10 / 5 | 365 | 5 / 11 | 3.6% | 0.0% | 0.0% | 11.4 MB |
| 5 / 5 | 458 | 5 / 9 | 7.2% | 0.2% | 0.0% | 12.2 MB |
| 5 / 3 | 674 | 3 / 6 | 17.2% | 1.2% | 0.0% | 14.7 MB |
| 3 / 2 | 1,136 | 2 / 3 | 49.4% | 3.7% | 0.0% | 20.4 MB |

bge-base cosines are compressed: almost every centroid is within 0.90 of
some patient, so 0.90 is not a useful threshold. The docs/35 rule
(minimum cluster size, never publish document embeddings) is what 5/5
keeps and 5/3 and 3/2 relax.

### Significance (paired bootstrap, 10,000 resamples)

| Comparison | Records | MRR difference | p |
|---|---|---|---|
| 5/5 P16 vs 10/5 P16 | 218 vs 268 | +0.003 [−0.008, +0.014] | 0.64 |
| 5/5 P16 vs 10/5 P8 | 218 vs 140 | **+0.028** [+0.014, +0.042] | < 0.001 |
| 5/3 P16 vs 10/5 P16 | 162 vs 268 | −0.004 [−0.015, +0.007] | 0.48 |
| 5/3 P16 vs 10/5 P8 | 162 vs 140 | **+0.021** [+0.007, +0.036] | 0.004 |
| 3/2 P24 vs 10/5 P8 | 159 vs 140 | **+0.025** [+0.011, +0.039] | < 0.001 |
| 10/5 P24 vs broadcast | 392 vs 80 | −0.007 [−0.017, +0.002] | 0.13 |
| 5/3 P24 vs broadcast | 237 vs 80 | −0.009 [−0.020, +0.002] | 0.09 |

## Recommended setting

| If the priority is | Use | Records | MRR |
|---|---|---|---|
| Earlier results unchanged | 10/5, P = 8 (current default) | 140 | 0.500 |
| Quality at the same 5-patient minimum | **5/5, P = 16** | 218 | 0.527 |
| Least release at the 5-patient minimum | 5/5, P = 4 | 59 | 0.463 |
| Least release overall (weaker centroid protection) | 3/2, P = 8 | 57 | 0.490 |

The defaults are not changed, so every earlier number is unchanged.
`build_cluster_index(docs_per_cluster=, min_size=)` and the probe count `P`
are the two knobs.

## What this does not establish

- Released records are de-identified (docs/54) but still real case text.
  Membership inference on released records or centroids was not run.
- "Within cosine 0.95 of a patient" is a proximity measure, not a
  demonstrated inversion. Turning a centroid into text (vec2text-style) was
  not tried.
- One corpus, one split (k-means), one seed.
- A two-level unlock (embeddings first, text only for the top-k) would cut
  text release to the top-k. It is designed in the docs/55 discussion, not
  built.

## Reproduce

```
cd backend
python -m eval.run_release
python -m eval.bootstrap_compare ../docs/results/release_20261002-005108.perquery.json \
    blind_g5-5_P16_hybrid:blind_g10-5_P16_hybrid
```
