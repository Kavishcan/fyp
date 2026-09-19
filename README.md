# FedSafeRouter

**Privacy-aware source routing for Federated Retrieval-Augmented Generation:
mitigating query and access-pattern leakage.**

A federated RAG system routes each question to a few of many independently
owned knowledge sources. That routing leaks twice: the contacted sources see
the question, and anyone watching *which* sources were contacted can infer
what it was about. This repository measures both leaks on a standard
federated-search benchmark, shows that the cheap fixes do not close them,
and implements and measures two that do:

- **Query content** never reaches a source: dispatch is an OPRF / labeled
  private-set-intersection exchange over cluster ids (`backend/privacy/psi.py`).
  On 200 synthetic privacy cases, 0 of 3 sensitive values are exposed to
  contacted nodes, against 3 of 3 for text or vector dispatch.
- **Query topic** is hidden from a pattern observer by fixed anonymity cells
  (`backend/router/anonymity.py`): topic inference falls from 0.454 to 0.201
  and source inference from 0.744 to 0.231 at the same fan-out.

Everything is measured, including what did not work: Gaussian perturbation,
semantic hashing, topic-stable decoys against the topic attack, hard trust
gates. The authoritative description of the system, threat model and claims
is [docs/41 — current system specification](docs/41-current-system-specification.md).

This is a final-year research prototype. Claims are routing-stage privacy
against contacted sources and a pattern observer under a trusted
coordinator; not end-to-end privacy, not differential privacy, not a proof.

## Pipeline (`routing_mode="psi"`, `decoy_policy="cells"`)

```text
question
  → shared routing embedder                      (device side)
  → local ranking over signed source profiles
  → dispatch set: the fixed cell of the top source, one exposure budget
  → per node: nearest public cluster centroids → blinded ids
       → node OPRF-evaluates and serves encrypted envelopes   (real MCP process)
       → only matched envelopes open on the device
  → rerank inside and across nodes, evidence trust update
  → local generation (Ollama, localhost only) → answer + citations
  → per-stage latency and per-contact bytes logged
```

Legacy (cosine + rerank + decoys) remains the API/dashboard default; `smart`,
`v2` and `psi` are opt-in per request.

## Results index

| Question | Note | Headline |
|---|---|---|
| Does routing leak the topic? | [39](docs/39-routing-pattern-leakage.md) | cosine router: 0.496 topic accuracy (chance 0.077); sticky decoys do not reduce it |
| A decoy policy that works | [40](docs/40-cells-rerank-healthcare.md) | cells: 0.201 topic / 0.231 source; same-domain healthcare: 0.272 / 0.250 |
| Query content to sources | [37](docs/37-privacy-cases-and-transport.md) | psi 0 of 3 values exposed; ~10 ms, ~170 KB per contact |
| PSI stage and FeB4RAG routing | [36](docs/36-psi-dispatch-and-feb4rag.md) | nDCG@1 0.734, MRR 0.578; privacy modes cost nothing in routing |
| Answer quality | [38](docs/38-answer-quality.md) | MIRAGE, local Qwen3.5-9B: closed 0.547 / psi 0.580 / broadcast 0.627 |
| Bucketing for PSI | [35](docs/35-bucket-recall.md) | SimHash fails (0.001); cluster ids 0.89 of dense recall |
| Scaling and transport | [33](docs/33-scaling-and-transport.md) | 30–300 sources; 30 real MCP processes |
| Cheap defences fail | [32](docs/32-v2-attack-results.md) | inversion 1.000; noise kills utility first; trust gate deadlocks |
| v2 vs legacy | [30](docs/30-privacy-pipeline-v2.md), [31](docs/31-mode-comparison-results.md) | v2 ties legacy; exemption leaks decoys |
| Encrypted scoring PoC | [34](docs/34-encrypted-query-scoring.md) | Paillier, correct, ~18 s/query — experimental |

Each note records its command, seeds and what it does not establish.

## Run locally

Python 3.10+. Exact versions used for every reported number are in
`backend/requirements-lock.txt`.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
ROUTING_EMBEDDER=BAAI/bge-base-en-v1.5 MCP_PERSISTENT=1 \
  .venv/bin/uvicorn api.app:app --app-dir backend --port 8000
