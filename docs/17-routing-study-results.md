# Routing improvement and profile-cloning results

## Verdict

The implementation is improved over the old default, but the proposed research
claim is **not yet established**. Finer source profiles help; the relative
stopping rule trades away measurable recall. EvidenceTrust suppresses an empty
clone but harms clean retrieval and does not eliminate bait-based exposure.
Do not describe these results as a new state-of-the-art router or formal privacy.

## What was implemented

- Opt-in `selection_policy="relative"` in SmartRouter and the API contract.
- No centroid-overlap penalty in this mode; a relative score/cost floor instead.
- Existing authorization, positive cost, strict budget and source-cap checks.
- Unchanged default policy, generator, live hashing encoder and trust update.
- Offline runner with coarse/fine profiles, matched baselines, budget sweeps,
  query-cluster confidence intervals and online profile-cloning stress tests.
- Upstream TASR feedback loaded directly from the vendored file. Its weights
  augment max-centroid ranking; this is not the paper's full router reproduction.

The implementation does not use qrels to select sources, build profiles, forge
profiles or update trust. Profiles are built from local documents only.
Clustering is data-dependent preprocessing; 'training-free' means no supervised
router fitting or embedding/LLM fine-tuning, not that no computation is fitted
to source documents.

## Data and protocol

See [the protocol fixed before execution](16-routing-study-protocol.md).

| Dataset | Documents | Unique test queries | Source partitions |
|---|---:|---:|---|
| SciFact | 5,183 | 300 | 30 random shards, seeds 11/22/33 |
| NFCorpus | 3,633 | 323 | 30 random shards, seeds 11/22/33 |

