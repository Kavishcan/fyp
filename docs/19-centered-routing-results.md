# Development-selected routing experiment

## Decision

The proposed centering change did not improve development recall. The registered
selection rule chose strength 0, which retains ordinary cosine ranking. Do not
call this a new superior ranking algorithm. The useful configuration change is
to remove an unvalidated early-stop threshold when coverage is the priority,
while retaining the strict contact budget.

The experimental centering option is implemented and tested, but not promoted
as the recommended operating mode. Legacy/API defaults remain unchanged.

## Development protocol and result

See [the protocol written before the experiment](18-centered-routing-protocol.md).
Use official SciFact train and NFCorpus dev judgments, with exact case/whitespace
normalized test-text overlaps removed. Development has 807 SciFact queries
(2 excluded) and 323 NFCorpus queries (1 excluded). The sources are the same
30 random shards and frozen 16-centroid profiles as routing-study-v1, across
seeds 11/22/33. No profiles are built using query judgments.

The encoder is cached all-MiniLM-L6-v2, snapshot
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, with a 256-token limit.
The two datasets receive equal weight after averaging partition seeds.
Development selects a hyperparameter using labels; it does not train model
weights. That distinction must accompany the term training-free.

| Centering strength | Macro development source recall, budget 3 |
|---|---:|
| 0, raw cosine | 21.49% |
| 0.25 | 21.16% |
| 0.50 | 20.71% |
| 0.75 | 20.27% |
| 1.00 | 19.43% |

The frozen setting was saved before any additional transfer evaluation.
No setting was changed in response to test results. At strength zero the
centered method name in output files denotes an identity transform, not a
different geometric ranking. Its extra normalization has no intended benefit.

## Frozen test results

The run completed 116,856 method/query/partition/scenario decisions, with zero
recorded budget violations. These are repeated method evaluations, not 116,856
independent questions. Test queries: SciFact 300, NFCorpus 323, SCIDOCS 1,000.
Corpora contain 5,183, 3,633 and 25,657 documents respectively. Each corpus is
split into 30 simulated sources under three seeds. All methods see the same
16-centroid profiles. SciFact/NFCorpus are exploratory regressions; SCIDOCS is
the registered one-pass additional benchmark.

At budget 3, percentages below are retrieval measurements, not answer accuracy:

| Dataset | Method | Mean contacts | Source recall | Available evidence coverage | Document recall@10 |
|---|---|---:|---:|---:|---:|
| SciFact | Earlier relative floor 0.8 | 2.86 | 28.50% | 28.52% | 27.37% |
| SciFact | Budget filling / raw top-3 | 3.00 | 29.77% | 29.80% | 28.42% |
| NFCorpus | Earlier relative floor 0.8 | 2.69 | 11.14% | 11.72% | 5.86% |
| NFCorpus | Budget filling / raw top-3 | 3.00 | 12.49% | 13.08% | 6.32% |
| SCIDOCS | Earlier relative floor 0.8 | 2.96 | 12.41% | 12.69% | 6.92% |
| SCIDOCS | Budget filling / raw top-3 | 3.00 | 12.53% | 12.82% | 6.99% |

The budget-filling and raw fixed controls selected exactly the same sources in
all 14,607 paired clean query/partition/budget cases. Every predeclared contrast
(three datasets, budgets 1/3/5, source recall/evidence coverage/document recall/
contacts) has difference 0 and bootstrap interval [0, 0]. This is parity of
identical observed decisions, not proof of population-level equivalence between
distinct algorithms. In particular, the primary SCIDOCS contrast does not show
an advantage at equal contacts.

Budget sweep, source recall percentages:

| Dataset | Budget | Earlier rule: contacts / recall | Budget filling: contacts / recall |
|---|---:|---|---|
| SciFact | 1 | 1.00 / 15.05% | 1.00 / 15.05% |
| SciFact | 3 | 2.86 / 28.50% | 3.00 / 29.77% |
| SciFact | 5 | 4.55 / 36.50% | 5.00 / 39.63% |
| NFCorpus | 1 | 1.00 / 4.56% | 1.00 / 4.56% |
| NFCorpus | 3 | 2.69 / 11.14% | 3.00 / 12.49% |
| NFCorpus | 5 | 3.98 / 16.14% | 5.00 / 20.25% |
| SCIDOCS | 1 | 1.00 / 4.67% | 1.00 / 4.67% |
| SCIDOCS | 3 | 2.96 / 12.41% | 3.00 / 12.53% |
| SCIDOCS | 5 | 4.83 / 19.68% | 5.00 / 20.33% |

