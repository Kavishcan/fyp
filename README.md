# FedSafeRouter

**Privacy-aware source routing for Federated Retrieval-Augmented Generation:
mitigating query and access-pattern leakage.**

A federated RAG system can reveal a question to contacted sources and its
topic through the contact pattern. The recommended **blind unlock** mode
(`backend/privacy/blind_unlock.py`) keeps question text and embeddings on
the trusted device and sends the same number of blinded points to every
node. Its fixed contact set puts topic inference at the majority-class floor
on three simulated PMC-Patients splits (docs/50). Earlier PSI + anonymity
cells reduces leakage but does not consistently close the pattern channel.

Node-side de-identification (`backend/privacy/deidentify.py`) reduces
disclosure of patient identifiers in retrieved passages. It is **not** a
validated clinical de-identifier: unregistered, uncued names and
quasi-identifiers can remain (docs/44).

Everything is measured, including what did not work: Gaussian perturbation,
semantic hashing, topic-stable decoys against the topic attack, hard trust
gates. The authoritative description of the system, threat model and claims
is [docs/41 — current system specification](docs/41-current-system-specification.md).

This is a final-year research prototype, not a deployment for real patient
data. In the studio the API coordinator sees the question; the standalone
`client.Device` keeps it on the user's machine (docs/52). Nodes still see
the credential and activity, unless fixed-rate cover traffic is used for
the latter. No differential privacy or end-to-end patient privacy is claimed.

## Recommended pipeline (`routing_mode="blind"`)

```text
question
  → local embedding and ranking of signed cluster profiles
  → top-P clusters chosen on the device; P real-or-dummy blinded points to EVERY node
  → nodes OPRF-evaluate; device opens matching cached envelopes
  → device-side dense or hybrid ranking and top-k evidence
  → local generation (when configured) → answer + citations
```

The API default remains legacy for experimental controls; the studio selects
blind mode explicitly. The standalone client is the private deployment path.

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
| Comparison with a local HyFedRAG-style baseline | [46](docs/46-hyfedrag-comparison.md), [50](docs/50-robustness-significance-sessions.md) | blind mode sends the question to no hospital; matched-ranker retrieval depends on probe budget and split |
| Role-based access on nodes | [45](docs/45-role-based-access.md) | node serves each role only its collections, enforced inside PSI; lying about a role gains nothing |
| Node-side de-identification | [44](docs/44-node-side-deidentification.md) | cued/registered canary identifiers removed; unregistered bare names can remain |
| Credential gate on PSI | [43](docs/43-credential-gate.md) | node evaluates only for allow-listed clients within a daily budget; dumping a node takes 8–10 days, logged |
| Blind unlock and retrieval trade-off | [47](docs/47-blind-unlock.md), [50](docs/50-robustness-significance-sessions.md) | matched hybrid MRR: P=8 retains 81–94% of the local HyFedRAG-style baseline across splits; P=24 retains 97–98% |
| Standalone device and cover schedule | [52](docs/52-standalone-client-and-cover-traffic.md) | no API server in the standalone query path; equal-size real/cover rounds, with operational limits |

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

## Try blind mode in the studio

```sh
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Is milk good for our bones?","routing_mode":"blind","blind_probes":8,"rerank":"hybrid","evidence_top_k":2}'
```

The API process sees this question. To keep it on the user's machine, run
`python -m client` from the backend (docs/52). `GET /audit/{query_id}` exposes
a trace and must not be treated as a privacy boundary.

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

Blind unlock contacts every node and downloads an encrypted table per node;
this has scaling and bandwidth costs. The finite CLI cover demonstration
is not an always-on traffic-hiding service; clock jitter was not measured.
Malicious-source selection and passage poisoning are not solved. De-identification
is incomplete, and retrieval is below the matched local HyFedRAG-style
baseline on most splits; at P=24 the gap is small but not universally
statistically indistinguishable (docs/50). Answer quality is one model, one
seed, 150 MIRAGE questions. The hospitals are simulated partitions of public
data, not real institutions. Do not use real private or patient data.
