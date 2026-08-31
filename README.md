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

Planning and baseline-selection stage. Nothing implemented in this repository.

**Next action:** reproduce official RAGRoute on FeB4RAG and record ranked source
IDs, Recall@K, latency and communication output. Then reproduce the public
routing-hijacking/TASR evaluation used for RQ03. Do not rebuild an ordinary
source router before testing whether the published implementations are usable.
