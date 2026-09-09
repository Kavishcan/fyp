# Architecture

The proposed system is an independent, training-free smart source router.
RAGRoute is a comparison baseline, not the engine beneath the smart router.
This document describes the current code; future extensions are labelled.

## Experimental evidence-budget path

The new branch adds an independent opt-in `/query/evidence` path:

```text
query + cached authorized source profiles
  -> evidence-budget allocator chooses (source, next local rank)
  -> reserve one candidate slot, and a client slot if new
  -> MCP / in-process retrieve(top_n=1, offset=rank)
  -> coordinator embeds the returned text
  -> update residual profile coverage and repeat within C/B caps
  -> deduplicate -> common cosine top-K merger -> optional generator
```

There are no free query-time profile requests, uncharged candidate previews,
trust updates or fallback broadcasts. This is a heuristic experiment, not a
replacement for the paths below. Exact rule and limits: [protocol](20-evidence-budget-protocol.md).
The [first results](21-evidence-budget-results.md) do not support superiority.

An additional `method=feedback` variant uses the first paid passage from each
contacted node to refine the routing query for the next client, anchored to the
original query. It keeps equal quotas and original-query local retrieval/final
ranking. See [protocol](24-feedback-routing-protocol.md). This is a tested
pseudo-relevance-feedback hypothesis, not a missing-fact detector or proof of
novelty. It does not replace the old joint or fixed control methods.

The opt-in rich-profile path uses `method=equal`, `profile_strategy=hybrid` and
development-selected `lexical_weight=0.25`:

```text
source documents -> semantic centroids + lexical presence sketch -> registry
query -> semantic score + inverse-source-frequency lexical match
      -> fused top-C source selection -> equal passage quotas within B
      -> paid local retrieval -> original-query cosine top-K -> optional generator
```

Sketches are published through simulator/MCP profiles when metadata is enabled.
Invalid/missing sketches at any eligible source trigger semantic fallback for
the query. No extra query-time discovery calls are hidden from the budget.
See [protocol](26-rich-profile-protocol.md) and [results](27-rich-profile-results.md).
This branch's measured gain concerns source selection, not adaptive quotas or
trust defense. Defaults remain unchanged; live hashing and offline MiniLM
embedding paths still differ.

The evaluation-only `baselines/profile_fusion.py` adds tuned weighted RRF and
min-max controls while reusing the existing charged equal allocator. It does not
add API modes. `eval.prepare_answer_study` builds source-based chunk retrieval
and separates generation prompts from references; `eval.answer_quality` accepts
actual externally generated predictions for offline EM/F1 scoring. See the
[audit/readiness report](29-strong-controls-results.md): generation remains pending.

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
exist, but signature verification is a placeholder. Profile noise is not DP.
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

An experimental `relevance_mode="centered"` subtracts a source-balanced
background from normalized queries and centroids before scoring. Only authorized,
valid, trust-eligible profiles enter that background. Raw profiles remain in the
registry and are still used for consistency feedback. This uses no new MCP fields
and sends no extra query probes. It is not a privacy or hijacking defence.
Development selection chose strength zero (no transform); do not present
centering as an improvement. See [the frozen study protocol](18-centered-routing-protocol.md).

For a coverage-oriented control, use max aggregation, relative selection with
relative_score_floor=0 and minimum_gain=0. This fills the affordable positive-score
budget instead of applying the unvalidated 0.8 early-stop threshold. It is not
an evidence-sufficiency detector and may increase contacts. All existing defaults
remain unchanged for compatibility.

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
costs, stop reason, routing latency and retrieval errors. Network byte counts,
full stage timings and answer-quality metrics are not automatically measured
just because logging fields or MCP transport exist.
