# Baseline selection and evidence

## Current decision

Build the independent SmartRouter and compare it with published and transparent
local source routers. This revises the earlier baseline-as-engine design.
Do not present that revision as supervisor approval; confirm the new scope at
the next meeting.

```text
Frozen sources, queries, labels and evaluation conditions
  -> broadcast / random / cosine / oracle controls
  -> official RAGRoute or explicitly labelled adaptation
  -> proposed SmartRouter and its ablations
  -> matched retrieval, exposure, attack and cost evaluation
```

## Roles

| Method | Role | Local implementation status |
|---|---|---|
| RAGRoute | Intended primary published source-routing comparator | Upstream checkout exists locally; project adapter is a stub |
| Broadcast / random / cosine | Direct local controls | Existing SourceRouter adapters |
| Oracle | Label-derived diagnostic reference | Existing adapter; never a deployable method |
| TASR | External security comparison | Adapter exists; not the new EvidenceTrust heuristic |
| HERouter | Optional encrypted routing comparison | Requires a verified runnable condition and explicit key/observer assumptions |
| DP-CR | Optional DP routing comparison | Verify full mechanism/artifacts before implementing or claiming reproduction |
| RAGRouter | Adjacent routing methodology | Do not substitute LLM routing for a direct knowledge-source comparison |

Publication status and exact versions must be verified against authoritative
records before submission. This implementation update does not re-audit the
literature or infer quality from author metrics.

## RAGRoute integration requirements

The inspected upstream code supports routing without LLM generation and contains
a router module that can be wrapped. Ollama is not inherently required for a
routing-only comparison. The old adapter docstring overstates that dependency;
the adapter remains unimplemented.

Its inspected FeB4RAG configuration uses 13 named sources, specific embedding
models, centroids, source-ID features and learned weights. The checkout inspected
during implementation contained training scripts but not a ready checkpoint.
Obtain compatible artifacts or reproduce offline training.

The inspected selection rule uses sigmoid probability above 0.5 rather than
always selecting top three. Preserve that rule for native reproduction.
Exposing scores/top-k or changing source embeddings/identities must be recorded
as an adaptation. Pin the exact upstream commit because paper and code versions
may differ.

Use the upstream routing decision before retrieval; its full query endpoint
already dispatches source requests and cannot retroactively enforce a budget.

## Comparison contract

Baseline adapters expose register_sources and rank with ranked IDs/scores where
available. SmartRouter.route also consumes coordinator evidence/config and
returns a variable-size constrained set. Preserve both semantics.

A direct comparison requires compatible source/question access, observable
selection, repeatable runs and documented retrieval/generation settings.
Source count, source IDs, embeddings, learned features and query splits must be
explicit. Do not force a 13-source checkpoint onto 49 or 1,000 clients silently.

## Reproduction record

Record code commit, artifact hashes, license, environment, hardware, dataset
version, split/partition manifest, model versions, profile construction, query
order, parameters, seed, exact command, adaptations and raw per-query results.

A clone is not reproduction. A unit test is not the paper's benchmark. Published
aggregate numbers are related-work context, not directly comparable local
measurements. An independently reimplemented baseline must be labelled as such.

If upstream artifacts cannot run, report the limitation and use transparent
controls while pursuing a documented adaptation. Do not fabricate official
results. Baseline training, when needed, does not change the proposed algorithm's
training-free status.

## Primary references for verification

- [RAGRoute code](https://github.com/sacs-epfl/ragroute)
- [RAGRoute DOI](https://doi.org/10.1145/3721146.3721942)
- [Routing-hijacking/TASR code](https://github.com/Junjie-Mu/routing-hijacking-fedrag)
- [Routing-hijacking paper record](https://arxiv.org/abs/2605.28112)
- [RAGRouter code](https://github.com/OwwO99/RAGRouter)
