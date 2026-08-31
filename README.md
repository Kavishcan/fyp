# Training-Free Exposure-Constrained and Trust-Aware Source Routing for Federated RAG

Final year project. A privacy layer for federated retrieval-augmented generation
that selects a small set of relevant, trustworthy sources while measuring and
reducing leakage from queries and observable routing decisions. Healthcare is the
case-study domain; the routing method is domain independent.

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

**Baseline-first.** The project does not rebuild ordinary source routing before
testing existing implementations. Official RAGRoute is the primary
relevance/efficiency platform; Mu and Li's routing-hijacking repository supplies
the A3 attack, the HERouter comparison, and the TASR defence. Both are accessed
through a common adapter contract (`register_sources`, `rank`) so the privacy
layer sits on top of a reproduced baseline rather than a bespoke router. See
[docs/10-baseline-selection.md](docs/10-baseline-selection.md).

## Structure

| Path | Contents |
|---|---|
| `docs/` | Gap, proposal, architecture, router design, experiments, datasets, roadmap, deployment, thesis mapping |
| `src/baselines/` | Adapters for runnable published routers and simple controls |
| `src/router/` | Proposed privacy, exposure and trust layer |
| `src/nodes/` | MCP node servers and in-process simulator |
| `src/attacks/` | A1 inversion, A2 source inference, A3 hijack integration |
| `src/eval/` | Instrumentation, metrics, ablation harness |
| `data/` | Dataset prep and node partitioning |
| `experiments/` | Configs and result logs |

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

Implemented, tested locally on synthetic data, not yet run against any real
dataset or upstream repository:

- `src/baselines/`: the `SourceRouter` adapter contract, plus broadcast,
  random, cosine (max/mean/top-r-mean aggregation), and oracle controls.
- `src/router/`: source registry with a neutral trust prior, empirical query
  and profile perturbation, exposure cost and budget enforcement, topic-stable
  and random anonymity-set construction, bounded trust update (unmodified and
  decoy-aware), and the pipeline composing all of it around a baseline router.
- `src/nodes/`: PII-redaction heuristic, k-means profile construction with
  noise, in-process source simulator, and A3 profile forgery.
- `src/attacks/`: A2 source-inference (frequency and intersection variants —
  the intersection attack is what topic-stable decoys are specifically
  designed to defeat), a nearest-neighbour A1 inversion baseline, and a local
  hijack-trial harness for prototyping against the project's own trust update.
- `src/eval/`: routing metrics (recall/coarse-recall kept separate, precision,
  MRR, nDCG, audit cost), per-query instrumentation, and baseline-provenance
  recording.
- `data/partition.py`: cluster-based and random synthetic source partitioning.
- 59 unit/integration tests, all passing, run on synthetic vectors with no
  optional heavy dependencies required.

**Not yet done, deliberately:** `ragroute_adapter.py` and `tasr_adapter.py` are
contract-only stubs — they raise until the actual upstream repositories
(linked in [docs/10-baseline-selection.md](docs/10-baseline-selection.md)) are
cloned, verified against the acceptance gate, and wired in. No baseline result
should be reported until that reproduction has actually been run. MCP
transport (`src/nodes/server.py`) is a thin, unwired stub, per the build order
in `docs/04-router-design.md` — it comes after the in-process pipeline is
validated against real data, not before.
