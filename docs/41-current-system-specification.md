# Current system specification

The single authoritative statement of what is implemented, what is measured,
and what is claimed. Where an older document disagrees with this one, this one
is current; documents 04, 07–08 and 13–17 are historical design and pilot
notes kept for provenance (each carries a status line).

## Research question

> To what extent do source-routing decisions in Federated RAG reveal the
> query — its content to contacted sources, and its topic to an observer of
> the contact pattern — and can privacy-aware routing reduce both leaks while
> preserving source-selection accuracy, answer quality and efficiency?

Two leaks, two mechanisms, one budget:

| Leak | Adversary | Mechanism | Status |
|---|---|---|---|
| Query content | a contacted source | OPRF / labeled-PSI over cluster ids (`privacy/psi.py`); in blind unlock no node learns even whether it was relevant | Implemented, measured: 0 of 3 sensitive values exposed (docs/37); PMC-Patients: question to 0 of 8 hospitals (docs/46–47) |
| Contact pattern | an observer of which sources are contacted | **blind unlock** (`routing_mode="blind"`, `privacy/blind_unlock.py`): every node receives the same number of real-or-dummy blinded points (recommended, docs/47); fixed anonymity cells (`decoy_policy="cells"`, docs/40) are an older, lower-bandwidth option | Implemented, measured: blind — topic inference at the majority floor on k-means, Dirichlet and random PMC-Patients partitions and over five-question sessions (docs/50); cells leak above floor on Dirichlet (0.294 vs 0.210) |

Secondary: one malicious-source experiment (forged profile), where the
router has no defence (selected 1.000) and the cross-node evidence rerank
keeps the planted passage out of the prompt (cited 1.000 → 0.067, docs/40).

## Threat model

| Party | Sees | Trusted? |
|---|---|---|
| **Coordinator** (the API process) | raw query, embeddings, all returned passages, routing trace | **Trusted** — it plays the user's device in the studio. The deployment path is the standalone `client.Device` (docs/52): the same protocol code on the user's machine, no server in the path. |
| **Contacted source** (MCP node) | legacy/smart: query text; v2: an invertible vector; psi: blinded group elements + a fetch set; **blind: exactly P uniform group elements per question, real or dummy, from every client alike** | Honest-but-curious about the query; may lie about content (A3) |
| **Pattern observer** (network, relay, colluding sources) | which sources were contacted, sizes, timing | Untrusted |
| **Malicious client** | everything a credentialed client sees | Gated: the node evaluates the OPRF only for an allow-listed credential within its daily evaluation budget (docs/43), persisted on disk since docs/49 (before, a spawn-per-call node reset it on every call); a gated node refuses unauthenticated text/vector retrieval and the experimental scorer (docs/49) |

Protected assets: some identifiers in node documents (best-effort
de-identification before indexing, docs/44); query text and embedding from
sources (PSI/blind); query topic and genuine-source identity from a contact
observer (blind). Blind sends the same-size request to every source;
fixed-rate cover can additionally hide whether a question was asked on a
given tick (docs/52). Not protected: the active credential, device-local
side channels, uncaught identifiers or re-identifying combinations, source
truthfulness, or generation when a hosted provider is configured. The
studio API coordinator sees the question; standalone `client.Device` does not
put a server on the query path.

Claims are **routing-stage privacy** against contacted sources and a pattern
observer under the stated threat model (docs/51), plus measured partial
node-side de-identification. Not end-to-end patient privacy or differential
privacy; network jitter and clinical re-identification were not evaluated.

## Pipeline as implemented — recommended (`routing_mode="blind"`, `rerank="hybrid"`)

```text
offline, once per key epoch (same bytes for every client of a role)
  every node → its encrypted cluster table (OPRF-derived tags, padded float16 payloads;
               restricted collections only to permitted roles) → device cache
question
  → shared routing embedder (bge-base in the demo and every experiment)
  → score every published cluster of every node locally → global top-P (default 4 API, 8 studio)
  → EVERY node, in sorted order: exactly P blinded points, real r·H(c) or dummy r·G
  → node OPRF-evaluates per permitted collection, charges P to the persisted budget
  → device unblinds real replies → tag lookup in the cache → open envelopes
  → hybrid rank (cosine + pool BM25, router/hybrid_rerank.py) → top-k evidence
  → local generation → answer; per-stage latency and bytes logged
```

