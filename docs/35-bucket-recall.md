# Semantic hashing for PSI retrieval: bucket recall (E1/E2)

## Verdict

**SimHash fails. Cluster ids work, at a disclosure cost that is now a number.**

Under labeled PSI a node can only match exact ids, so retrieval becomes
"is the relevant passage in the query's bucket?" Measured on the same bge-base
embeddings as docs/31–33, before any cryptography:

- **SimHash (data-independent LSH) is unusable for asymmetric query→passage
  matching.** At 32 bits, bucket recall is 0.001–0.19 regardless of probing;
  at 64 bits it is 0.000. The only configuration that recalls anything (16
  bits, radius 2, 8 tables: 0.946) delivers **901 of 2,000 documents** per
  query — 45% of the node's corpus — and at that disclosure exact cosine
  would have scored 0.997. At every operating point hashing is strictly worse
  than dense retrieval at equal disclosure. Centering the embeddings does not
  rescue it (0.566 recall at 47 envelopes).

- **Cluster ids (published k-means centroids, IVF-style) reach ~0.89 of
  dense recall while delivering ~36 passages per contacted node** — about
  3.6x a dense top-10 fetch — at k=200, nprobe=2, minimum cluster size 5.
  Recall converges to dense as nprobe grows, with disclosure growing
  linearly.

- **The price of cluster ids is that the node publishes its centroids**, and
  at high k those become single documents' embeddings (28% at k=500, 60% at
  k=1000). A minimum cluster size of 5 removes every singleton and holds the
  near-document fraction at ~2% with no recall cost. Reducing passage
  disclosure by raising k without that rule moves the leak into the profile.

Why SimHash fails here: relevant query–passage pairs have mean cosine 0.701
against 0.511 for random pairs — an angle of ~45° versus ~59°. A random
hyperplane separates a relevant pair with probability ~0.25, so a 16-bit code
agrees on all bits with probability ~0.01. Apple's NeuralHash matches
near-identical images (angle near 0); this is a different regime.

## Setup

`eval/run_bucket_recall.py`. Five BEIR corpora, each one node pool of 2,000
documents (qrel-required plus filler; nfcorpus 2,368) and 100 judged queries;
data seed 11; `BAAI/bge-base-en-v1.5` normalised via the embedding cache.
Hash/cluster randomness seeds 1/2/3; means over 5 corpora × 3 seeds.

- `bucket_recall`: fraction of queries with ≥1 relevant document in a probed
  bucket (any table / any probed cluster).
- `dense_recall@10`: exact cosine, same pool — the ceiling (0.894 mean).
- `envelopes`: mean distinct documents in the probed buckets — what the node
  would deliver, i.e. node-side disclosure per query.
- `dense_recall@envelopes`: dense recall at k = envelopes, so the two schemes
  can be compared at equal disclosure.

SimHash: bits {16, 32, 64} × Hamming radius {0, 1, 2} × tables {1, 4, 8}.
Cluster: spherical k-means with k {50, 100, 200, 500, 1000, 2000}, nprobe
{1, 2, 4, 8, 16}, minimum cluster size {1, 5, 10}. Leak metrics:
`singleton_fraction` (clusters of one document) and
`centroid_near_doc_fraction` (published centroids within cosine 0.95 of some
document).

## SimHash (selected rows; full grid in the CSV)

| bits | radius | tables | probes/query | Bucket recall | Envelopes | Dense @ same envelopes |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 0 | 8 | 8 | 0.273 | 36.8 | 0.941 |
| 16 | 1 | 8 | 136 | 0.709 | 277.4 | 0.973 |
| 16 | 2 | 4 | 548 | 0.816 | 532.3 | 0.989 |
| 16 | 2 | 8 | 1,096 | 0.946 | **900.9** | 0.997 |
| 32 | 2 | 8 | 4,232 | 0.191 | 7.5 | 0.868 |
| 64 | 2 | 8 | 16,648 | 0.001 | 0.03 | — |

## Cluster ids

| k | nprobe | Bucket recall | ÷ dense@10 | Envelopes | p95 | Dense @ same envelopes |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 1 | 0.709 | 0.79 | 54.3 | 94.5 | 0.947 |
| 50 | 2 | 0.825 | 0.92 | 108.0 | 166.9 | 0.959 |
| 100 | 1 | 0.685 | 0.77 | 28.9 | 52.6 | 0.935 |
| 100 | 2 | **0.813** | **0.91** | **56.9** | 91.8 | 0.948 |
| 100 | 4 | 0.888 | 0.99 | 113.0 | 161.2 | 0.959 |
| 200 | 1 | 0.670 | 0.75 | 15.9 | 33.6 | 0.916 |
| 200 | 2 | 0.794 | 0.89 | 31.8 | 54.9 | 0.937 |
| 200 | 4 | 0.868 | 0.97 | 63.4 | 97.1 | 0.948 |
| 200 | 8 | 0.915 | 1.02 | 125.9 | 174.7 | 0.962 |

Per-corpus at k=100, nprobe=2: arguana 0.923, scidocs 0.873, fiqa 0.833,
nfcorpus 0.730, scifact 0.707 — the two biomedical corpora with the lowest
dense ceilings are also the hardest to bucket.

