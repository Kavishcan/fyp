# CLAUDE.md

Guidance for working in this repository.

## What this is

A final-year research project: a training-free, exposure-constrained,
trust-aware privacy layer for source routing in federated RAG. The contribution
is the privacy/trust layer and the leakage measurement, evaluated on top of a
**reproduced published router**, not a new router built from scratch.

Read [README.md](README.md) for the architecture summary. Read the numbered docs
in `docs/` for full detail — `01-research-gap.md` and `02-proposal.md` for the
research framing, `03-architecture.md` and `04-router-design.md` for the system
contract, `10-baseline-selection.md` for which published works are reused and how.

## The one rule that shapes everything else

**Reuse a runnable published source router; do not rebuild ordinary routing.**
Student effort goes into the privacy layer, the leakage attacks, and the
measurement — not into reimplementing what RAGRoute or the routing-hijacking/TASR
repo already do. Before writing a new routing mechanism, check whether an
existing adapter already covers it.

## Terminology discipline

These distinctions are load-bearing for the thesis and must hold in code,
comments, docstrings, and commit messages alike:

- **"Empirical embedding perturbation," never "differential privacy"** — unless
  sensitivity, adjacency, and a formal privacy budget are actually defined and
  proven, Gaussian noise on an embedding is not DP. Name it for what it measurably
  does: resistance to a specific evaluated attacker.
- **"Reproduced" means the upstream code was actually run**, not that its
  described behaviour was reimplemented from the paper. If only the published
  numbers were used, call it a literature comparison, not a benchmark result.
- **Max-over-centroid aggregation is an ablation condition, not a default
  truth.** Mean and top-r mean must be measured as alternatives before any one
  is presented as correct.
- **New sources start at a neutral trust prior with an uncertainty penalty**,
  not full trust. Trust is earned from evidence observations.
- **An unmodified trust-defence condition must exist before any decoy-aware
  change is measured against it.** The interference result depends on having
  both conditions, not just the modified one.
- **Coarse-stage recall and final recall are logged separately.** If the
  correct source is dropped before reranking, no later stage can recover it,
  and conflating the two numbers hides which stage failed.
- **State the real-transport/simulated split explicitly wherever it appears** —
  in code comments, logs, and output — rather than letting a demo at small scale
  imply a claim at large scale.
- **No fabricated or assumed empirical values.** A metric that has not actually
  been measured is marked unverified, not filled in with a plausible number.

## Module map

| Path | Contract |
|---|---|
| `src/baselines/` | `SourceRouter` adapters (`register_sources`, `rank`) — RAGRoute, TASR/routing-hijacking, broadcast, random, cosine, oracle |
| `src/router/` | The proposed layer: `registry.py` (source profiles), `perturb.py` (perturbation), `exposure.py` (exposure cost + budget), `anonymity.py` (decoy selection), `trust.py` (bounded trust update), `pipeline.py` (composes a baseline with the layer) |
| `src/nodes/` | `profile.py` (offline profile construction), `simulator.py` (in-process nodes), `server.py` (MCP transport, added after the in-process pipeline is stable) |
| `src/attacks/` | `a1_inversion.py`, `a2_source_inference.py` (the project's primary new measurement), `a3_hijack.py` (integrates the routing-hijacking repo) |
| `src/eval/` | `instrument.py`, `metrics.py`, `sweep.py`, `ablation.py`, `reproduce.py` (baseline provenance records) |
| `data/` | Dataset loading and source partitioning |

## Build order (from `docs/04-router-design.md`)

Reproduce the baseline and get an unprotected leakage number before adding any
protection. Roughly: baseline adapter and local controls first, then A1/A2
instrumentation against the unprotected router, then perturbation, then the
exposure-constrained anonymity set, then A3/TASR integration and the
interference sweep, then MCP transport last, once the in-process pipeline is
stable. Do not add a mechanism whose baseline comparison hasn't been run yet.

## External code

`ragroute_adapter.py` and `tasr_adapter.py` wrap third-party repositories
(linked in `docs/10-baseline-selection.md`). Cloning and running that code is a
separate, explicit step — do not silently vendor or fabricate their behaviour.
Record commit, environment, licence, and exact command per the reproduction
checklist in `docs/10-baseline-selection.md` before treating a result as a
direct benchmark.

## Testing

Router-logic tests should run on synthetic vectors without requiring the heavy
optional dependencies (`torch`, `sentence-transformers`, `faiss-cpu`, `mcp`) to
be installed — embedding and transport are injected, not hard-imported, so the
privacy-layer logic is testable in isolation.
