# Routing improvement: protocol fixed before execution

This is an implementation experiment, not a promise of novelty or improvement.
The design is motivated by the already-inspected SciFact pilot. No parameter
search will be run on the evaluation results below.

## Change

An opt-in `relative` selection policy removes the assumption that similar
source centroids imply duplicate evidence. It ranks affordable sources by
relevance times coordinator trust divided by contact cost. After the first
selection it stops when the best remaining ratio is below 0.8 of that first
ratio, or when the hard budget/cap prevents further selection. Zero-score
queries abstain. The previous `overlap` policy remains the default.

This is a relevance heuristic, not an estimate or guarantee of evidence gain.
Compare four-centroid profiles against sixteen-centroid profiles, constructed
from documents only with the existing profile builder. More detailed profiles
may improve ranking but publish more information; that improvement must not
be attributed to the stopping algorithm.

## Clean comparison

- SciFact test: exploratory, previously inspected.
- NFCorpus official test: one-pass cross-dataset check; prior historical use
  outside this experiment has not been audited. No held-out tuning claim.
- All positive qrels; frozen MiniLM snapshot; full local corpora; no downloads.
- 30 balanced random document shards, seeds 11, 22, 33, independent of qrels.
- Budgets 1, 3, 5; broadcast; max-cosine fixed-k at four/sixteen centroids;
  relative policy on both profile sizes; previous mean/overlap policy.
- Trust neutral; same retrieval scores, query order and documents per condition.
- Source recall, available relevant-document coverage, document recall@10,
  contacts, empty selections, budget violations and isolated routing latency.
- Paired query-cluster bootstrap intervals, averaging over partitions first.
  Main contrasts: fine fixed vs coarse fixed, and fine relative vs fine fixed.
  Intervals are exploratory and uncorrected for multiple comparisons.

## Profile-hijacking stress test

Add one attacker to the 30 honest sources at budget 3. It copies source 0's
sixteen-centroid profile before seeing evaluation queries. No qrels or test
queries enter the forged profile. Once contacted, the attacker either returns
no evidence or replays source 0's top-five legitimate passages (bait). The latter
tests whether relevant evidence can earn trust while a cloned endpoint receives
queries; it is not a factual-poisoning or embedding-inversion attack.

Compare fixed max-cosine, relative without feedback, relative with the current
EvidenceTrust, fixed max-cosine plus upstream TASR feedback, and relative plus
the same TASR feedback. Also run the same streams without attackers to measure
honest-client harm. All feedback is from contacted clients only, after selection;
every contact consumes budget. TASR uses its published feedback implementation
with defaults, no extra exploration contacts; its weights are applied to the
same max-centroid scores for matched comparison. Label this a post-layer adapter,
not a reproduction of the paper's full experiment or its single-centroid route.

Randomized query order is fixed per partition; trust resets for each method and
scenario, not each query. Report attack-recipient rate, honest-source recall,
returned-document recall, mean contacts, first-50 versus later attack exposure,
and budget violations. Do not use an IID query bootstrap for online trust streams.

## Boundaries

No claim of beating RAGRoute without an appropriate trained checkpoint for the
same sources and embedding space. No end-to-end answer quality, network latency,
formal privacy, source anonymity, or 1,000-real-client result is measured here.
Unit tests cover budget accounting and the opt-in API/MCP dispatch path; offline
semantic benchmarks do not imply the hashing-based live demo is semantic.
Record source hashes, model revision, configurations and raw per-query decisions.
Keep all old artifacts; each run requires a fresh directory.
