# Data

Preparation scripts, partition definitions and local node files support routing
experiments. Raw corpora and many generated outputs are gitignored; inspect the
local inventory before downloading anything. Respect the user's 500 MB download
limit and record licenses/version information.

- FeB4RAG/BEIR: document-backed sources and relevance-labelled routing queries.
  The inspected upstream RAGRoute configuration uses 13 named sources; that is
  not a universal count for the benchmark or this application's active nodes.
- Same-domain shards: routing difficulty and source-overlap control.
- MultiHop-RAG: complementary evidence across source partitions; verify any
  claimed 49-client setup from its manifest.
- Synthetic cases: budget/access/attack tests with explicit labels and seeds.
- MedQA: intended healthcare case study; questions alone are not source corpora.

TREC result pools contain rankings/scores, not the full source documents.
Separate score replay from live document retrieval and profile construction.

See [dataset strategy](../docs/06-datasets.md) and
[experiment controls](../docs/05-experiments.md). Dataset files alone do not
establish a completed or leakage-free evaluation.
