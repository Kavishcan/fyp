# Rich-profile routing: measured results

## Verdict

The development-selected lexical/semantic source router improves retrieval over
the 16-centroid cosine control on a separate FiQA transfer experiment. It does
**not** establish universal superiority: lexical-only is effectively tied on
random partitions, and candidate-recall differences against the approximately
byte-matched 21-centroid control have intervals crossing zero in both layouts.

This is a positive source-representation/selection result, not evidence that
the earlier adaptive candidate-allocation heuristic works. Preserve the negative
results in [the first pilot](21-evidence-budget-results.md) and
[the feedback study](25-feedback-routing-results.md).

## Implemented method

Each source builds 16 semantic centroids and an 8,192-byte hashed lexical
presence sketch from its own documents. The coordinator combines maximum
query-centroid cosine with a query-bucket match score weighted by inverse source
frequency. The selected mixture is 0.75 semantic + 0.25 lexical. It selects three
sources, requests four passages from each, and ranks the resulting 12 candidates
by the original query cosine to retain five.

The [frozen protocol](26-rich-profile-protocol.md) specifies tokenization,
hashing, source filtering, fusion, controls and fallback behavior. Missing or
invalid sketches at any eligible source, or no discriminative query buckets,
trigger whole-query semantic fallback. No additional query-time profile probes
are made. Every attempted candidate request is charged by the existing allocator.

No router or generator weights are trained. Centroid construction fits clusters,
and the mixture weight is selected with development relevance judgments; the
method is not free of fitting or hyperparameter tuning. Hashes are not a privacy
mechanism, and source-supplied sketches are not protected against forgery.

## Development and transfer

- Development: 807 SciFact and 323 NFCorpus queries, with the existing verified
  normalized-query exclusions. Grid: lexical weights 0, .25, .5, .75 and 1.
- Selection: maximize macro candidate recall, equally weighting each dataset
  and partition layout. Weight .25 won with 35.724% versus 27.290% for weight 0.
- Transfer: FiQA, 57,638 documents and 648 test queries, not used to select this
  study's method or weight. FiQA was used elsewhere in the project, so it is not
  claimed to have been untouched throughout the entire research process.
- Both stages: 30 simulated sources; random and topic-clustered assignments;
  seeds 11, 22 and 33; common cached MiniLM embeddings and retrieval backend.
- Topic assignments and profiles use corpus embeddings, not query judgments.
  These are simulated institutions, not naturally federated organizations.
- Completed: 61,020 development and 19,440 transfer query/configuration/seed
  decisions, with zero budget violations. These are not 80,460 unique queries.
- Every transfer decision contacted exactly 3 sources and requested/returned
  exactly 12 candidates. No LLM generation was evaluated.

## Transfer quality

All values below are percentages. Candidate recall measures the fraction of gold
documents in the collected 12 passages; final recall measures the fraction in
the final five. Neither is answer accuracy or multi-hop evidence completeness.
Each row averages 648 queries across three partition seeds.

| Layout | Source selection | Candidate recall | Final Recall@5 | nDCG@5 |
|---|---|---:|---:|---:|
| Random | Semantic 16 centroids | 9.710 | 8.573 | 8.946 |
| Random | Semantic 21 centroids | 9.882 | 8.330 | 9.177 |
| Random | Lexical with semantic fallback/ties | 11.080 | 9.817 | 10.308 |
| Random | Unweighted RRF | 10.101 | 8.873 | 9.568 |
| Random | **Hybrid, weight .25** | **11.067** | **9.804** | **10.320** |
| Topic | Semantic 16 centroids | 34.972 | 31.499 | 30.462 |
| Topic | Semantic 21 centroids | 35.354 | 31.796 | 30.717 |
| Topic | Lexical with semantic fallback/ties | 35.091 | 31.592 | 30.676 |
| Topic | Unweighted RRF | 28.405 | 26.395 | 25.904 |
| Topic | **Hybrid, weight .25** | **35.798** | **32.299** | **31.240** |

### Uncertainty

Hybrid minus comparator, in percentage points, with 95% paired query-cluster
bootstrap intervals (10,000 resamples; seeds averaged within each of 648 queries).
Intervals are descriptive and not adjusted for multiple comparisons.

| Layout | Comparator | Candidate recall difference [95% interval] | Final recall difference [95% interval] |
|---|---|---|---|
| Random | Semantic 16 | +1.357 [+0.553, +2.191] | +1.231 [+0.441, +2.062] |
| Random | Semantic 21 | +1.185 [-0.159, +2.530] | +1.474 [+0.204, +2.747] |
| Random | Lexical | -0.013 [-0.180, +0.154] | -0.013 [-0.180, +0.154] |
| Random | RRF | +0.966 [+0.185, +1.783] | +0.931 [+0.180, +1.720] |
| Topic | Semantic 16 | +0.826 [+0.017, +1.668] | +0.799 [+0.015, +1.598] |
| Topic | Semantic 21 | +0.443 [-0.616, +1.555] | +0.503 [-0.468, +1.515] |
| Topic | Lexical | +0.707 [+0.242, +1.255] | +0.707 [+0.212, +1.269] |
| Topic | RRF | +7.393 [+6.082, +8.767] | +5.903 [+4.627, +7.251] |

