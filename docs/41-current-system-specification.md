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
| Query content | a contacted source | OPRF / labeled-PSI dispatch over cluster ids (`privacy/psi.py`) | Implemented, measured: 0 of 3 sensitive values exposed (docs/37); ~10 ms, ~170 KB per contact (docs/37) |
| Contact pattern | an observer of which sources are contacted | fixed anonymity cells (`router/anonymity.build_cells`, `decoy_policy="cells"`) | Implemented, measured: topic inference 0.454 → 0.201, source attack 0.744 → 0.231 on FeB4RAG (docs/40) |

Secondary: one malicious-source experiment (forged profile), where the
router has no defence (selected 1.000) and the cross-node evidence rerank
keeps the planted passage out of the prompt (cited 1.000 → 0.067, docs/40).

## Threat model

| Party | Sees | Trusted? |
|---|---|---|
| **Coordinator** (the API process) | raw query, embeddings, all returned passages, routing trace | **Trusted** — it plays the user's device in this prototype. Moving its device-side code to the client and reducing it to a relay is the docs/03 target, not the implementation. |
| **Contacted source** (MCP node) | legacy/smart: query text; v2: an invertible vector; **psi: blinded group elements + a fetch set** | Honest-but-curious about the query; may lie about content (A3) |
| **Pattern observer** (network, relay, colluding sources) | which sources were contacted, sizes, timing | Untrusted |
| **Malicious client** | everything a client sees | Bounded by the OPRF: ⌈clusters/nprobe⌉ evaluated queries to dump a node's table (docs/37) |

Protected assets: query text and embedding (from sources, psi); query topic
(from the observer, cells); which contact is genuine (cells / topic-stable
decoys). Not protected: that a query happened, its size and timing; the
coordinator's view; source truthfulness; generation when a hosted provider
is configured.

Claims are **routing-stage privacy** against contacted sources and a pattern
observer. Not "end-to-end", not differential privacy, not a proof beyond
reduction to DDH and the AEAD.

## Pipeline as implemented (`routing_mode="psi"`, `decoy_policy="cells"`)

```text
question
  → shared routing embedder (hashing in the live demo; bge-base in every experiment)
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

The API default remains legacy; the studio defaults to psi + cells with every mode selectable.

## Labels

| Implemented and measured | Experimental | Planned / not built |
|---|---|---|
| local routing, budget, signing, topic-stable decoys, anonymity cells, PSI dispatch, cluster index, persistent MCP, cross-node rerank, local generation, per-query instrumentation | Paillier encrypted scoring (`POST /query/private-score`, docs/34): correct, ~18 s/query keygen, ≤128 rows — the in-cluster tier if ever needed | relay separated from the device code; key authority / credentials; sublinear PSI (APSI); in-cluster HE scoring; RAGRoute reproduction; trust redesign |

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
| Enumeration | `eval/run_psi_enumeration` | synthetic | queries to open a table | ⌈C/nprobe⌉ — docs/37 |

## Baselines

Random (lower bound), broadcast (always every source — `top_k` ignored),
cosine top-k ("normal router": max-over-centroid cosine, top-k), oracle
(ground-truth engines), smart (adaptive gain/budget), plus the decoy
variants. RAGRoute is an unimplemented adapter; TASR is an external adapter.
No superiority over a published learned router is claimed.

## Reproducibility

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
- PSI response size is linear in the node's table (~170 KB per 40-doc node).
- No routing-level defence against a forged profile.
- Regex PII redaction catches 1 of 3 value types on the privacy cases.
- Healthcare federation is public literature partitioned by topic.
