# A Smart, Privacy-Aware Source Router for Federated RAG

Final year project. A source router for federated retrieval-augmented generation
that selects a small set of relevant, trustworthy nodes from a large pool without
revealing which nodes hold what. Evaluated in a healthcare network setting.

## The problem in one paragraph

Federated RAG keeps documents local, but the routing decision is exposed. A router
sees the query, holds a map of which node knows what, and its selection pattern is
readable across repeated queries. The one existing privacy mechanism at this stage
is ranking-preserving homomorphic encryption: it hides the query from the router
and leaves the selected node IDs unchanged.

## Structure

| Path | Contents |
|---|---|
| `docs/` | Gap, proposal, architecture, router design, experiments, datasets, roadmap, deployment, thesis mapping |
| `src/router/` | Two-stage privacy-aware router |
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

## Status

Planning. Nothing implemented.

**Next action:** clone https://github.com/Junjie-Mu/routing-hijacking-fedrag and
confirm it runs. RQ03 depends on it entirely.
