# Router

Two-stage privacy-aware source router.

- `registry.py` — node profiles, flattened FAISS centroid index, trust state
- `coarse.py` — stage 1, max-over-centroid scoring, 1000 to ~50 candidates
- `rerank.py` — stage 2, relevance + trust + cost, 50 to k
- `anonymity.py` — stage 3, topic-stable decoy sampling, k to m
- `trust.py` — stage 4, decoy-aware wrapper around TASR

Use max over centroids, not mean. Averaging buries a strong single-cluster match
under many irrelevant ones, and this is the most common way a coarse filter
silently loses recall.
