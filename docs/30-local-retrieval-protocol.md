# Document-aware local retrieval protocol

Exploratory follow-up on previously inspected MultiHop-RAG. No held-out or
novelty claim. Freeze routing weights, source profiles, chunks and embeddings
from `routing-study-answer-pilot-v1`. Verify its inputs/artifacts/code before use.

Compare four local policies across all seven frozen routers:

- cosine: unchanged relevance ranking;
- parent_cap1: promote the highest ranked chunk per parent document;
- parent_cap2: promote up to two chunks per parent document;
- mmr: standard greedy relevance/redundancy fusion, cosine similarity, weight .7.

All work from the same first 64 local cosine candidates (or the available number).
Parent caps are soft: backfill skipped chunks in original order after promoted
chunks, then preserve the unmodified tail. MMR reranks the same prefix. Settings
are fixed before this run, not selected on test labels. Report every variant.
This local processing is additional computation, not free remote retrieval;
record ranking computation time separately, not as measured network latency.

Keep C=3, B=12, equal quotas and final cosine top-5 unchanged. Cache rankings
only within the simulator; the coordinator receives exclusively charged pages.
Assert every policy contacts the same sources as its cosine counterpart and
that cosine reproduces the previous per-query final IDs/metrics. No free probes.

Report candidate/final parent-document recall, all-gold-document coverage,
distinct final documents, per-query wins/ties/losses and mean relevance of final
chunks. A gold parent is not proof its returned chunk contains the needed fact.
Examine regressions; do not infer answer accuracy from document metrics. Null
questions are run but excluded from document-recall denominators. No generation.
Question-level paired intervals are exploratory because questions share articles.

Runtime integration is opt-in in node specs, requiring aligned parent IDs for
parent caps. Defaults and paging remain unchanged. Real MCP tests prove protocol
behavior using fixtures, not benchmark quality; live hashing differs from MiniLM.

MMR is prior art, not a proposed novel algorithm:
[Carbonell and Goldstein (1998)](https://www.cs.cmu.edu/~jgc/publication/MMR_DiversityBased_Reranking_SIGIR_1998.pdf).

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_local_retrieval_study --output experiments/routing-study-local-retrieval-v1
```