The three partitions reuse the same questions, not three independent query
samples. SciFact was already inspected during development. NFCorpus is a
one-pass cross-dataset test in this experiment, with no threshold selection
from its results; earlier historical use was not audited. These are simulated
clients, not 30 independent institutions. Both tests use the cached
all-MiniLM-L6-v2 snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`,
normalized embeddings, CPU execution and a 256-token sequence limit.

There were 57,939 method/query/partition/scenario cases, including 1,869 broadcast
reference cases. All 56,070 bounded cases respected their specified contact cap.
This is implementation evidence for a recipient constraint, not measured secrecy.

## Clean results at budget 3

Recall columns are percentages; they are not answer accuracy.

| Dataset | Method | Mean contacts | Source recall | Document recall@10 |
|---|---|---:|---:|---:|
| SciFact | Old mean/overlap, 4 centroids | 0.92 | 5.92 | 5.91 |
| SciFact | Fixed max-cosine, 4 centroids | 3.00 | 19.90 | 18.94 |
| SciFact | Relative rule, 4 centroids | 2.90 | 19.29 | 18.31 |
| SciFact | Fixed max-cosine, 16 centroids | 3.00 | 29.77 | 28.42 |
| SciFact | Relative rule, 16 centroids | 2.86 | 28.50 | 27.37 |
| NFCorpus | Old mean/overlap, 4 centroids | 0.68 | 2.60 | 1.48 |
| NFCorpus | Fixed max-cosine, 4 centroids | 3.00 | 11.18 | 4.25 |
| NFCorpus | Relative rule, 4 centroids | 2.66 | 10.18 | 4.09 |
| NFCorpus | Fixed max-cosine, 16 centroids | 3.00 | 12.49 | 6.32 |
| NFCorpus | Relative rule, 16 centroids | 2.69 | 11.14 | 5.86 |

Broadcast source recall is 100% by construction; its document recall@10 is
78.33% on SciFact and 15.50% on NFCorpus. NFCorpus has many relevant documents
per query, so the top-10 denominator differs substantially from SciFact. Do not
compare the two percentages as though they measure identical task difficulty.

Paired 95% query-cluster bootstrap intervals for source-recall differences:

| Contrast | SciFact, percentage points | NFCorpus, percentage points |
|---|---:|---:|
| Fine fixed minus coarse fixed | +9.87 [6.34, 13.46] | +1.31 [0.05, 2.65] |
| Fine relative minus fine fixed | -1.28 [-2.39, -0.44] | -1.35 [-1.83, -0.95] |

The relative rule saves 4.67% and 10.46% of contacts, respectively, but loses
recall. No non-inferiority margin was specified, so 'equivalent quality' is not
supported. Intervals are conditional on these three partitions, exploratory,
and uncorrected for the multiple reported contrasts. The finer representation
is the clearest measured improvement; it is not a new routing algorithm.

## Profile publication cost

Mean serialized profile JSON bytes per source increased from 34,310 to 136,431
on SciFact, and from 34,225 to 136,092 on NFCorpus: approximately four times as
much profile data. These are payload sizes, not measured MCP wire traffic.
More centroids may expose more collection information; no leakage attack or
formal privacy analysis was performed on these profiles.

## Cloned-profile stress tests

One extra endpoint copies source 0's fine profile before seeing test queries.
It either returns no passages or replays source 0's top-five genuine passages.
The second scenario models a profile-cloning endpoint that can supply relevant
bait. It does not test fabricated factual content. All methods see the same
forgery, question order and available corpora; feedback uses only contacted
sources and updates after selection. Budgets remain 3 including the attacker.

The following numbers are percentages of queries sent to the attacker:

| Policy / feedback | SciFact empty | SciFact bait | NFCorpus empty | NFCorpus bait |
|---|---:|---:|---:|---:|
| Fixed fine, no feedback | 6.78 | 6.78 | 6.91 | 6.91 |
| Relative fine, no feedback | 6.44 | 6.44 | 6.40 | 6.40 |
| Relative + EvidenceTrust | 0.11 | 3.22 | 0.21 | 2.06 |
| Fixed fine + TASR feedback | 3.00 | 42.56 | 2.68 | 47.37 |
| Relative fine + TASR feedback | 3.00 | 17.11 | 2.37 | 36.53 |

**Do not interpret the last rows as a general defeat of TASR.** This is a
particular transfer test with random same-domain shards, cloned profiles,
default feedback thresholds and a max-centroid base scorer. The clone and
donor return identical relevant evidence, which can reinforce agreement and
reputation. That is an interpretation requiring signal-level follow-up, not
an established causal explanation. Official TASR datasets/settings were not
reproduced; its optional extra exploration was disabled for the hard cap.

The no-attack online control exposes the cost of feedback:

| Policy | SciFact honest-source recall | NFCorpus honest-source recall |
|---|---:|---:|
| Fixed fine, no feedback | 29.77 | 12.49 |
| Relative fine, no feedback | 28.50 | 11.14 |
| Relative + EvidenceTrust | 25.56 | 10.64 |
| Fixed fine + TASR feedback | 29.44 | 12.31 |
| Relative fine + TASR feedback | 26.16 | 11.13 |

The current trust heuristic reduces malicious contacts partly at a utility
cost. These descriptive stream results are not IID significance estimates.
Only one cloned donor and one attacker are tested; multiple attackers, profile
optimization, source churn and semantic poisoning remain untested.

Clean `evidence_coverage` measures judged documents available anywhere in the
selected source pool. Online `evidence_coverage` measures judged documents in
the actual returned top-five-per-source pool. Compare this metric only within
the same scenario; these denominators share qrels but the accessible pools
differ. Online source recall excludes the clone from honest-source coverage;
replayed relevant documents still count towards returned-document recall.

## API use

Register each source with a chosen `k` (for example 16, capped by document
count), or set `k` in its MCP node specification. Then submit:

```json
{
  "question": "Which evidence supports this claim?",
  "routing_mode": "smart",
  "selection_policy": "relative",
  "aggregation": "max",
  "relative_score_floor": 0.8,
  "minimum_gain": 0,
  "exposure_budget": 3,
  "max_nodes": 3
}
```

No new UI selector was added. Live inference retains the hashing encoder,
existing uncertainty penalty and one-passage retrieval; it is not numerically
identical to the semantic, controlled offline benchmark.
MCP nodes accept a positive integer `k`, defaulting to four, but retain their
existing profile noise (sigma 0.05); the offline experiment uses sigma zero.

## Reproduce and inspect

```sh
env PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  .venv/bin/python -m eval.run_routing_study \
  --output experiments/routing-study-reproduction

.venv/bin/python -m pytest -q
```

Completed outputs are in `experiments/routing-study-v1/`: `summary.csv`,
`intervals.json`, `decisions.jsonl`, embedding/partition/profile artifacts and
`metadata.json`. Raw artifacts remain local and ignored by Git. The runner
refuses to overwrite existing output. Metadata records dataset/code hashes,
configuration and model revision. A SmartRouter docstring was clarified after
this run; its recorded hash therefore predates that comment-only edit.

Verification: Python tests cover real-MCP dispatch/profile-size configuration, API,
budget, deterministic ordering, qrel isolation and metric tests.
Final verification: 201 tests passed; TypeScript `tsc --noEmit --incremental false`
and `git diff --check` passed. No model downloads, supervised training, external
generation calls, Git commits or pushes were performed for this change.

## What remains before the stronger research claim

1. An evidence-aware rule that improves the quality/contact frontier beyond
   the same-profile fixed baseline, evaluated on a fresh development/test plan.
2. Profile-size and source-overlap ablations, natural source partitions and
   additional datasets; do not repeatedly tune the tests above.
3. Matched official RAGRoute and fuller TASR/SCOUT-RAG comparisons. A checkpoint
   trained for different source identities is not an appropriate baseline here.
4. Stronger, separately specified attacker tests and honest-client utility
   controls. Authenticating a source alone does not prove its profile truthful.
5. Actual answer quality, end-to-end MCP latency/bytes and a justified privacy
   threat model. Recipient-count compliance does not establish secrecy.
