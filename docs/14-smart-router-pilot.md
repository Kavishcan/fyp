# Measured smart-router pilot

## Verdict

The current default smart-router heuristic is not yet a useful improvement over
cosine source selection on this pilot. It obeys the exposure budget but stops
too aggressively, reducing retrieval quality substantially. This is a measured
negative result, not evidence that the full research idea is impossible.

No algorithm parameters were changed after observing these results. Preserve
this run as the initial reference, and use validation data for subsequent design
changes. The test queries used here are now exploratory evidence for development;
do not repeatedly optimize on them and then call them an untouched final test.

## Setup

- Local SciFact corpus: 5,183 documents and 300 test questions with positive qrels.
- 30 simulated sources, balanced random document shards; partition seeds 11, 22, 33.
- Partition construction is independent of queries and relevance labels.
- 900 query/partition cases per method, but only 300 unique questions. The three
  partitions share documents/questions and are not independent query samples.
- Cached all-MiniLM-L6-v2 embeddings, normalized; no downloads or model training.
- Model snapshot: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41; max length 256 tokens.
- Four centroids per source, existing NumPy clustering, no profile noise.
- Unit contact cost, all sources authorized, neutral trust 0.5 with no feedback.
- Smart default: mean aggregation, gain threshold 0.05, uncertainty penalty 0.1,
  overlap weight 1, source cap 5. These were not fitted to this dataset.
- CPU, four Torch threads, macOS arm64. NumPy 2.5.2, Torch 2.13.0,
  sentence-transformers 6.0.1. Document/query encoding took 31.30 seconds.

This is a same-domain, randomly partitioned source experiment, not a real
30-hospital deployment or a measurement of MCP transport.

## Results

All recall values are percentages, macro-averaged over the 900 cases.

| Method | Mean contacts | Source recall | Document recall@10 | No-source rate |
|---|---:|---:|---:|---:|
| Broadcast | 30.00 | 100.00 | 78.33 | 0.00 |
| Cosine mean top-1 | 1.00 | 6.15 | 6.14 | 0.00 |
| Cosine mean top-3 | 3.00 | 16.66 | 15.65 | 0.00 |
| Cosine mean top-5 | 5.00 | 24.38 | 22.31 | 0.00 |
| Cosine max top-3 | 3.00 | 19.90 | 18.94 | 0.00 |
| Smart budget 1 | 0.92 | 5.92 | 5.91 | 7.67 |
| Smart budget 3 | 0.92 | 5.92 | 5.91 | 7.67 |
| Smart budget 5 | 0.92 | 5.92 | 5.91 | 7.67 |
| Smart no overlap, budget 3 | 2.74 | 15.71 | 15.03 | 7.67 |
| Smart zero gain threshold, budget 3 | 3.00 | 13.82 | 13.36 | 0.00 |
| Smart no uncertainty penalty, budget 3 | 0.96 | 6.04 | 6.03 | 3.89 |

Source recall is the fraction of sources containing positively judged documents
that were selected. Document recall@10 is the fraction of positively judged
documents recovered in the top ten by shared embedding similarity, restricted
to selected sources. This evaluates candidate availability plus dense retrieval,
not generated-answer accuracy. Judgments are incomplete; a source with no
positive qrel is not necessarily irrelevant in the real world.

Broadcast source recall is 100% by construction, not a trained routing success.
It exceeds constrained methods' contact budgets and is a coverage reference.
Mean and max aggregation are shown separately, not treated as identical baselines.

## Measurable answers

### Does the budget constraint work?

Yes in this experiment: zero violations across 5,400 smart-method cases,
including all three budgets and ablations. This establishes empirical compliance
for the executed cases, alongside unit tests; it is not a formal privacy proof.

### Does the default keep useful evidence while reducing contacts?

Not adequately here. Against cosine mean top-3, budget-3 smart routing uses
69.22% fewer contacts but loses 10.74 percentage points of source recall and
9.73 percentage points of document recall@10. Do not present the contact
reduction alone as a quality-preserving privacy gain.

### Is adaptive selection using the larger budget?

No. All default-budget conditions return identical selections for every case:
831 cases select one source and 69 select none. All stop at insufficient_gain.
Increasing the budget therefore has no effect with these settings and profiles.

### Which components are implicated?

Removing overlap raises source recall from 5.92% to 15.71% and contacts from
0.92 to 2.74. Setting minimum gain to zero uses all three contacts and reaches
13.82% recall. Removing uncertainty alone still never selects more than one
source. These ablations implicate the overlap/gain rule on this source setup;
they do not identify an optimal replacement or prove a general causal claim
across all datasets.

### How fast is source selection?

Budget-3 smart selection has median 0.412 ms and p95 0.479 ms. Cosine mean top-3
has median 0.062 ms and p95 0.078 ms. These are local selection timings only,
excluding embedding, profile construction, retrieval, network and generation.
Smart normalizes profiles per call while cosine caches normalized profiles at
registration; implementation overhead is included and affects the comparison.

### Does this prove privacy or security benefits?

No. This run has no A2 observer, malicious sources, trust feedback, authentication
test, generation or real network transport. It cannot answer source-identity
privacy, query secrecy, hijacking resistance, answer quality or 1,000-server scale.
Official RAGRoute, HERouter, DP-CR and TASR were not benchmarked in this pilot.

## Across partition seeds

Source-recall means range from 5.25% to 7.18% for default smart, 14.86% to
18.80% for cosine mean top-3, and 13.28% to 18.13% for smart without overlap.
These are seed ranges, not confidence intervals or a significance test.

## What to do next

1. Keep the current run intact as a negative reference.
2. Define validation/test data that will not be reused for repeated tuning.
3. Reassess whether max centroid overlap measures actual evidence redundancy;
   random same-domain shards often have similar profiles but distinct evidence.
4. Evaluate stopping calibration and profile aggregation on validation data,
   with fixed-contact controls and separate quality/exposure targets.
5. Re-run frozen settings on new held-out conditions and source constructions.
6. Only then add attack/trust-stream evaluation and published baseline results.

Do not simply rename the best test-set ablation as a proven novel router.

## Reproduce and inspect

From the repository root, with the cached model and local corpus available:

```sh
env PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
  .venv/bin/python -m eval.run_smart_pilot \
  --corpus backend/vendor/beir/scifact --sources 30 --seeds 11 22 33 \
  --output experiments/smart-pilot-scifact-30-v1
```

The runner refuses to overwrite an existing output directory; use a new path
for another run. Existing results occupy about 18 MB and are gitignored locally:

- summary.csv: all metrics, including routing latency and seed ranges.
- decisions.jsonl: 9,900 raw method/query/partition decisions and smart traces.
- metadata.json: model/version/input hashes and code fingerprints.
- partition_*.json: document-to-source maps.
- embeddings.npz and profiles_*.npz: exact numeric inputs for this run.

Runner: [run_smart_pilot.py](../backend/eval/run_smart_pilot.py).
Metric/partition helper tests: [test_smart_pilot.py](../backend/tests/test_smart_pilot.py).
The full Python suite passed 163 tests after adding the pilot.

Router SHA-256 at measurement:
11659ba532bfbb344f2d5ccc7758290de98e53e9dbab3edb8330626731cf98ef.
The run metadata fingerprints the runner, profile builder, cosine router and
input files as well. No production algorithm or default was changed by this pilot.
