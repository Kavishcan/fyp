# MCP metadata extension and measured comparison

## What was implemented

Sources can now publish these additional application-defined fields through
their existing MCP get_profile tool:

- description: a compact document-derived keyword description.
- topics: up to 16 document-frequency keywords, with deterministic tie ordering.
- description_embedding: embedded in the shared routing space.
- metadata_method and metadata_embedding_model: construction and model identifiers.

The builder is nodes/metadata.py. It accepts documents only, not query text,
query IDs, qrels or target routing labels. It uses no LLM. Each document gives
a term one vote regardless of repetition; English stopwords and recognized
email/phone/ID patterns are removed before extraction. This is a simple,
extractive first implementation, not a comprehensive collection summary.

MCP and simulated sources both build the fields before registration. The
coordinator caches them and does not probe every source with a question.
Descriptions/topics are visible in GET /nodes. Description vectors stay in
the source profile used internally for routing and in the MCP profile payload.

MCP source files and simulated registration requests accept publish_metadata=false.
Metadata can disclose names or sensitive collection topics despite heuristic
redaction. Opt-out disables metadata publication; it does not hide existing
centroids. Source-reported metadata and model identifiers are not authenticated.

The MCP centroid seed now uses SHA-256 of source ID rather than Python's
process-randomized hash, so fresh processes publish reproducible profiles for
the same source data. Policy labels from node files are also preserved.
The old pilot's saved numeric profiles were not regenerated or overwritten.

## Routing modes

The default remains centroid-only. Explicit smart relevance modes are:

```text
centroid:    original mean/max clipped centroid-query cosine
description: clipped cosine(query, description_embedding)
combined:    (1-w)*centroid_score + w*description_score; default w=0.5
```

Trust, budget, centroid-overlap penalty and stopping defaults are unchanged.
Missing/incompatible description vectors exclude sources in metadata modes;
there is no silent centroid fallback. The coordinator checks the declared
model identifier and vector dimensions. This is compatibility checking, not
proof that a malicious source actually used the declared encoder.

Example after registering compatible sources:

```sh
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"COVID treatment research","routing_mode":"smart","relevance_mode":"combined","description_weight":0.5,"aggregation":"max","exposure_budget":3,"max_nodes":5}'
```

The API uses the adaptive stopping rule, not the forced-top-3 diagnostic below.
The studio still has no metadata-mode selector; requests are available through
the API and its updated TypeScript contract. Live sources still use hashing;
the scientific pilot below explicitly uses the cached semantic model.

## Quality experiment

Reused the exact previous pilot input artifacts: 5,183 SciFact documents,
300 unique test questions, 30 balanced random source shards and seeds 11/22/33.
Model: cached all-MiniLM-L6-v2, same snapshot and frozen document/query embeddings.
The source descriptions use only the documents assigned by each frozen manifest.
No queries/qrels entered metadata construction or mixture-weight selection.

There are 900 query/partition cases per method, sharing 300 questions, not 900
independent queries. This is an exploratory follow-up on already inspected test
data, not an untouched confirmatory benchmark. No optimality or generalization
claim should be drawn from these settings.

Five fixed-contact controls rank sources and select exactly three, including
zero-score ties by source ID. This isolates information quality from stopping.
Three adaptive conditions run the actual SmartRouter defaults at budget 3.
All sources have neutral trust and unit costs; there are no attacks or feedback.

The first attempted run (v1) aborted when an adaptive implementation of a fixed
control abstained for query 1146. The completed v2 runner implements fixed top-3
ranking explicitly. The original partial output is preserved and is not a result.
No production threshold was changed to make the control select three.

## Measured results

Recall columns are percentages. Source recall measures positively judged source
coverage. Document recall@10 uses shared-embedding document ranking within the
selected source pool; it is not answer accuracy or generated-response quality.

