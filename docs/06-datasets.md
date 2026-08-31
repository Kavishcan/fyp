# Datasets

Three datasets. Deliberately few.

## Keep

### FeB4RAG — primary routing benchmark

790 queries, 16 source clients, precomputed top-100 result pools and qrels.
Apache-2.0 (underlying BEIR datasets carry separate terms).

The precomputed pools support routing and merging evaluation, but they are not a
replacement for the source corpora when constructing document-derived centroids.
Official FeB4RAG instructions require the underlying BEIR collections. Use the
published RAGRoute/FeB4RAG artifacts where available and document exactly which
parts are reproduced versus reused.

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

### MedQA-USMLE — healthcare case study

Add a subset of roughly 150 questions. **Not** a primary benchmark.

A project claiming healthcare that evaluates only on news and StackExchange-style
data will be challenged. Mu and Li used 100 MedQA questions as a high-stakes case
study and it carried the domain claim adequately. MedQA is small and easy to
obtain, unlike the MedRAG corpora cut below.

Reuse their node partition directly: 15 non-medical nodes, 3 honest medical nodes
built from disjoint training shards, plus malicious nodes. Queries come from the
test split, using the question stem only.

Role: demonstrates that routing behaviour and leakage persist under a clinical
query distribution. Not used for tuning.

Dataset: https://huggingface.co/datasets/bigbio/med_qa

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
| 8-16 | FeB4RAG clients | Real MCP demonstration and in-process research runs |
| 49 | MultiHop-RAG source metadata | Logical clients; in-process by default |
| 100 / 300 / 1000 | Synthetic sharding of the above | In-process, mocked |

Synthetic shards from one corpus are more homogeneous than real institutions.
State the construction plainly rather than implying 1000 real silos were
deployed.
