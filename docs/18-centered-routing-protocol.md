# Centered routing: development and frozen transfer protocol

## Hypothesis

Common semantic directions can make many source centroids similar. Test whether
subtracting a source-balanced background vector improves relevance ranking,
without adding document information or increasing profile size. This is a known
type of embedding geometry correction, not automatically a novel algorithm.

Normalize each published centroid, average within each source, then average
across sources. Multiply this background by strength a and subtract it from
the normalized query and centroids; renormalize and use clipped max cosine.
Each authorized, valid, trust-eligible source gets one vote. Zero vectors stay
zero. The production path must use this same transform and enforce all contact
costs. Source-profile manipulation can affect this transform; no robustness
guarantee is assumed.

## Development selection, before transfer evaluation

Use SciFact official train and NFCorpus official dev queries. Exclude exact
normalized query-text overlaps with their test sets. Use the existing frozen
16-centroid profiles and 30-source manifests from routing-study-v1. Do not
rebuild profiles from queries or judgments. Encode queries with the same cached
MiniLM snapshot. Compare a in {0, 0.25, 0.5, 0.75, 1}; a=0 is the max-cosine
baseline. Rank exactly three sources for development selection.

Choose a by macro-averaged source recall across the two development datasets,
averaging partition seeds 11/22/33 within each dataset. Resolve ties toward
smaller a. This uses development labels for hyperparameter selection but does
not fit a router/encoder model. Preserve every development result, including
the baseline, and freeze the chosen value in a JSON artifact before transfer.

## Evaluation after freezing

1. SciFact and NFCorpus test sets: exploratory regressions, already inspected.
2. SCIDOCS official test: one-pass additional benchmark; no setting changes
   based on its results. Historical uses outside this study are not audited.
3. Same 16-centroid information for every method; 30 random document shards and
   three seeds; budget 3 as primary, budgets 1 and 5 as secondary.
4. Compare raw fixed top-k, centered fixed top-k, old relative stopping (0.8),
   and the new centered budget-filling policy (relative floor zero). The latter
   spends affordable positive-score budget instead of unvalidated early stopping;
   it is not presented as a new evidence-sufficiency stopping mechanism.
5. Measure source recall, available evidence coverage, document recall@10,
   contacts, no-source rate, cap violations and isolated routing latency.
6. Primary transfer contrast: centered budget-filling versus raw fixed top-3.
   Paired bootstrap over query clusters (average partitions before resampling),
   10,000 draws with seed 20260910. Report full intervals, not only positive rows.
7. Test clone-empty and clone-bait attacks using the previous fixed donor/attacker
   simulator, budget 3. Compare raw and centered policies with and without the
   same EvidenceTrust. Also run no-attack online controls. These are descriptive
   streams, not independent-query significance tests.

## Boundaries

No supervised model training, new profile fields, qrel-derived profiles,
off-budget probes, generator calls or downloads. Published centroids may still
leak information. No claims about RAGRoute superiority, formal privacy, semantic
poisoning resistance, natural organizational partitions or real network scale.
Do not retune after transfer results. Preserve raw outputs and code/protocol
snapshots. Keep legacy production defaults unchanged until evidence warrants it.