| Fixed-contact method | Mean contacts | Source recall | Document recall@10 |
|---|---:|---:|---:|
| Centroid mean | 3.00 | 17.09 | 16.09 |
| Centroid max | 3.00 | 19.90 | 18.94 |
| Description only | 3.00 | 12.19 | 10.89 |
| 50/50 description + centroid mean | 3.00 | 15.41 | 14.38 |
| 50/50 description + centroid max | 3.00 | 21.07 | 19.72 |

Fixed controls clip each centroid cosine to [0,1], matching smart relevance.
The earlier CosineRouter mean baseline averages unclipped values and reported
16.66%, not 17.09%. These are labelled separately; the slight discrepancy is a
scoring convention, not a new model or changed dataset. Max results agree here.

| Actual adaptive mode, budget 3 | Mean contacts | Source recall | Document recall@10 | No-source rate |
|---|---:|---:|---:|---:|
| Centroid mean | 0.92 | 5.92 | 5.91 | 7.67% |
| Description only | 0.81 | 4.22 | 4.12 | 19.00% |
| 50/50 description + centroid mean | 0.86 | 4.89 | 4.89 | 14.00% |

Zero budget violations occurred in all 7,200 completed method/query/partition
cases. Fixed contacts are intentionally bounded at three; the adaptive subset
contains 2,700 smart-router cases. No routing-pattern or security benefit was tested.

## Does the small gain hold up?

Description + max-centroid improves source recall by 1.17 percentage points
over max-centroid alone. A paired percentile bootstrap over 300 query clusters
(averaging each query's difference across three partitions, 10,000 resamples,
seed 2026) gives a 95% interval of -0.87 to +3.23 percentage points.

The interval includes zero. This is not convincing evidence of an improvement.
It is exploratory, conditional on these three partitions, and not corrected for
multiple comparisons. The same bootstrap for description + mean versus mean
gives -1.69 points, interval -4.03 to +0.71 points.

Do not promote the most favorable row as proof of a novel or better router.
Description-only routing is weaker here, and the adaptive variants still stop
too early. The initial hypothesis that richer metadata might help remains open.

## Why might this happen?

An example source description starts with cells, cell, expression, analysis,
associated, gene and protein. Another source starts with very similar terms.
Random shards of a single scientific collection share broad vocabulary; local
frequency-based summaries do not necessarily distinguish the evidence they hold.
This is an interpretation of the metadata, not an established causal result.

Better document-derived profiling, domain/source-based partitions and validated
stopping remain candidate next steps. Do not tune them repeatedly on these test
queries and call the eventual score an untouched evaluation.

## Overhead and transport boundaries

Descriptions plus vectors added a mean of 8,962 serialized JSON bytes per source,
about 26.12% over the source-ID/centroid-only JSON payload in this pilot. These
are profile-payload sizes, not measured MCP wire traffic or end-to-end latency.
The coordinator caches the information at registration; queries do not trigger
profile retrieval. The current MCP client still rebuilds its process per call.

Real MCP subprocess tests verify publication, caching, opt-out, deterministic
profiles and retrieval integration on synthetic fixtures. The 30-source quality
experiment uses the same metadata builder in-process and cached profiles; it
does not claim that 30 semantic-model MCP servers were benchmarked.

## Reproduce

First run the previous pilot if its frozen local artifacts are absent. Then:

```sh
env PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
  .venv/bin/python -m eval.run_metadata_pilot \
  --reference experiments/smart-pilot-scifact-30-v1 \
  --output experiments/metadata-pilot-scifact-30-v2
```

Existing output directories are never overwritten. Use a new path for another
run. Raw decisions, summary.csv, source_profiles_*.json and metadata.json are
saved locally in that directory and gitignored. Provenance includes original
input/artifact hashes, model snapshot, configurations and code fingerprints.

Code: [metadata builder](../backend/nodes/metadata.py),
[MCP server](../backend/nodes/mcp_server.py),
[comparison runner](../backend/eval/run_metadata_pilot.py).
The full Python suite passed 181 tests after this implementation.

No downloads, model training, external LLM calls or changes to default routing
settings were required. These results concern one deterministic keyword-based
metadata method, not every possible way of using MCP source information.
