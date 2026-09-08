# Dataset strategy

The independent smart router needs source documents for profiles, questions for
routing, and relevance/evidence labels for evaluation. These are different
assets; a list of search scores is not a document corpus.

Inspect existing local files before downloading. The user disallowed downloads
larger than 500 MB. Verify dataset licenses, release versions, counts and source
mappings before freezing an experiment; totals below are experiment plans,
not an inventory certification.

## Roles

| Asset | What becomes a source/client | What it tests | Required files |
|---|---|---|---|
| FeB4RAG / underlying BEIR collections | One collection per source in the chosen baseline configuration | Cross-domain source routing and comparison with RAGRoute | Documents, queries, source map, relevance labels and compatible profiles/artifacts |
| Same-domain BEIR partition | Disjoint documented shards of one corpus | Harder routing where topics overlap | Partition manifest and remapped document/source relevance |
| MultiHop-RAG | Source-based partitions from verified article metadata | Whether selection covers complementary evidence across sources | Articles, question/evidence mappings and source manifest |
| Synthetic privacy/attack set | Explicit artificial source policies and malicious/benign profiles | Budget, access, manipulation, cold-start and attacker controls | Generation seed, labels, attack settings and expected outcomes |
| MedQA case-study subset | Document-backed sources defined separately from held-out questions | Healthcare query behaviour | Explicit knowledge corpus, query split and evidence labels if available |

Medical multiple-choice QA alone does not define distributed knowledge sources
or source-relevance ground truth. Do not use test answers to construct profiles
or expose the answer key as routing features.

## Initial baseline condition

The inspected upstream RAGRoute FeB4RAG configuration lists 13 sources:
arguana, climate-fever, dbpedia-entity, fever, fiqa, hotpotqa, msmarco, nq,
nfcorpus, scidocs, scifact, trec-covid and webis-touche2020.

Use that exact configuration and compatible artifacts for an initial faithful
comparison if available. Do not equate it with every source in the original
FeB4RAG release or every node currently loaded in this demo.

FeB4RAG top-100 TREC result pools support replay/evaluation. They do not contain
the full document text needed to construct new centroids or retrieve fresh
passages. Obtain compatible source corpora or verified precomputed profiles;
label a score-replay experiment separately from live retrieval.

## Planned larger conditions

A 49-source MultiHop-RAG condition must be verified from the actual partition
manifest, not assumed from a dataset name. Likewise 30+ sources are a target
condition until their document membership and relevance mappings are frozen.

For 100/300/1,000 logical clients, document the splitting/replication procedure.
Replicated profiles are a stress test, not additional independent institutions.
The existing 1,000-profile synthetic unit test is not a dataset benchmark.

## Freeze before comparing

Record dataset release/license, corpus/query/document IDs, source membership,
train/validation/test separation, deduplication, routing/local embedding models,
preprocessing, centroids/noise settings, source-policy labels, costs and seeds.
No test qrels or future trust observations may enter routing or tuning.

The live hashing demo is for integration checks. Semantic-model quality results
require consistent query/profile embeddings and documented model provenance.

## Reference locations

- [FeB4RAG](https://github.com/ielab/FeB4RAG)
- [MultiHop-RAG](https://huggingface.co/datasets/yixuantt/MultiHopRAG)
- [MedQA](https://huggingface.co/datasets/bigbio/med_qa)
- [Project dataset repository](https://github.com/Kavishcan/fedrag-dataset)

Check these upstream sources directly when preparing data; this architecture
update did not download datasets or verify their current licensing terms.
