# PSI dispatch stage and FeB4RAG routing results

## Verdict

**The dispatch stage now exists in which no node receives the query.**
`routing_mode="psi"` routes locally exactly as v2, then replaces the vector
dispatch with an OPRF / labeled-PSI exchange (`privacy/psi.py`): the client
blinds the ids of the nearest published cluster centroids, the node evaluates
them under its key and serves encrypted envelopes, and only the matched ones
open on the device. Verified over real MCP subprocesses with the text and
vector retrieval tools monkey-patched to fail — they are never called.

**Measured cost on 30 real MCP nodes, 16 queries, 6 contacts:**

| Mode | Query total | Per contact | Request bytes | Response bytes | Node sees |
|---|---:|---:|---:|---:|---|
| legacy | 2.43 s | 404 ms | 3.7 KB | 5.2 KB | query text |
| v2 | 2.44 s | 406 ms | 7.8 KB | 5.9 KB | query vector (invertible, docs/32) |
| **psi** (all envelopes) | **4.85 s** | **808 ms** | **1.0 KB** | **1.01 MB** | blinded points only |
| psi (fetch set 2) | 4.43 s | 738 ms | 1.0 KB | 0.80 MB | blinded points + a 2-id set |

Latency doubles because this client makes two spawn-per-call MCP round trips
per contact (evaluate, then envelopes); routing itself is <1 ms. Response
bytes are ~170x v2's: full labeled PSI delivers every envelope a node holds,
and each envelope carries its passages' routing-space embeddings as JSON
floats so the device can rerank without re-embedding. Those nodes hold 40
documents; the bytes are the whole corpus encrypted, per contact, per query.
Communication is linear in the node's table size — the known cost of DH-PSI
that sublinear schemes (APSI) exist to remove.

**FeB4RAG (docs/06's named routing benchmark), 13 of 16 engines, 785
requests, graded resource-selection qrels, 3 profile seeds:**

| | nDCG@1 | nDCG@3 | nDCG@5 | MRR (best engine) | Top-1 = best |
|---|---:|---:|---:|---:|---:|
| Local profile ranking (legacy = v2 = psi) | 0.734 | 0.734 | 0.759 | 0.578 | 0.399 |

| Mode | Captured gain @ contacts | Contacts | Zero-grade contacts | A2 precision |
|---|---:|---:|---:|---:|
| broadcast | 1.000 | 13.0 | 3.54 | 0.067 |
| oracle | 1.000 | 1.5 | 0.00 | 1.000 |
| legacy | 0.662 | 6.0 | 1.34 | 0.194 |
| v2 / psi | 0.662 | 6.0 | 1.34 | 0.231 |
| smart | 0.538 | 6.0 | 1.85 | 0.172 |

The routing layer captures 66% of the best achievable graded gain at six
contacts and ranks the single best engine first 40% of the time. v2 and psi
share the ranking and dispatch of legacy by construction, so on FeB4RAG the
privacy modes cost nothing in routing quality and the only differences are
what the node receives and what it costs to send.

## The PSI stage

`privacy/psi.py`, over the ed25519 prime-order group via libsodium
(PyNaCl 1.6; this build has no ristretto, so `from_uniform` hash-to-point
with cofactor clearing and unclamped scalar multiplication are used):

1. Device: for each probed cluster id, `P = H2C(id)`, `B = r·P`.
2. Node: `E = k·B` (`psi_evaluate` MCP tool; the OPRF key persists in
   `<node>.psi.key` so spawn-per-call processes agree).
3. Device: `F = r⁻¹·E = k·P`; envelope key `KDF(F, node_id)`.
4. Node: `psi_envelopes(fetch_set)` returns XChaCha20-Poly1305 envelopes of
   whole clusters keyed by random tokens; `None` = every envelope.
5. Device: opens what it holds keys for, reranks passages by exact cosine on
   the embeddings inside the envelopes, updates evidence trust, cites.

Cluster tables (`privacy/cluster_index.py`) follow docs/35: ~10 documents per
cluster, minimum size 5, `nprobe` 2. Centroids are published in the profile
and covered by the Ed25519 signature. `SourceProfile.cluster_centroids`,
`api/schemas.QueryRequest.psi_nprobe` / `psi_fetch_set`, and
`frontend/lib/api.ts` were extended; legacy remains the default.

What the node receives in psi mode: blinded group elements (uniform under
DDH), optionally a fetch set of cluster ids, and the credential identity the
transport carries. Not the query, not a vector, not which cluster matched.
The API process plays the device in this demo; a deployment moves
`AppState._psi_retrieve` and the routing call to the client and reduces the
coordinator to a relay (docs/03 target).

## Setup

FeB4RAG: `eval/run_feb4rag.py`. Engines with local BEIR corpora: nfcorpus,
fiqa, arguana, scidocs, scifact, trec-covid, nq, dbpedia-entity, hotpotqa,
msmarco, fever, climate-fever, webis-touche2020 (signal1m, robust04,
trec-news are not BEIR and are excluded; qrels and nDCG ideals are restricted
to the 13). Profiles: 1,500 documents reservoir-sampled from the first
200,000 lines of each corpus, `BAAI/bge-base-en-v1.5`, k=3 centroids, seeds
11/22/33; profiles never see the requests or result pools. Graded qrels
`BEIR-QRELS-RS.txt`; "best" = the engine(s) with the request's maximum
grade; `captured_gain` = gain of the contacted set ÷ gain of the best set of
the same size. 6-contact cap, `genuine_k=2`, `coarse_k=12`.

Transport: `eval/run_mcp_transport.py --modes legacy v2 psi`, 30 node files,
16 BEIR query texts, hashing routing embedder (the live demo's), 40 documents
per node → 3–4 clusters, spawn-per-call client. Bytes are JSON payloads.

## What this does not establish

- Retrieval quality of psi on FeB4RAG: FeB4RAG grades engines, not
  passages, so the graded-gain rows measure routing only. Passage-level
  recall under cluster bucketing is docs/35 (0.89 of dense@10).
- Cost at realistic node sizes: 40-document nodes make "every envelope" cheap
  in absolute terms and expensive relative to v2. At 2,000 documents per
  node the same protocol sends ~50x more; the fetch-set knob or a sublinear
  PSI is required there, and neither is measured.
- A security proof. Hiding rests on DDH in the ed25519 group and on the
  AEAD; timing, size and credential metadata are visible to the node and
  relay. The enumeration attack (a malicious client harvesting envelopes) is
  bounded only by the OPRF requiring the node's cooperation per id; it is
  not measured.
- The persistent-session transport that would remove most of the 808 ms.
- Anything about FeB4RAG's full 16 engines, or answer quality.

## Reproduce

```
python -m eval.run_feb4rag
python -m eval.run_mcp_transport --node-counts 30 --modes legacy v2 psi --n-queries 16
python -m eval.run_mcp_transport --node-counts 30 --modes psi --n-queries 16 --psi-fetch-set 2
```

Tests: `tests/test_psi.py`, `tests/test_psi_api.py`, `tests/test_feb4rag_metrics.py`.
Test counts are not privacy or retrieval results.