## Pipeline as implemented — per-query PSI (`routing_mode="psi"`, `decoy_policy="cells"`)

```text
question
  → shared routing embedder (ROUTING_EMBEDDER: hashing by default, bge-base for the demo and every experiment)
  → local ranking over signed profiles (router/v2.select_dispatch)
  → dispatch set: cells of the top source(s) [or genuine_k + topic-stable decoys]
       every contact charged to one exposure budget, no exemption
  → per contacted node: nearest nprobe public cluster centroids → blind ids
       → node OPRF-evaluates, serves AEAD envelopes → only matched open
       (nodes/mcp_server psi_evaluate / psi_envelopes; PersistentMCPNodeHandle)
  → device-side rerank inside each node's envelopes, then across nodes
       (AppState._rerank_evidence, evidence_top_k)
  → evidence trust update (every contact)
  → local generation (generation/ollama_generator, localhost only) → answer
  → per-stage latency and per-contact bytes logged for every query
```

The API default remains legacy; the studio defaults to blind unlock (P = 8) with hybrid ranking, every mode selectable.

## Labels

| Implemented and measured | Experimental | Planned / not built |
|---|---|---|
| blind unlock (offline tables, fixed-count real/dummy probes, tag lookup, key epochs), hybrid device rerank, local routing, budget, signing, topic-stable decoys, anonymity cells, PSI dispatch, cluster index, credential gate with persisted per-client evaluation budget, role-based access to node collections (per-collection OPRF keys), node-side de-identification at load (rules + registry + optional NER), persistent MCP, cross-node rerank, local generation, per-query instrumentation | Paillier encrypted scoring (`POST /query/private-score`, docs/34): correct, ~18 s/query keygen, ≤128 rows — the in-cluster tier if ever needed | blind-unlock future work (docs/47: chunked/compressed tables, grouped blind unlock or PIR for scale, two-level unlock, key lifecycle with threshold/hardware keys, credential expiry/revocation, verifiable OPRF); relay separated from the device code; key authority (issuance/revocation) and anonymous credentials; TLS (deployment); sublinear PSI (APSI); in-cluster HE scoring; RAGRoute reproduction; better trust signal |

## Traceability

| RQ | Module | Dataset | Metric | Result |
|---|---|---|---|---|
| Leak exists | `attacks/a2_topic_inference`, `eval/run_leakage` | FeB4RAG (13 engines, 640 req.) | topic acc / F1 / top-3 vs chance and metadata floor | 0.496 (chance 0.077) — docs/39 |
| Same-domain hard case | `eval/run_healthcare` | pooled biomedical BEIR, 8 k-means clients | same | 0.604 (majority floor 0.31) — docs/40 |
| Pattern defence | `router/anonymity.build_cells` | both | topic + source attack, gain | 0.201 / 0.231; 0.272 / 0.250 — docs/40 |
| Content defence | `privacy/psi`, `eval/run_privacy_cases` | 200 synthetic privacy cases | sensitive values exposed | 0 of 3 (others 3 of 3) — docs/37 |
| Routing utility | `eval/run_feb4rag` | FeB4RAG graded qrels | nDCG@k, MRR, top-1, captured gain | nDCG@1 0.734, MRR 0.578 — docs/36 |
| Answer quality | `eval/run_answer_quality` | 150 MIRAGE questions, Qwen3.5-9B local | MCQ accuracy | closed 0.547 / psi 0.580 / broadcast 0.627 — docs/38 |
| Efficiency | `eval/run_scaling`, `eval/run_mcp_transport` | 30–300 virtual; 30 real MCP processes | ms, bytes, contacts | psi 61 ms/query persistent; 102 KB (v2) vs 1 KB (psi) request — docs/33, 36–37 |
| Malicious source | `eval/run_privacy_cases` attack section, `eval/run_v2_a3` | 60 attack cases; 24 shards | selected, cited, honest recall | selected 1.000; cited 0.067 with rerank — docs/32, 40 |
| Enumeration | `eval/run_psi_enumeration` | synthetic, real gate | queries / days to open a table | ⌈C/nprobe⌉ ungated; 8–10 days gated at 20/day — docs/37, 43 (holds on real MCP nodes only since docs/49) |
| Both leaks at once | `privacy/blind_unlock`, `eval/run_hyfedrag_compare` | PMC-Patients, 986 q, 8 hospitals | MRR, question to hospitals, topic acc, records, ms, bytes | question to 0, topic at floor, MRR 0.421 (P=8) vs HyFedRAG-style 0.444, ~5 KB/q + 83 MB once — docs/47 |
| Device ranking | `router/hybrid_rerank`, same harness | same | MRR at matched ranking | blind P=8 0.509 / P=24 0.535 vs HyFedRAG-style 0.543 (all hybrid) — docs/48 |
| Split robustness and significance | `eval/run_hyfedrag_compare`, `eval/bootstrap_compare` | 986 PMC-Patients queries, 8 simulated hospitals, three partitions | matched hybrid MRR, paired bootstrap | blind P=8 retains 81–94% of local HyFedRAG-style MRR; P=24 retains 97–98%; only k-means P=24 is statistically indistinguishable — docs/50 |
| Blind-mode answers | `eval/run_answer_quality` | 150 MIRAGE questions, local Qwen3.5-9B | MCQ accuracy, paired bootstrap | blind dense 0.613 vs closed-book 0.547 (p=0.035); hybrid 0.573, not a universal gain — docs/50 |
| Implementation security | `tests/test_audit_fixes` | real MCP nodes | attack replays | 3 no-credential holes closed — docs/49 |
| No server, hidden timing | `client/`, `tests/test_client` | real MCP nodes | what each node receives per round | identical points and bytes for real and cover rounds; one round per tick — docs/52 |

