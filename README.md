# A Smart, Privacy-Aware Source Router for Federated RAG

Final year project. Building a source router for federated retrieval-augmented
generation that selects a small set of relevant, trustworthy nodes from a large
pool without leaking which nodes hold what.

## The problem in one paragraph

Federated RAG keeps documents local, but the routing decision itself is exposed.
Before retrieval happens, a router decides which of potentially thousands of nodes
to contact. That router sees the query, holds a map of which node knows what, and
its selection pattern is readable across repeated queries. Confidential computing
protects documents. Federated embedding learning protects retriever training.
Secure aggregation protects model updates. None of them reach the routing stage.

## What this repo will contain

| Path | Contents |
|---|---|
| `docs/` | Research gap, proposal, architecture, experiment plan |
| `src/router/` | The two-stage privacy-aware router |
| `src/nodes/` | MCP node servers and the in-process simulator |
| `src/attacks/` | Query inversion, source inference, routing hijack |
| `src/eval/` | Instrumentation, metrics, ablation harness |
| `data/` | Dataset prep scripts and client partitions |
| `experiments/` | Configs and result logs |

## Documents

1. [Research gap](docs/01-research-gap.md)
2. [Proposal](docs/02-proposal.md)
3. [Architecture](docs/03-architecture.md)
4. [Router design](docs/04-router-design.md)
5. [Experiments](docs/05-experiments.md)
6. [Datasets](docs/06-datasets.md)
7. [Roadmap](docs/07-roadmap.md)

## Status

Planning. Nothing implemented yet.

**Next action:** clone the routing-hijack reference implementation and confirm it
runs. RQ3 depends on it entirely — see [roadmap](docs/07-roadmap.md).
