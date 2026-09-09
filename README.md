# FedSafeRouter

**Training-Free Exposure-Constrained and Trust-Aware Adaptive Source Routing
for Scalable Federated RAG.**

This FYP investigates an independent source-selection algorithm. It combines
profile relevance, coordinator-observed trust, overlap-aware adaptive selection
and a strict contact-exposure budget. RAGRoute is a comparison baseline, not
the required engine underneath the proposed router.

The implementation is a research prototype. Novelty, privacy benefit, attack
resilience and scalability must be established through comparative experiments.
Healthcare is the intended case study, not a validated clinical deployment.

## Experimental evidence-budget branch

On `research/evidence-budget-routing`, a separate candidate-level router is
available through `POST /query/evidence`. It chooses the next client and local
retrieval depth under distinct client and passage-request caps, with paginated
MCP retrieval and a common cosine result merger. Legacy and smart defaults
are unchanged; the studio has not been switched to this experimental endpoint.

The [48,690-decision pilot](docs/21-evidence-budget-results.md) found zero budget
violations but **no improvement over the fixed allocation controls**. The
method remains experimental. See the [algorithm and API protocol](docs/20-evidence-budget-protocol.md)
and [prioritized reading list](docs/22-evidence-routing-reading-list.md).

The [query-level failure analysis](docs/23-query-failure-analysis.md) now traces
misses to source selection, retrieval depth or final ranking, with gold document
IDs and local ranks. A separate [anchored-feedback experiment](docs/24-feedback-routing-protocol.md)
adds opt-in `method=feedback`; its strength is selected on development data,
then frozen before an exploratory test-set comparison. No defaults are changed.
The [follow-up results](docs/25-feedback-routing-results.md) selected zero
feedback: the new option reproduces equal quotas and does not improve them.

The new [rich-profile study](docs/27-rich-profile-results.md) adds opt-in hybrid
lexical/semantic source selection with fixed quotas. Development selected lexical
weight .25. On FiQA, final Recall@5 improved from 8.573% to 9.804% on random sources
and 31.499% to 32.299% on topic sources versus the 16-centroid control, at the same
3-source/12-candidate budget. Lexical-only effectively ties on random sources;
candidate-recall superiority over byte-matched dense profiles is unresolved.
This is a measured representation improvement, not proven global novelty or a
successful adaptive quota policy. Defaults remain unchanged.

The [stronger-control audit](docs/29-strong-controls-results.md) now tunes RRF and
min-max fusion on development data and tests the frozen controls on FiQA and
49-source MultiHop-RAG. Results are mixed: hybrid has slightly higher final
MultiHop document recall, but min-max has higher candidate recall. The answer
pipeline has 192 prepared prompts and a tested EM/F1 scorer; actual generated
answer quality remains pending because no generator was configured.

## Current architecture

The [routing improvement study](docs/17-routing-study-results.md) now compares
coarse/fine source profiles, an opt-in relative stopping policy, and cloned-profile
attacks on SciFact and NFCorpus. Finer profiles improve retrieval; the stopping
and trust trade-offs do not yet establish superiority over matched baselines.
The old default remains unchanged. See the report for measurements and API usage.