The gain over early stopping comes with more contacts. No matched-contact
advantage, evidence-sufficiency stopping rule or new ranking contribution is
established by this table.

## Trust and cloned-profile tests

The attacker copies source_000's profile before the query stream. Empty clones
return nothing; bait clones return the donor's top-five passages. This measures
query exposure to a cloned identity, not factual poisoning or a general adaptive
attacker. The same fixed shuffled stream and only post-contact feedback are used
in paired conditions. All these budget-filling streams contact three sources.

Percentage of queries contacting the attacker:

| Dataset | Empty: neutral trust | Empty: EvidenceTrust | Bait: neutral trust | Bait: EvidenceTrust |
|---|---:|---:|---:|---:|
| SciFact | 6.78% | 0.22% | 6.78% | 4.44% |
| NFCorpus | 6.91% | 0.41% | 6.91% | 6.19% |
| SCIDOCS | 5.93% | 0.10% | 5.93% | 8.17% |

Honest-source recall shows the cost of the feedback:

| Dataset | No attack: neutral / EvidenceTrust | Bait attack: neutral / EvidenceTrust |
|---|---|---|
| SciFact | 29.77% / 27.46% | 28.77% / 26.27% |
| NFCorpus | 12.49% / 11.86% | 12.26% / 11.58% |
| SCIDOCS | 12.53% / 12.40% | 12.30% / 12.22% |

EvidenceTrust helps against an empty clone but can reinforce matching bait.
On SCIDOCS it increases bait exposure by 2.23 percentage points and slightly
reduces honest-source recall. These are descriptive, history-dependent streams;
no independent-query confidence interval is claimed. Raw and zero-strength
centered variants have the same selection semantics. Do not call this a solved
profile-hijacking defence, or change its settings using these test outcomes.

## Verification

217 Python tests passed, including API field forwarding, weighted budget and
authorization invariants, zero-vector handling, development selection, and real
MCP subprocess retrieval. TypeScript checking and git diff --check passed.
Source/protocol fingerprints matched the executed snapshot. The new tests do
not establish semantic-model integration or network-scale performance.

## Measurement boundaries

- Source recall is the fraction of relevant source shards contacted, not answer accuracy.
- Clean evidence coverage counts relevant documents available anywhere in selected shards.
- Clean document recall@10 ranks documents from selected shards using raw MiniLM cosine.
- Online feedback retrieves at most five passages per contacted source; its evidence coverage counts returned passages, so it is not directly comparable to clean available coverage.
- The router never receives test judgments or uncontacted-source evidence.
- Budget filling may spend more contacts than early stopping. It is not evidence-aware stopping.
- Routing latency is local computation, not network or end-to-end latency. The centered-fixed control caches transformed profiles; the production router recomputes them for eligible sources, so their timings are not like-for-like algorithm speedups.
- Trust measures profile/passage consistency, not honesty. A bait source can still receive queries.
- These are 30 simulated shards, not independent organizations; no claims about 1,000 live clients follow.
- No generator, formal privacy guarantee, route-inference test, or completed RAGRoute reproduction is included.

## Reproduce

Use the existing local data, cached model, and frozen routing-study-v1 artifacts.
No dataset or model downloads are made. Both commands require fresh output paths:

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python \
  -m eval.run_centered_study develop --output experiments/routing-study-centered-dev-v1
PYTHONPATH=backend OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python \
  -m eval.run_centered_study evaluate --output experiments/routing-study-centered-test-v1 \
  --frozen experiments/routing-study-centered-dev-v1/frozen-config.json
```

The development directory contains all seed/strength results, the retained
query IDs and embeddings, frozen config and source snapshots. The test directory
contains decisions.jsonl, summary.csv, intervals.json, profile/partition files,
SCIDOCS embeddings, input fingerprints and the exact source/protocol snapshots.
Large experiment artifacts remain local and gitignored. This report is tracked.

## API configuration

Use the [coverage-oriented request](13-smart-router-implementation.md#coverage-oriented-request)
with relevance_mode=centroid, aggregation=max, selection_policy=relative,
relative_score_floor=0 and minimum_gain=0. All selected-source costs still
count against the budget, including failed contacts.

The live API uses hashing embeddings and ongoing consistency-trust feedback;
the clean benchmark uses MiniLM and equal trust. The demo therefore does not
inherit the offline quality numbers automatically.
