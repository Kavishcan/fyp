# FedSafeRouter

Training-Free Exposure-Constrained and Trust-Aware Source Routing for
Federated RAG. Final year project. A smart, privacy-aware source router for
federated retrieval-augmented generation that selects a small set of relevant,
trustworthy sources while measuring and reducing leakage from queries and
observable routing decisions. Healthcare is the case-study domain; the
routing method is domain independent.

The name is literal: **Fed**erated + **Safe** + **Router** — the contribution
is the router and its privacy/trust layer specifically. The demo does run a
full pipeline end to end (routing -> retrieval -> generation), but generation
itself is not the research contribution and, in the demo, is not even
built the way the research design specifies — see Generation below.

## The problem in one paragraph

Federated RAG keeps documents local, but routing still exposes a query-derived
representation and a pattern of contacted sources. Existing source routing
primarily optimises relevance and efficiency. Encrypted routing can protect query
content while preserving the same source ranking, so it does not by itself hide
the observable selection pattern. This project measures that leakage and adds a
training-free privacy and trust layer to a reproduced public routing baseline.

## Architecture

Three trust zones, with the router in the middle and an adversary on each side.
Full detail in [docs/03-architecture.md](docs/03-architecture.md); design contract
in [docs/04-router-design.md](docs/04-router-design.md).

- **Trusted zone (user side).** Query embedding, perturbation, and generation
  (a local open-weight model, fixed prompt) happen here.
- **Router zone (honest-but-curious, A1).** Holds the source-profile registry and
  makes the selection. Never holds documents.
- **Routing-observer zone (A2).** Observes which sources are contacted and when,
  across many queries, but not query content.
- **Node zone (some malicious, A3).** Each node holds its own documents and local
  index; at least one forges its published profile.

Online path:

```
query
  -> embed + perturb (user side)
  -> baseline router adapter        (RAGRoute / cosine top-k / etc.)
  -> proposed privacy layer         (exposure constraint, trust-aware selection,
                                      anonymity set: k genuine + decoys = m)
  -> fan out to m sources
  -> each source retrieves locally, returns top-n passages
  -> merge + rerank
  -> trust update (feeds back into rerank)
  -> local LLM, fixed prompt -> answer
```

Offline path (once per source): documents -> PII removal -> local embed and
index (never leaves the source) -> k-means centroids -> Gaussian noise -> publish.

**Two embedding spaces, deliberately kept separate.** FeB4RAG and MultiHop-RAG
both use a different embedding model per source, not one shared model — and a
vector from one embedding model can't be compared against a vector from
another (different dimensionality, unrelated geometry), so naive shared-space
cosine similarity would silently break under that realism. The fix: a **shared
routing embedder** (one model, every profile and every routing-time query) is
the only thing the router ever compares — that's what keeps max-over-centroid
scoring valid and training-free. Each node's **own local embedder** (free to
differ node to node) is used only for that node's local index, and the query
is re-embedded through it again, per selected node, at retrieval time. See
`backend/nodes/simulator.py` module docstring and `backend/api/embedder.py`.

**Baseline-first.** The project does not rebuild ordinary source routing before
testing existing implementations. Official RAGRoute is the primary
relevance/efficiency platform; Mu and Li's routing-hijacking repository supplies
the A3 attack, the HERouter comparison, and the TASR defence. Both are accessed
through a common adapter contract (`register_sources`, `rank`) so the privacy
layer sits on top of a reproduced baseline rather than a bespoke router. See
[docs/10-baseline-selection.md](docs/10-baseline-selection.md).

## Structure

Monorepo: a Python research backend, a Next.js dashboard frontend, and
gitignored local checkouts of the external baselines being reproduced.

