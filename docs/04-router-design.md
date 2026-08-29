# Router design

One class, one `route()` method, roughly 300 lines. Everything else in the system
feeds it or measures it.

## Registry

Built once at startup from what nodes publish.

```
node_id -> {
    centroids:  ndarray (c x d)   # c ~= 32, already noised by the node
    trust:      float             # starts at 1.0
    doc_count:  int               # for score normalisation
}
```

Flatten all centroids into one FAISS index with a row -> node_id lookup. At 1000
nodes and 32 centroids that is 32k vectors: a few hundred MB, searchable in
single-digit milliseconds. Scaling the router is cheap. Fan-out is what costs.

## Stage 1: coarse filter

```python
def coarse(self, q_noisy, n_candidates=50):
    D, I = self.index.search(q_noisy, 200)
    scores = defaultdict(list)
    for dist, row in zip(D[0], I[0]):
        scores[self.row_to_node[row]].append(dist)
    node_score = {n: max(s) for n, s in scores.items()}
    return top_k(node_score, n_candidates)
```

**Use max, not mean.** A node is relevant if any one of its clusters matches.
Averaging across 32 centroids buries a strong single match under 31 irrelevant
ones. This is the most common way a coarse filter silently loses recall.

## Stage 2: rerank

```
score(n) = alpha * sim(q, n) + beta * trust(n) - gamma * cost(n)
```

Keep alpha, beta, gamma in config. They are an ablation axis: `beta = 0` gives a
pure relevance router, which is one of the baselines for free.

`cost(n)` is optional — normalised doc count or measured latency. Include it for
the bandwidth story, drop it if it complicates the ablation.

Take the top k (3 to 10). These are the genuine hits.

## Stage 3: anonymity set

The contribution. Sampling strategy matters more than it looks.

```python
def add_decoys(self, real, candidates, m):
    pool = [n for n in candidates if n not in real]
    decoys = self.sample_decoys(pool, m - len(real))
    return shuffle(real + decoys)
```

Three things to get right:

1. **Sample decoys from the coarse candidates, not the full pool.** Drawing
   uniformly from all 1000 nodes makes the real ones obvious — they would be the
   only topically coherent members of the set.

2. **Shuffle before dispatch.** If real nodes always appear first in request
   order, the ordering leaks the answer.

3. **Keep decoys sticky per topic.** If the same query topic draws different
   random decoys each time, an observer intersects across queries and the real
   nodes fall out immediately. Seed decoy selection from a hash of the query
   cluster so a topic gets a consistent cover set.

Point 3 is the difference between a defence that survives A2 and one that
collapses under it. It is also a paragraph in the paper.

## Stage 4: trust update

After results return, score what each node actually sent:

- Did its passages reach the final merged top-n?
- Do they agree with passages from other contacted nodes?
- Does the content match the profile the node advertised?

Update with a slow exponential moving average:

```
trust <- 0.9 * trust + 0.1 * signal
```

Fast updates let one bad query blackball an honest node, and let an attacker
recover by behaving well once.

**Exclude decoys from trust updates.** They were never expected to return
anything useful. Penalising them corrupts the signal.

Signals follow Mu and Li's trust-aware post-routing framework. Compose with their
implementation rather than reinventing it.

## Build order

1. `route()` with stages 1 and 2 only, `beta = 0`, no noise. Recall@K table on
   FeB4RAG.
2. Instrumentation.
3. Noise on profiles and queries. Watch coarse recall.
4. Anonymity sets.
5. Trust.

## Two things that will bite

**Coarse recall is the ceiling.** If the right node is not in the top 50, no
amount of clever reranking recovers it. Log coarse recall separately from final
recall from day one. When performance drops after adding noise, this tells you
whether stage 1 or stage 2 broke.

**Noise calibration needs a pilot.** Run it in month 3, small, before committing.
If distance-preserving noise destroys routing recall before it meaningfully
reduces inversion success, fall back to anonymity sets alone — weaker, but still
a thesis. Learn that in week 10, not week 30.
