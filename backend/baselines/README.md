# Baseline adapters

Use published implementations as the research platform where they can accept the
project's sources and queries and return routing decisions.

## Priority

1. `ragroute_adapter.py` — official RAGRoute source routing, primary baseline.
2. `tasr_adapter.py` — routing-hijacking attack, HERouter and unmodified TASR.
3. `broadcast.py` — all sources.
4. `random_router.py` — random top-k.
5. `cosine_router.py` — transparent profile-similarity top-k.
6. `oracle.py` — qrel-derived upper bound.

RAGRouter is documented as adjacent NeurIPS work but is not labelled a direct
source-routing baseline unless it can be configured with custom distributed
knowledge sources and return their ranked IDs.

Do not vendor third-party code without checking its licence. Prefer pinned Git
submodules, installation scripts or adapters and record the exact upstream commit.
