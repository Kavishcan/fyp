# Discovery/completion results and next steps

## Verdict

Implemented an experimental query-deficit discovery/completion allocator in
`backend/router/discovery_completion.py`, with a node-local action selector.
This is callable Python, not yet a new HTTP/MCP endpoint or UI feature.
Existing defaults are unchanged. Do not claim novelty or superiority.
Protocol and formulas: doc 33. Reading pack: doc 32.

## Measured results

Artifacts: `experiments/routing-study-discovery-completion-v1/`.
2,556 queries, four policies, 10,224 decisions. Metrics below average over
2,255 evidence-bearing questions. All methods use the same frozen hybrid
source selector, up to three sources, twelve requests and five final chunks.
No downloads, training or generator calls were performed.

| Acquisition method | Candidate document recall | Final document recall | Candidate literal fact coverage | Final literal fact coverage |
|---|---:|---:|---:|---:|
| Equal cosine | 62.54% | 50.89% | 32.75% | 23.88% |
| Equal parent-cap1 | 72.56% | 59.21% | 24.84% | 20.81% |
| Adaptive discovery-only | 74.37% | 59.59% | 25.16% | 20.82% |
| Adaptive discovery/completion | 57.03% | 50.17% | 29.32% | 23.41% |

The new completion method does not beat cosine. It improves literal fact
coverage over document diversification but sacrifices document recall.
Discovery-only improves the document proxy slightly, not fact coverage.
This demonstrates why document-ID recall alone was an inadequate success test.

For completion versus cosine, the final fact-coverage difference is -0.466
percentage points. A paired question bootstrap (10,000 samples, seed 20260910)
gives a 95% interval of [-1.075, +0.126] points: no demonstrated improvement.
There are 117 wins, 1,995 ties and 143 losses on this metric.
These are exploratory, uncorrected query-level intervals, not article-cluster
inference and not a new held-out test.

## Evaluation boundaries

Supporting facts come only from raw MultiHopRAG annotations, matched by query
with answer consistency checked. Their normalized literal text is searched
within chunks of gold documents. Of 6,084 fact instances, 211 (3.47%) do not
match a single gold chunk and remain in the denominator. Causes may include
paraphrase or chunk boundaries; they were not individually classified.
Literal matching is not semantic entailment, faithfulness or answer accuracy.

No request/candidate/final-size budget violations occurred. The completion
policy made 14,798 successful discovery calls, 15,839 successful completion
calls and 35 empty discovery calls; empty calls consumed budget.
This benchmark uses cached local rankings, not production network latency.
Query-term deficits can prefer irrelevant extra details and miss implicit
relations. Five observed parents is a heuristic completion threshold.

## Next steps

1. Keep cosine and parent-cap1 as controls; do not promote this candidate.
2. Inspect errors on a development split to distinguish wrong sources, wrong
   chunks and global reranking losses. Keep untouched article groups for a
   later test. Existing MultiHop results must stay labelled exploratory.
3. Evaluate semantic supporting-fact coverage and actual generated answers
   with a fixed generator. Obtain compute/API approval before running it.
4. Test a revised, explicitly justified completion signal only after freezing
   the protocol. Avoid tuning a long series of heuristics on these queries.
5. Integrate action requests into HTTP/MCP only if the revised method earns
   a quality/cost benefit. MCP connectivity itself is not the contribution.

## Reproduce

Use a new output directory; the runner refuses to overwrite previous runs.

```sh
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=backend .venv/bin/python -m eval.run_discovery_completion --output experiments/routing-study-discovery-completion-recheck
env PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
```

The manifest records cached-input checksums and the new controller/runner/
protocol snapshots. Shared dependency versions remain those of this checkout;
the snapshot is not a standalone environment lock or complete source archive.