| Path | Contents |
|---|---|
| `backend/baselines/` | `SourceRouter` adapters — RAGRoute, TASR/HERouter, broadcast, random, cosine, oracle |
| `backend/router/` | Proposed privacy, exposure and trust layer |
| `backend/nodes/` | Real MCP node servers (`mcp_server.py`), the client that talks to them (`mcp_client.py`), and the in-process simulator |
| `backend/attacks/` | A1 inversion, A2 source inference, A3 hijack integration |
| `backend/eval/` | Instrumentation, metrics, ablation harness |
| `backend/api/` | FastAPI service backing the frontend |
| `backend/vendor/` | Gitignored clones of RAGRoute and routing-hijacking-fedrag (TASR) — see below |
| `backend/tests/` | Unit and integration tests (pytest) |
| `frontend/` | Next.js + TypeScript + Tailwind + shadcn/ui dashboard |
| `docs/` | Gap, proposal, architecture, router design, experiments, datasets, roadmap, deployment, thesis mapping, baseline selection |
| `data/` | Dataset prep and node partitioning |
| `experiments/` | Configs, result logs, and the baseline reproduction log |

## Running it

Backend (from repo root). **Requires Python 3.10+** — the `mcp` SDK dropped
3.9 support entirely, and node server processes need it too:

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # brew install python@3.12 if needed
pip install -r backend/requirements.txt
uvicorn api.app:app --reload --app-dir backend
```

To see real MCP nodes (see "MCP nodes" below) rather than an empty source
list, fetch a couple of small BEIR corpora and prepare their node files
first — otherwise the backend starts fine with zero nodes and you register
simulated ones from the UI instead:

```bash
mkdir -p backend/vendor/beir && cd backend/vendor/beir
for name in arguana nfcorpus; do
  curl -sL -o "$name.zip" "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/$name.zip"
  unzip -q "$name.zip" && rm "$name.zip"
done
cd ../../.. && python data/prepare_beir_nodes.py
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm run dev
```

Open `http://localhost:3000`. The **Architecture** panel at the top is a live
[React Flow](https://reactflow.dev) diagram of the actual pipeline — query,
shared-embedder routing, the anonymity set, and the feedback loop into trust
update — with currently registered sources rendered as real nodes in it,
pulled from `/nodes`. Click the dashed "+ Add source" node to register a new
one directly from the diagram (same effect as the Register panel below; both
update the same backend state). Below that: register a source with a few
documents, run a query, then use "Reveal audit trail" to see the genuine/decoy
breakdown the query response itself deliberately withholds.

Tests: `pytest` from the repo root (config in `pyproject.toml` points at
`backend/`).

## Generation (demo only — reads as a departure from the research design)

`docs/02-proposal.md` and `docs/03-architecture.md` specify generation on a
**local** open-weight model specifically so retrieved passages and the query
never leave the trust boundary — that's what keeps prompt/output leakage out
of the thesis's scope. The demo API instead calls an external provider
(OpenAI or Gemini) for convenience, which means passages **do** leave the
boundary. Don't use its output as evidence for any privacy claim; treat it as
a UI convenience, not part of the evaluated system.

```bash
cp backend/.env.example backend/.env
# fill in exactly one: OPENAI_API_KEY or GEMINI_API_KEY
```

Provider is auto-detected from whichever key is set (or force one with
`LLM_PROVIDER=openai|gemini`). With neither key set, `/query` keeps returning
`answer: null` as before. See `backend/generation/` — the interface
(`Generator.generate(question, passages)`) is provider-agnostic, so a real
local-model implementation can replace this later without touching the API
layer.

## MCP nodes

Two kinds of source coexist in the same registry and pipeline:

- **Simulated** (the Register panel / dialog): documents posted straight to
  the coordinator's own process. Fast to set up, nothing genuinely separate.
- **MCP-backed** (`backend/nodes/mcp_server.py`): a real, separate OS process
  per source, holding real documents (from `data/prepare_beir_nodes.py`,
  sourced from the actual BEIR `arguana`/`nfcorpus` corpora — not toy
  strings), reached over the actual MCP protocol via
  `backend/nodes/mcp_client.py`. The coordinator never reads a node's
  documents directly — at startup it calls each node's `get_profile` MCP tool
  to fetch the (perturbed, centroid-only) profile it publishes, and at query
  time it calls `retrieve` to get back passages. Every one of those calls
  spawns and tears down a real subprocess (`nodes/mcp_client.py`'s module
  docstring explains the tradeoff — no persistent session, so no
  event-loop-bridging complexity inside a synchronous FastAPI app).

Every `*.json` file in `data/mcp_nodes/` (produced by the prep script above)
is auto-registered on backend startup. They show up in `/nodes`, the sources
table, and the Architecture flow diagram with a **transport: MCP** badge,
indistinguishable from simulated sources to the router — the whole point is
that routing, decoys, and trust don't need to know which kind they're talking
to.

## External baselines (`backend/vendor/`)

RAGRoute and the routing-hijacking-fedrag repo (source of TASR and HERouter)
are cloned locally, not committed — `backend/vendor/` is gitignored. Clone them
yourself to reproduce:

```bash
git clone https://github.com/sacs-epfl/ragroute backend/vendor/ragroute
git clone https://github.com/Junjie-Mu/routing-hijacking-fedrag backend/vendor/routing-hijacking-fedrag
```

- **TASR is wired for real** (`backend/baselines/tasr_adapter.py` loads their
  actual `TrustAwareRouter` class directly, bypassing their package's heavier
  optional imports). `backend/tests/test_tasr_adapter.py` runs against it
  automatically once cloned.
- **RAGRoute is not wired up.** It's a multi-process system (HTTP coordinator +
  routing process + Ollama for generation), not an importable router — see the
  docstring in `backend/baselines/ragroute_adapter.py` for exactly what running
  it for real requires.
