# Architecture

The proposed system is an independent, training-free smart source router.
RAGRoute is a comparison baseline, not the engine beneath the smart router.
This document describes the current code; future extensions are labelled.

## Components and boundaries

| Component | Current role | Information visible |
|---|---|---|
| Next.js studio | Register demo sources, submit legacy queries, inspect results | Query, citations, source IDs and legacy audit |
| FastAPI coordinator | Own registry, routing, dispatch, trust feedback and optional generation | Raw query, source profiles, returned passages and complete routing trace |
| SmartRouter | Select an affordable, useful set from existing profiles | Query embedding, centroids, coordinator evidence and configuration |
| In-process source | Simulate a local index | Documents are held in the coordinator process |
| MCP source | Retrieve through a separate local subprocess | Local documents and raw questions sent to that source |
| Optional generator | Produce an answer from selected evidence | Raw question and returned passages; external provider when configured |
| Audit log | Record routing decisions for evaluation | Source identities, decisions and selection features |

The pure SmartRouter does not read raw documents. That is a module boundary,
not an isolated security zone: the coordinator hosting it sees raw questions
and retrieved passages. The implemented system does not hide queries from an
honest-but-curious coordinator or from contacted nodes.

## Profile registration

```text
Source documents
  -> heuristic redaction
  -> shared-space routing embeddings
  -> clustering and optional empirical profile noise
  -> centroid profile + version + policy labels
     + optional document-only description/topics/description embedding
  -> registry

Source documents
  -> local retrieval embeddings/index
  -> source-side retrieval tool
```

Routing queries and source centroids must share an embedding model and dimension.
A source may use a different local retrieval space; in that case the raw question
is embedded again at that source. The live demo uses hashing embeddings.
SentenceTransformerEmbedder exists but is not wired consistently across the
live API/MCP path yet.

The same routing model embeds the optional description. get_profile publishes
it with topics and method/model identifiers; the coordinator caches them during
registration. Smart relevance_mode can be centroid, description or combined.
This is application-defined MCP tool output, not automatic MCP knowledge about
source contents. A node can set publish_metadata=false; topics may disclose
collection details and are neither private nor authenticated by this extension.
See [implementation and results](15-mcp-metadata-pilot.md).

Redaction is a regex heuristic, not validated de-identification. Version checks
exist; Ed25519 profile signatures are verified when present and can be required
(docs/30) — they prove integrity and key binding, not truthfulness. Profile noise is not DP.
No exact centroid count or noise setting should be assumed across all node files.

For MCP nodes, get_profile and retrieve are tools on the same server
implementation. The client currently launches a fresh subprocess for each call;
it does not retain the same running process from registration to retrieval.

## Smart-mode query path

```text
User question
  -> FastAPI coordinator: embed question
  -> read already-published profiles and coordinator evidence
  -> YOUR SmartRouter
       exclude unauthorized / insufficiently trusted sources
       estimate relevance and profile overlap
       select the highest gain-per-cost affordable source
       repeat until gain, exposure budget or fan-out stops selection
  -> dispatch only selected sources
       in-process retrieval OR real MCP retrieve(raw question)
  -> collect returned passages
  -> coordinator embeds passages and updates profile-consistency trust
  -> optional configured generator, only when evidence exists
  -> answer / citations / routing_details
```

Selection does not issue retrieval calls to every source. Registered profiles
are scored locally. Retrieval is currently sequential and requests one passage
per selected source. The live path collects citations; global deduplication,
evidence reranking and a fixed local generation backend are not yet implemented.

A failed retrieval still consumes its reserved contact-exposure cost and is
recorded. Smart mode does not silently broadcast or retry additional sources.
No evidence means no generation call. No decoys or query perturbation are
added in smart mode.

## Operating modes

Smart mode now offers an opt-in `selection_policy="relative"` alongside the
existing overlap policy. It changes pre-dispatch selection/stopping only;
cached source profiles still arrive through registration/MCP, and retrieval,
budget accounting and coordinator feedback retain the existing path.
See [routing study protocol](16-routing-study-protocol.md). This is not a
new MCP protocol or a switch of the live demo to semantic embeddings.