The follow-up [development-selected study](docs/19-centered-routing-results.md)
tests a same-profile centering hypothesis and a budget-filling control.
Development rejected centering: raw cosine won. The experimental option remains
opt-in; do not claim it improves ranking. The usage guide now includes a
[coverage-oriented request](docs/13-smart-router-implementation.md#coverage-oriented-request)
that removes the earlier unvalidated stopping threshold while preserving budgets.

```text
Source documents -> source index + shared-space profile -> registry

Question -> coordinator embedding
         -> SMART ROUTER: relevance + trust + overlap + strict budget
         -> selected MCP / in-process nodes
         -> returned passages -> coordinator consistency-trust update
         -> optional configured generator -> answer and citations
```

The coordinator sees the raw question and returned passages. Contacted MCP
nodes receive raw questions. The pure routing module uses embeddings/profiles,
but is not isolated from the coordinator as a separate security boundary.

The live API/MCP path still uses hashing embeddings. A semantic embedder exists
but needs consistent integration before meaningful retrieval-quality results.
The legacy/smart API collects passages without a global reranker. The separate
evidence endpoint performs coordinator-cosine merging over its paid candidates.

MCP profiles now optionally include deterministic document-derived descriptions,
topics and description embeddings. Smart requests can select relevance_mode
centroid, description or combined; centroid remains the default. The
[metadata comparison](docs/15-mcp-metadata-pilot.md) found a small, statistically
uncertain fixed-contact gain and no improvement to default adaptive stopping.

## Modes

| Mode | Purpose | Current status |
|---|---|---|
| smart | Independent constrained adaptive router | Implemented; opt in through the API |
| legacy | Earlier cosine/rerank/decoy pipeline | Preserved; API and dashboard default |
| Published/local baselines | Research comparisons | Separate experiment adapters; not smart-router dependencies |

Smart mode has no decoys and no query-embedding perturbation. Default cost is one
unit per recipient; every contact must fit the budget. It can select fewer than
the source cap, or no sources. A smaller contact set is not a formal privacy
guarantee and may still reveal routing patterns.

## Run locally

Use Python 3.10+ and the existing environment when available:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn api.app:app --reload --app-dir backend --port 8000
```

Prepared node files in data/mcp_nodes are registered at startup. Without them,
register harmless simulated sources through the UI or API. Inspect existing
datasets before downloading; do not download a dataset larger than 500 MB
without revisiting the user's limit.

In a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open [the studio](http://localhost:3000). Its diagram, controls and source trust
display still describe legacy mode. The TypeScript API contract supports smart
requests, but there is not yet a studio mode selector.

## Try the smart router

After registering suitable sources:

```sh
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"COVID treatment research","routing_mode":"smart","max_nodes":5,"exposure_budget":2,"minimum_gain":0.05}'
```

Smart mode treats max_nodes as a ceiling; genuine_k is legacy-only.
routing_details in the response and audit endpoint explains selection features,
costs, exclusions and stopping. See the
[step-by-step implementation guide](docs/13-smart-router-implementation.md).

## Repository map

| Path | Role |
|---|---|
| backend/router/smart.py | Independent selector and EvidenceTrust |
| backend/router/ | Registry and preserved legacy components |
| backend/baselines/ | RAGRoute stub, TASR adapter and local controls |
| backend/nodes/ | Profile construction, hashing/semantic embedders, MCP server/client and simulator |
| backend/api/ | FastAPI coordinator, request validation and mode dispatch |
| backend/attacks/ | Existing A1/A2/A3 experiment components |
| backend/eval/ | Metrics, instrumentation and existing evaluation helpers |
| backend/generation/ | Optional generation backends |
| backend/tests/ | Unit and integration tests |
| frontend/ | Legacy-oriented studio and shared API types |
| data/ | Preparation scripts and local node datasets |
| experiments/ | Experiment configurations and provenance/results |
| docs/ | Design, research plan, dataset strategy and status |

## Generation and transport

With no configured generator, answers are null and retrieved citations remain
available. When OpenAI/Gemini is configured, the question and passages are sent
to that provider. This is demo convenience, not privacy-preserving generation.
Smart mode skips generation when no evidence was retrieved. A fixed local model
for evaluation remains future work.

Simulated sources hold documents in the coordinator process. MCP sources use
real local subprocess/stdio transport; each call starts a fresh subprocess.
Transport is real, but that does not establish remote institutional deployment.
Raw corpora remain at MCP sources while selected passages return to the coordinator.

## Baselines

- Official [RAGRoute](https://github.com/sacs-epfl/ragroute) is the intended direct
  published routing comparison. The adapter is still a stub. Its upstream
  routing module can be wrapped separately; Ollama is not intrinsically required
  for routing-only work, and upstream has a disable-LLM option.
- [Routing-hijacking/TASR](https://github.com/Junjie-Mu/routing-hijacking-fedrag)
  supplies external security comparison code. The TASR adapter is distinct from
  the new smart-mode consistency heuristic.
- Broadcast, random, cosine and oracle adapters remain local controls.

A clone or passing adapter unit test is not a completed benchmark reproduction.
Record versions, artifacts, commands and raw outputs before reporting results.
See [baseline selection](docs/10-baseline-selection.md).

## Verification and limitations

The first [real-data pilot](docs/14-smart-router-pilot.md) found that default
smart routing stops too aggressively on 30 random SciFact sources. It obeyed
the budget but underperformed cosine top-3 on source/retrieval recall. Preserve
this negative result; implementation correctness is not algorithmic benefit.

The smart-router implementation was verified with 217 Python tests passing,
including real MCP integration on a synthetic fixture, and TypeScript checking.
The 1,000-profile test checks an in-memory invariant, not deployment scalability.
Rerun these checks after changes:

```sh
.venv/bin/pytest -q
cd frontend
./node_modules/.bin/tsc --noEmit --incremental false
```

Still required: semantic-model integration, comparable baseline runs, full
attack evaluation, global evidence reranking, network/stage instrumentation,
persistent authenticated identity/policies, and larger transport experiments.
Profile signing is a placeholder; redaction is heuristic; consistency does not
prove honesty. Do not use real private or patient data in this demo.

## Documentation

1. [Research gap hypotheses](docs/01-research-gap.md)
2. [Proposal planning notes](docs/02-proposal.md)
3. [Architecture](docs/03-architecture.md)
4. [Router design](docs/04-router-design.md)
5. [Experiments](docs/05-experiments.md)
6. [Dataset strategy](docs/06-datasets.md)
7. [Roadmap](docs/07-roadmap.md)
8. [Deployment boundaries](docs/08-deployment.md)
9. [Thesis mapping](docs/09-thesis-mapping.md)
10. [Baseline selection](docs/10-baseline-selection.md)
11. [Smart-router implementation and usage](docs/13-smart-router-implementation.md)
12. [Measured smart-router pilot](docs/14-smart-router-pilot.md)
13. [MCP metadata extension and comparison](docs/15-mcp-metadata-pilot.md)
14. [Coarse/fine profiles and cloning results](docs/17-routing-study-results.md)
15. [Frozen centering development/transfer protocol](docs/18-centered-routing-protocol.md)
16. [Centering results and coverage-oriented configuration](docs/19-centered-routing-results.md)