Even cluster ids lose to dense retrieval at equal disclosure (0.813 vs
0.948 at ~57 documents): the gap is the cost of the node not being able to
rank. A client-side rerank over the delivered envelopes recovers ranking but
not the documents outside the probed clusters.

## Finer clusters, and the centroid leak

Raising k lowers envelopes but publishes centroids that increasingly *are*
single documents' embeddings — and docs/32 showed embeddings invert. Both
axes, nprobe=2, means over 5 corpora × 3 seeds:

| k | Envelopes | Recall ÷ dense | Singleton clusters | Centroids within cos 0.95 of one doc |
|---:|---:|---:|---:|---:|
| 100 | 57 | 0.91 | 2% | 3.5% |
| 200 | 32 | 0.89 | 5% | 8.1% |
| 500 | 14 | 0.87 | 19% | **28.4%** |
| 1000 | 7 | 0.85 | 45% | **60.3%** |
| 2000 | 1 | 0.80 | 96% | 99% |

At k=500 a quarter of the published centroids are a document embedding in
the clear; at k=1000 more than half. Reducing passage disclosure by raising
k moves the leak into the profile. It is not a free knob.

### Minimum cluster size

`enforce_min_cluster_size(m)` merges any cluster below m documents into its
nearest cluster, so no published centroid represents fewer than m documents
— k-anonymity on the centroid. nprobe=2:

| k | m | Centroids published | Recall ÷ dense | Envelopes | Singletons | Centroid ≈ doc |
|---:|---:|---:|---:|---:|---:|---:|
| 200 | 1 | 200 | 0.887 | 31.8 | 5.2% | 8.1% |
| **200** | **5** | **151** | **0.889** | **35.8** | **0** | **2.1%** |
| 200 | 10 | 99 | 0.891 | 51.7 | 0 | 1.5% |
| 500 | 1 | 500 | 0.872 | 13.6 | 19.0% | 28.4% |
| 500 | 5 | 205 | 0.886 | 26.4 | 0 | 4.8% |
| 1000 | 5 | 198 | 0.878 | 31.7 | 0 | 6.4% |

m=5 removes every singleton, cuts the near-document fraction ~4x, and costs
~4 envelopes and no recall at k=200. m=10 costs 20 envelopes for little
further gain. Requesting k=500 or 1000 with m=5 collapses to ~200 effective
clusters anyway — the minimum size, not k, ends up setting the resolution.

The remaining 2.1% at k=200/m=5 are clusters of ≥5 near-duplicate documents
whose centroid is close to all of them; publishing it reveals the shared
content of that group, not one record.

### Recommended operating point

**k = 200, nprobe = 2, min cluster size = 5** (for ~2,000-document nodes;
the transferable rule is ~10 documents per cluster, probe 2, never publish a
centroid for fewer than 5). Recall 0.795 = 0.89 of dense@10; ~36 passages
delivered per contacted node; no singleton centroids; 2.1% near-document
centroids; 2 PSI items per query.

### How to state disclosure

"Envelopes per relevant document" is not a usable ratio: relevant documents
per query range from ~1 (arguana, scifact) to ~38 (nfcorpus), so the same 32
envelopes read as 32x on one corpus and 0.8x on another. The stable comparison
is against what exact retrieval would deliver: dense top-10 returns 10
passages; the recommended point returns ~36 — **3.6x the passages of a
top-10 fetch for 0.89 of its recall**, with the node learning nothing about
the query.

## Implication for the end-to-end design

- Replace "semantic hash" with "published cluster id" in the PSI stage. The
  client computes nearest centroids locally (the centroids are public and
  signed with the profile), and the PSI item is the cluster id. Nothing else
  in the design changes.
- The node publishes ~150–200 centroids, each standing for ≥5 documents. That
  is a topic map at higher resolution than the routing profile; its leak is
  measured (`centroid_near_doc_fraction`) and must be reported.
- Node-side passage disclosure is ~3–4x a top-10 fetch. Decoy contacts
  multiply it. Report it next to A2.
- Getting disclosure to ~1 without giving up recall needs scoring inside the
  probed clusters that the node cannot see — encrypted scoring over ~36
  vectors per node rather than 2,000, which this result makes cheap enough to
  consider. Not built.

## What this does not establish

- Any PSI cost, latency or bytes — no cryptography was run.
- Adversarial behaviour: a node can publish centroids that attract queries
  (an A3 variant); collisions engineered by a malicious client.
- Learned hashing or product quantisation; SimHash is the floor, not the
  ceiling, for data-independent schemes.
- Behaviour at node sizes other than ~2,000 documents.
- What a centroid for ≥5 documents reveals beyond the cos>0.95 proxy used
  here; inversion of centroids was not attempted.

## Reproduce

```
python -m eval.run_bucket_recall --scheme simhash
python -m eval.run_bucket_recall --scheme cluster
python -m eval.run_bucket_recall --scheme cluster --clusters 100 200 500 1000 \
  --nprobe 1 2 4 8 --min-cluster-size 1 5 10
```

Tests: `tests/test_bucket_recall.py`. Test counts are not retrieval or
privacy results.