| Mode | Selection | Status |
|---|---|---|
| smart | Independent constrained greedy algorithm in smart.py | Implemented, API opt-in |
| legacy | Cosine shortlist, weighted rerank, fixed genuine-k and decoys | Preserved control; API/dashboard default |
| Official RAGRoute | Upstream learned routing | Separate baseline; local adapter remains a stub |
| Cosine / broadcast / random / oracle | Local comparison controls | Existing adapters, not selectable through this API mode field |
| TASR / HE comparisons | External security/privacy methods | Separate experiment integration; not the smart-mode trust mechanism |

The dashboard diagram and source trust display still describe legacy operation.
Smart decisions are available through the API response and audit endpoint.
See [usage](13-smart-router-implementation.md) and
[baseline requirements](10-baseline-selection.md).

## Exposure and trust

Every selected source has a positive coordinator-configured cost, default one.
The sum must stay within the per-query budget, including every genuine contact.
This is recipient-exposure accounting, not a formal privacy budget or measured
routing-pattern secrecy.

Smart trust starts at 0.5, with an uncertainty penalty for few observations.
Returned passages are embedded by the coordinator to assess consistency with
the advertised profile; source-supplied trust and retrieval scores do not
determine that update. Matching bait passages can still fool this heuristic.

The policy-label check is a demo selection hook. Registration, authentication,
identity binding, signed profiles and multi-tenant authorization remain open.

## Evaluation observers

- A contacted node sees the raw question. Recipient minimization limits who
  receives it; it does not protect it from that recipient.
- A routing observer may see contacted identities and timing. Fewer contacts
  can still make the route easier to identify; A2 must test that separately.
- A malicious source can advertise a misleading profile or return bait text.
  A3 must measure selection rate and harm to honest-source retrieval.
- An external generator sees its prompt when configured. Local-only generation
  is a future boundary improvement, not current protection.

## Scale and instrumentation

The implemented selector scans registered profiles. The 1,000-profile unit
test is synthetic, in-memory validation, not a distributed scalability result.
Run separate real-MCP and logical-client benchmarks and report both clearly.

Smart routing logs config, candidate/selected IDs, exclusions, selection scores,
costs, stop reason, routing latency and retrieval errors. Every query also logs
per-stage wall time (embed, routing, retrieval, per contact) and application
JSON request/response bytes per contact (docs/33). Those are payload bytes,
not network bytes. Answer quality is not measured anywhere.
# Encrypted-scoring extension

The opt-in query-privacy milestone is documented in
[doc 34](34-encrypted-query-scoring.md). It routes locally, encrypts the query
vector, scores all rows at contacted nodes and ranks decrypted scores at the
trusted coordinator. It intentionally stops before document fetch/generation.
Existing paths below are unchanged and are not made private by this extension.

# Target end-to-end architecture (planned; not the current code)

Measurement (docs/31–35) fixed the shape of the next design. Nothing cheaper
than cryptography protects the query from a contacted node (docs/32), a
routing-space vector is invertible and 55x heavier than text (docs/33), and
semantic hashing cannot bucket questions with their passages while published
cluster ids can (docs/35). The target below composes off-the-shelf primitives
around the routing layer that has already been measured; it invents no
cryptography. Everything in this section is a specification to build and
measure against, not a description of implemented behaviour.

## Zones

| Zone | Trust | Holds |
|---|---|---|
| User device | Trusted; the only party that ever sees the query or the answer | embedder, router, cluster assigner, PSI receiver, envelope keys, reranker, evidence trust, local generator |
| Relay | Untrusted; may collude with nodes | signed profile registry, ciphertext forwarding, rate limiting. No keys. |
| Node ×N | Untrusted for the query (honest-but-curious); may be malicious about content (A3) | redacted chunks, shared-model embeddings, k-means clusters, OPRF key, labeled-PSI table, AEAD envelopes, authorization, disclosure audit |
| Key authority | Honest for issuance only; no path to data | credentials and envelope decryption keys per policy |

