# Datasets

Three datasets. Deliberately few.

## Keep

### FeB4RAG — primary routing benchmark

790 queries, 16 source clients, precomputed top-100 result pools and qrels.
Apache-2.0 (underlying BEIR datasets carry separate terms).

The precomputed pools are why this is primary — they save months of index
building. Use for the main routing and communication experiments.

Repo: https://github.com/ielab/FeB4RAG

**Caveat:** the 16 clients are cross-domain, making routing artificially easy.
Add a same-domain hard split (see [experiments](05-experiments.md)).

### MultiHop-RAG — secondary, multi-node evidence

2,556 questions, 609 articles, 49 source-based clients. ODC-BY 1.0 with
attribution.

Genuine multi-source evidence: some questions need passages from more than one
node. Tests whether the router selects several complementary nodes rather than
one.

Dataset: https://huggingface.co/datasets/yixuantt/MultiHopRAG

### Synthetic privacy and attack set — primary privacy test

200 fictional privacy cases plus 60 attack cases. Project-generated, no real PII.

Assign across 6 to 8 simulated nodes with different access rules. Validate every
required field, run an exact-text duplicate check, and freeze the random seed
before experiments.

Repo: https://github.com/Kavishcan/fedrag-dataset

## Cut

| Dataset | Reason |
|---|---|
| MIRAGE and its 5 subsets | Multiple-choice medical exam QA does not test routing. Large licensing and storage cost for a metric that is not the contribution. |
| MedRAG corpora | Terabyte-scale download, mixed licences, months of preprocessing. The single biggest scope risk in the original plan. |
| BEIR (full) | Already marked optional. Cut, except for the same-domain hard split. |
| MS MARCO | Not needed for the prototype. |
| Natural Questions | Background benchmark only. |
| FEVER | Useful for groundedness, not for routing. |
| KILT | Not needed. |

These papers stay in the literature review as background. Only the plan to
download them is cut.

## Node partitioning

| Scale | Source | Transport |
|---|---|---|
| 16 | FeB4RAG native clients | Real MCP servers |
| 49 | MultiHop-RAG source metadata | Real MCP servers |
| 100 / 300 / 1000 | Synthetic sharding of the above | In-process, mocked |

Synthetic shards from one corpus are more homogeneous than real institutions.
State the construction plainly rather than implying 1000 real silos were
deployed.