```

Prepared node files in `data/mcp_nodes` are registered at startup as real MCP
subprocesses. `ROUTING_EMBEDDER` selects the shared routing space for the
coordinator and every node process (default `hashing`, the dependency-free
placeholder; the semantic model above is what every measured result used and
makes demo retrieval meaningful). With a semantic model use `MCP_PERSISTENT=1`
so each node loads the model once — first start-up is ~10 s per node. For local generation install [Ollama](https://ollama.com), pull
a model, and set `LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3.5:9b`. Hosted
providers (OpenAI/Gemini) work but send the question and passages off-device;
they are a quality reference, not a private configuration.

Frontend:

```sh
cd frontend && npm install && npm run dev
```

## Try the private path

```sh
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Is milk good for our bones?","routing_mode":"psi","max_nodes":4,"genuine_k":1,"decoy_policy":"cells","cell_size":4,"evidence_top_k":2}'
```

`routing_details` shows the cell dispatched, per-node envelopes delivered
and opened, and `GET /audit/{query_id}` the full trace. `GET /nodes?routing_mode=psi`
reports that mode's trust state.

## Reproduce a result

The central table — every configuration against every measured axis — is one command:

```sh
cd backend
../.venv/bin/python -m eval.scorecard            # assemble from the newest result CSVs
../.venv/bin/python -m eval.scorecard --run      # re-run every backing harness first (hours; needs Ollama)
```

Individual harnesses:

```sh
cd backend
../.venv/bin/python -m eval.run_leakage            # docs/39–40 pattern leakage table
../.venv/bin/python -m eval.run_privacy_cases      # docs/37 sensitive values, attack cases
../.venv/bin/python -m eval.run_feb4rag            # docs/36 routing quality
../.venv/bin/python -m eval.run_mcp_transport --persistent --modes legacy v2 psi
LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3.5:9b ../.venv/bin/python -m eval.run_answer_quality
```

BEIR corpora under `backend/vendor/beir/` and FeB4RAG under
`backend/vendor/FeB4RAG/` are fetched per [docs/06](docs/06-datasets.md); the
synthetic privacy cases come from the companion `fedrag-dataset` repository.

## Repository map

| Path | Role |
|---|---|
| backend/router/v2.py | Local routing, exposure budget, decoy policies (`topic_stable`, `cells`) |
| backend/router/anonymity.py | Topic-stable sampling and fixed anonymity cells |
| backend/privacy/psi.py, cluster_index.py | OPRF / labeled-PSI dispatch; node cluster table |
| backend/nodes/ | Profiles, Ed25519 signing, MCP server and (persistent) client, simulator |
| backend/api/ | Coordinator (plays the device in this prototype), request validation |
| backend/attacks/ | A1 inversion, A2 source and topic inference, A3 hijack |
| backend/eval/ | One harness per results note; instrumentation |
| backend/generation/ | Ollama (local), OpenAI, Gemini |
| backend/baselines/ | Random, broadcast, cosine, oracle, smart controls; RAGRoute stub; TASR adapter |
| frontend/ | Studio; `lib/api.ts` mirrors `backend/api/schemas.py` |
| data/, experiments/ | Node preparation, results CSVs, run logs |
| docs/ | 01–10 planning; 13–17 historical pilots; 30–41 measured results and the current spec |

## Verification

```sh
.venv/bin/pytest -q                                            # from the repository root
cd frontend && ./node_modules/.bin/tsc --noEmit --incremental false
```

Test counts are not experimental, privacy or answer-quality results.

## Limitations

The coordinator is trusted and plays the user's device; separating it into
a relay is the docs/03 target. Metadata (that a query happened, its timing
and size) is not protected. A source that lies about its content is
selected as often as an honest one; the evidence rerank keeps its planted
passage out of the prompt but does not stop the contact. PSI responses are
linear in a node's table size. Answer quality is one model, one seed, 150
questions. The healthcare federation is public literature partitioned by
topic, not institutional data. Do not use real private or patient data.