The topic-layout improvement over semantic16 is small with a lower interval
close to zero. The primary candidate-recall advantage over semantic21 remains
unresolved. RRF here is standard unweighted rank fusion, not a tuned weighted
RRF competitor. Absolute recall on randomly scattered sources remains low.

## Costs and limitations

For 384-dimensional float32 centroids, canonical binary profile size is 24,576
bytes for semantic16, 32,768 for hybrid and 32,256 for semantic21. Hybrid therefore
adds 33.3% to semantic16 and costs 512 bytes more than semantic21. Mean serialized
representation JSON in FiQA was approximately 147-148 KB/source for hybrid versus
179-180 KB for semantic21; numeric JSON and base64 have different overheads.
These sizes cover the measured representation fields, not full MCP wire traffic.
Live registered profiles can publish the sketch even for a semantic request.

Mean warm cached allocator time was about 1.74 ms/query for hybrid versus 1.70 ms
for semantic16. This excludes embedding, local search, transport and generation;
it is not end-to-end latency. Hybrid returned about 10.18 KB of UTF-8 passage text
per random-layout query and 9.40 KB per topic-layout query, excluding envelopes.

Lexical bit occupancy averaged 19.3% in random layouts and 16.0% in topic layouts.
Collisions, saturation, common query terms, profile staleness and false source
claims need further study. Local presence does not establish that query terms
co-occur in a supporting document. No privacy or profile-hijacking defense was
demonstrated. No 1,000-server deployment or answer-quality gain was measured.

The live API/MCP path still uses hashing embeddings; these quality measurements
use MiniLM. MCP integration tests establish publication, fallback and retrieval
correctness, not identical semantic quality or production performance.

## Reproduce and use

Completed development artifacts: `experiments/routing-study-rich-dev-v2/`.
Completed transfer artifacts: `experiments/routing-study-rich-transfer-v1/`.
The earlier `routing-study-rich-dev-v1/` was aborted on an artifact-path error
before query evaluation and is not evidence. Experiment directories are ignored
by Git; preserve/export them separately when sharing a reproducibility package.

Each completed run records manifests, code/protocol snapshots and hashes,
profile assignments, profile costs, summary CSV and raw decision JSONL. The
development run includes `development.json` and `frozen.json`; transfer includes
`intervals.json` and cached FiQA embeddings. Code/protocol and summary hashes
were verified after completion. Commands are in the frozen protocol.

The selected opt-in API configuration is:

```json
{
  "question": "How does diversification affect investment risk?",
  "method": "equal",
  "profile_strategy": "hybrid",
  "lexical_weight": 0.25,
  "max_sources": 3,
  "candidate_budget": 12,
  "final_k": 5
}
```

Send to `POST /query/evidence`. Here `equal` controls passage quotas; `hybrid`
controls source selection. Re-register existing sources with metadata enabled
to publish lexical sketches. Old/mixed profiles use semantic fallback. Runtime
defaults, legacy routing and studio behavior have not been promoted or replaced.

Verification: 311 Python tests passed, including real MCP profile/retrieval
integration; TypeScript no-emit checking and `git diff --check` passed.

## Research claim and next tests

A defensible current statement is: "A development-selected compact hybrid source
profile improved fixed-budget retrieval over a 16-centroid cosine source router
on simulated FiQA partitions, with a measured profile-size trade-off."

This is not yet a defensible claim of a novel superior research algorithm.
Lexical/semantic fusion, resource profiles and inverse collection frequency have
prior art: [CORI](https://sigir.org/wp-content/uploads/2017/06/p160.pdf),
[RRF](https://doi.org/10.1145/1571941.1572114), and
[FeB4RAG](https://arxiv.org/html/2402.11891v1). The implementation is not a
reproduction of those systems or of [RAGRoute](https://arxiv.org/html/2502.19280v1).

Next: freeze another transfer benchmark; compare official routing baselines and
development-tuned RRF; sweep profile bytes and contact/candidate budgets; measure
answer quality with matched context tokens; integrate compatible semantic
embeddings into the live path. If retaining the earlier trust/security scope,
add forged-sketch attacks and independent defenses rather than claiming the
current sketch is trustworthy. Confirm the resulting research scope with the
supervisor before expanding implementation further.
