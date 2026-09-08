# Baseline adapters

These are comparison methods, not required engines beneath SmartRouter.

- ragroute_adapter.py: official RAGRoute adapter placeholder; not runnable yet.
- tasr_adapter.py: external TASR integration, distinct from smart EvidenceTrust.
- broadcast.py: all sources.
- random_router.py: random top-k.
- cosine_router.py: profile-similarity control.
- oracle.py: qrel-derived reference; labels must never reach the proposed router.

Adapters preserve the upstream decision rule. SourceRouter.rank is a ranking
contract; SmartRouter.route returns a constrained variable-size set. Record
selection-semantic differences in comparisons.

The RAGRoute adapter's old docstring overstates the full-stack/Ollama requirement.
Upstream supports disable-LLM operation and has a routing module that can be
wrapped. Actual weights, source features and compatible embeddings are still
required. A routing-only wrapper and baseline reproduction remain pending.

HERouter/DP-CR are optional comparisons with separate artifact and threat-model
verification, not existing smart-mode protections. RAGRouter is adjacent LLM
routing, not automatically a direct knowledge-source baseline.

See [baseline requirements](../../docs/10-baseline-selection.md).