- Provenance for both is recorded in `experiments/reproduction_log.jsonl`
  (commit hashes, licences, what's actually verified vs. not).

## Documents

1. [Research gap](docs/01-research-gap.md)
2. [Proposal](docs/02-proposal.md) — Chapter 1 format
3. [Architecture](docs/03-architecture.md)
4. [Router design](docs/04-router-design.md)
5. [Experiments](docs/05-experiments.md)
6. [Datasets](docs/06-datasets.md)
7. [Roadmap](docs/07-roadmap.md)
8. [Deployment](docs/08-deployment.md)
9. [Thesis mapping](docs/09-thesis-mapping.md)
10. [Baseline selection](docs/10-baseline-selection.md)

## Status

**Backend:** implemented and tested — the `SourceRouter` contract and local
controls, the full privacy/trust layer (registry, perturbation, exposure
budget, topic-stable anonymity sets, bounded trust update), node simulation
with per-node local embedders decoupled from the shared routing embedder,
**real MCP node servers backed by real BEIR document data** (see "MCP nodes"
above — this is genuine separate-process, real-protocol, real-data
communication, not a simulation of it), A1/A2/A3 attack modules,
evaluation/instrumentation, a real (not reimplemented) TASR adapter, and
pluggable generation (OpenAI/Gemini, demo-only — see Generation above). 96
tests passing, including live round trips against real spawned MCP
subprocesses.

**Frontend:** a working dashboard — a live React Flow diagram of the actual
architecture with registered sources rendered as real nodes in it (add a
source directly from the diagram), a table view with live trust scores and
local model, a query panel with citations and (when a provider is configured)
a generated answer, and the audit trail reveal. No auth, no persistence beyond
the backend's in-memory state — a research demo, not a deployment target.

**Not yet done, deliberately:**
- `ragroute_adapter.py` is a stub — RAGRoute needs its own process (and Ollama)
  running, which is a real resource commitment, not something to silently
  trigger.
- No local-model generation — only the external-API demo path exists so far.
  The research design's local model is still unbuilt.
- MCP nodes hold a small, fixed sample (40 docs each) from 2 of FeB4RAG's 16
  BEIR corpora, not the full benchmark, and use the placeholder hashing
  embedder, not a real sentence-embedding model. Real routing-quality numbers
  need both scaled up.
- A2 exists as a tested module but isn't wired into the API as a live observer.
