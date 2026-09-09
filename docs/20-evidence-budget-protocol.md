# Evidence-budget routing: exploratory protocol

Branch: `research/evidence-budget-routing`. This builds on the uncommitted
centering experiment without changing the legacy or smart routing defaults.
This document specifies a hypothesis, not an established novel contribution.

## Research question

Can a training-free sequential selector recover more judged-relevant passages
by choosing both the next client and its retrieval depth, under the same caps
on distinct clients C and candidate requests B?

Working title: Evidence-Aware Client Selection and Adaptive Candidate Budget
Allocation for Federated RAG. "Evidence-aware" means embedding-based feedback
from actually returned passages, not knowledge of which facts are required.

## Fixed experimental rule

Normalize query q and all profile centroids c_ij in the same encoder space.
For each source i:

- a_ij = max(0, cosine(q, c_ij)); r_i = max_j a_ij.
- w_ij = a_ij^2 / sum_j a_ij^2. Skip invalid or zero-relevance profiles.
- h_ij = max over returned unique passages p of max(0, cosine(c_ij, p))^2;
  h starts at zero.
- u_i = sum_j w_ij (1 - h_ij), the residual profile coverage proxy.
- l_i is the most recently returned passage's nonnegative query cosine;
  before any retrieval l_i = r_i.
- g_i = ((r_i + l_i) / 2) * u_i / sqrt(n_i + 1).

Choose the eligible source with largest g_i, then larger r_i, then source ID.
Request exactly one passage at zero-based local rank n_i. A new source is
eligible only while fewer than C distinct sources have been contacted.
Increment n_i and spend one of B slots BEFORE retrieval. All parameters above
are fixed before the pilot, not optimized on its results. Fill the budget even
if residual scores are zero; this is not a calibrated stopping rule.

Failures, empty responses, malformed vectors and duplicate passages consume
their requested slot. Failures/empty responses disable that source for the
rest of the query. Deduplicate global candidate IDs; repeated IDs never add
context or coverage. A document embedding must be produced by the coordinator
encoder. Local source scores are ignored. No cross-query trust update is used.

The diminishing-depth factor and profile coverage are heuristic predictions.
There is no submodularity/optimality guarantee, trained value model, formal
privacy guarantee, claim verification, or demonstrated worldwide novelty.
Semantic similarity can suppress complementary evidence; this is a core risk.

## Controls and ablations

| Method | Source choice | Candidate allocation |
|---|---|---|
| equal | Cosine top-C | One per source, then uniform remainder |
| proportional | Cosine top-C | One per source, then relevance-proportional Hamilton remainder |
| profile_only | Sequential over all eligible sources | r_i / sqrt(n_i + 1), no evidence feedback |
| allocation_only | Restricted to cosine top-C | Full feedback rule, variable depth |
| joint | Sequential over all eligible sources | Full feedback rule, variable depth |

Fixed quotas are executed round-robin with no hidden probes. Fixed controls do
not reassign failed slots; report their actual counts. The pilot uses healthy,
nonempty sources so failure behavior is tested separately in unit tests.
All methods use the same callback, per-request page size, encoder, profiles,
local rankings, candidate cap and final top-5 cosine reranker. B counts raw
candidate requests, not unique passages after deduplication. C counts distinct
clients; repeated requests count separately. Text bytes are measured payload
text only, not complete MCP wire traffic. Profile publication is offline and
excluded from per-query counts. No query-time metadata fetch is free.

Broadcast is not a matched-C baseline when C=3 among 30 sources. Official
RAGRoute and SCOUT-RAG are NOT reproduced by these controls. Those comparisons
remain necessary before making broader research claims.

## Pilot, frozen before execution

- Offline cached MiniLM embeddings, snapshot recorded in manifest. No download
  or training. SciFact 300 queries, NFCorpus 323, SCIDOCS 1,000.
- Reuse all three prior disjoint random 30-source partitions, seeds 11/22/33,
  and 16-centroid profiles. These are virtual shards, not 30 organizations.
- C=3, B in {6,12}, final K=5; five methods, all queries and seeds.
- Primary: candidate judged-relevant-document recall at B=12. Secondary:
  final Recall@5, binary nDCG@5, relevant-source recall, contacts, requests,
  text bytes and allocator wall time. Report each dataset, not only a macro gain.
- Paired 10,000-resample query-cluster bootstrap, averaging partition seeds
  within each query. 95% intervals are descriptive, not multiplicity-corrected.
- Same historical test queries have already been inspected: this is an
  EXPLORATORY regression pilot, not a fresh held-out confirmation. Do not tune
  parameters on these results and call a subsequent run a held-out test.
- Precompute local rankings inside the simulator only. The policy sees only
  profiles and paid returned candidates. Timing excludes local index search,
  embedding and transport: it is NOT end-to-end latency.
- No LLM generation is evaluated. A top-5 passage cap is not a token budget.
  Passage recall from BEIR qrels is not all-required-facts coverage or multi-hop
  answer accuracy. Those require a separate QA study with supporting evidence,
  a fixed generator and matched context-token cap.

## Offline oracle diagnostic

For each query, use gold relevance labels ONLY in the evaluation harness to
maximize relevant documents in local ranking prefixes under C and B. An exact
multiple-choice knapsack considers (source, prefix length) options. Report
both fixed-top-C-source quota headroom and joint source/quota headroom. The
upper bound relies on disjoint document partitions and is not a deployable
router or a claim that an unsupervised heuristic can achieve it.

## API and transport

`POST /query/evidence` is opt-in; existing `/query` behavior is unchanged.

```json
{"question":"What evidence supports this treatment?","max_sources":3,
 "candidate_budget":12,"final_k":5,"method":"joint"}
```

The endpoint filters profiles through existing coordinator policy labels,
uses the current hashing demo encoder, requests paginated text through MCP or
the in-process node, re-embeds it locally, merges and optionally generates.
MCP `retrieve(query, top_n=1, offset=n)` is required for repeated source reads.
Nodes must keep local rankings/corpora stable throughout the query. The current
MCP demo recreates a process/index per call; persistent sessions and stable
snapshot cursors are future deployment work. There is no fallback to fetching
uncharged top-n prefixes from old servers. API responses include an action ledger.

No studio changes, authenticated production access control, model training,
or privacy/attack-resilience claims are part of this experiment.

## Reproduction

```bash
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_candidate_study --output experiments/routing-study-candidates-v1
.venv/bin/pytest -q
```

Requires the earlier local cached experiment artifacts. The harness fails on
missing inputs rather than downloading. Use a fresh output directory. It saves
raw actions, per-query metrics, oracle diagnostics, intervals, input hashes,
the code/protocol snapshot and manifest; raw artifacts remain gitignored.