The current FastAPI coordinator becomes the relay. Routing, decryption,
reranking, trust and generation move to the device.

## Stages

| Stage | Where | Mechanism | Untrusted side sees | Residual leak (metric) |
|---|---|---|---|---|
| Embed | device | shared model, local | nothing | — |
| Route | device | v2 `select_dispatch` over signed public profiles: genuine_k + topic-stable decoys within budget | nothing | — |
| Bucket | device | nearest `nprobe` of the node's published cluster centroids (docs/35: k≈docs/10, nprobe 2, min cluster size 5) | nothing | centroid_near_doc_fraction, published per node |
| Dispatch | device → relay → node | blind cluster ids with secret r (OPRF / DH-PSI); identical payload to genuine and decoy nodes | blinded group elements | none under DDH |
| Match | node | OPRF with node key k; labeled PSI over the cluster table | which credential contacted it, item count | none about the query |
| Deliver | node → device | AEAD envelopes for matched clusters only | that envelopes were served | passages delivered per contact (~36 at the recommended point, ~3.6x a top-10 fetch) |
| Rerank | device | exact cosine on decrypted passages; decoy results dropped | nothing | — |
| Trust | device | evidence trust on decrypted passages (the docs/32 gate defect still applies) | nothing | A3 attacker rate, honest recall |
| Generate | device | local LLM | nothing | — |
| Pattern | relay | — | which nodes were contacted, sizes, timing | A2 precision; decoys are the control |

### Optional tier: encrypted scoring inside the probed clusters

The Paillier scoring in docs/34 scores every row a node holds and returns
an encrypted score per row (≤128 rows, ~264 KB request at 256-d, ~1 s per
contact plus ~18 s per-query keygen in the smoke run). Over a whole corpus
that is too slow and too large; over the ~36 passages of a probed cluster it
is the mechanism that would bring delivery down from ~36 passages to the
selected few without the node learning which. In the target design it sits
between Match and Deliver as an opt-in tier, with the coordinator role it
assumes today moved to the device. Its cost is a row in the same table as
plaintext and PSI dispatch; it is not a default.

## What each party learns

| Party | Learns | Does not learn |
|---|---|---|
| User | authorized matched passages, answer | non-matching documents, node OPRF keys |
| Relay | contacted node ids, payload sizes, timing, credential id | query, cluster ids, matches, passages, answer |
| Node | a credential contacted it; how many blinded items; that some envelopes were served | the query, the cluster ids, genuine vs decoy, what was done with the envelopes |
| Relay + nodes colluding | contact pattern | still not the query |

## Assumptions

1. The user's device is uncompromised.
2. Relay and nodes are honest-but-curious about the query; nodes may lie about content.
3. Non-collusion is not required for query confidentiality.
4. The key authority issues keys honestly and has no path to traffic or data.
5. DDH on ristretto255 for OPRF/PSI; AEAD for envelopes; Ed25519 for profiles; TLS on every hop.
6. Shared routing model and cluster parameters are public and identical everywhere; embeddings never leave the device.
7. Published centroids stand for ≥5 documents each (docs/35 minimum cluster size).
8. Node-side PII redaction is a preprocessing assumption whose quality is not evaluated here.

## What the target does not provide

- Metadata privacy: that a query happened, when, how large, from which credential.
- A security proof beyond reduction to the primitives' standard assumptions.
- Protection against a node that forges centroids or profiles to attract queries (A3); that remains the trust layer's problem and its measured defect stands.
- Any answer-quality result until measured.

## Claim shape

End-to-end confidentiality of query and evidence content under DDH and an
uncompromised client, with routing-metadata leakage bounded by decoys and
node-side passage disclosure measured rather than eliminated. Not "zero
leakage", not "provably private", not a new primitive.