## Baselines

Random (lower bound), broadcast (always every source — `top_k` ignored),
cosine top-k ("normal router": max-over-centroid cosine, top-k), oracle
(ground-truth engines), smart (adaptive gain/budget), plus the decoy
variants. RAGRoute is an unimplemented adapter; TASR is an external adapter.
No superiority over a published learned router is claimed.

## Reproducibility

`python -m eval.scorecard` assembles the configuration × axis table from the
newest result CSVs (`--run` re-executes every backing harness with the
arguments the docs notes record). It copies numbers; it computes nothing.

Exact environment: `backend/requirements-lock.txt`. Every experiment writes
per-seed and summary CSVs to `data/eval_results/` and records its command in
its docs note. Seeds 11/22/33 throughout; seeds share data, so spreads are
partition sensitivity, not confidence intervals. Node data under `data/` and
BEIR corpora under `backend/vendor/` are regenerated, not committed.

## Known limitations

- The coordinator is trusted; the relay is not yet a separate process.
- 1,000 sources not run; 300 virtual, 30 real.
- E10 is one model, one seed, 150 questions; ±8-point intervals.
- Cells cost one genuine contact and 0.12–0.13 of utility; 2-genuine cells
  are measurably weaker.
- PSI response size is linear in the node's table (~170 KB per 40-doc node);
  blind unlock moves that to a one-time download that grows with the
  federation (83 MB for 5,000 PMC patients) — per-query PSI with cells
  remains for nodes too large to cache.
- Blind unlock discloses the P unlocked clusters' records (74–393 per
  question at P = 4–24; HyFedRAG-style 80).
- Blind retrieval is not uniformly equal to or better than the matched
  baseline: P=8 retains 81–94% of its MRR across partitions, P=24 retains
  97–98% (docs/50). The HyFedRAG-style baseline is a local reimplementation.
- A finite cover-traffic demo is not an always-on anonymity service;
  credential identity and network jitter remain outside its demonstrated claim.
- Open findings from the audit (docs/49): cell churn and self-declared cell
  labels, a shared HMAC key across nodes, replay within a day, the
  psi_envelopes size leak, unauthenticated node registration, prompt
  injection, de-identification gaps.
- No routing-level defence against a forged profile.
- Node-side de-identification is rules + the node's registry + optional NER (docs/44):
  cued and registered identifiers do not leave the node; ~13% of uncued,
  unregistered names still do with NER on.
- Role-based access (docs/45) hides restricted documents and, through role-scoped
  publication, their centroids and topic words from roles without access; a node
  with no public documents still publishes a profile built from restricted content.
- Healthcare federation is public literature partitioned by topic.
