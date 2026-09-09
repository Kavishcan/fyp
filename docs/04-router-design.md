# Smart router design

## Evidence-budget branch note

The independent candidate-allocation experiment is specified in
[docs/20](20-evidence-budget-protocol.md), implemented in
`backend/router/evidence_budget.py`, and evaluated in
[docs/21](21-evidence-budget-results.md). It does not change the legacy/smart
rules below and must not be described as an empirically superior replacement.

The current proposal is an independent training-free source-selection heuristic.
Its implementation is [smart.py](../backend/router/smart.py). RAGRoute and other
published methods remain separate comparison baselines.

## 1. Interface

```python
SmartRouter.route(query_embedding, profiles, evidence, config) -> SmartDecision
```

SourceEvidence is coordinator-owned: trust, observation count, authorization and
positive exposure cost. SmartConfig defines budget, source cap, minimum gain,
minimum trust, uncertainty penalty, redundancy weight and centroid aggregation.
SmartDecision contains selected IDs, candidate IDs, exclusions, per-step features,
spent exposure, stopping reason, timing and configuration.

This is not the fixed-top-k SourceRouter.rank contract used by baseline adapters.
An evaluation harness must preserve the different selection semantics.

## 2. Relevance

Normalize the query and every profile centroid. Clip centroid-query cosine to
[0, 1]. Aggregate per-source similarities using mean by default, or max as an
explicit ablation. These are existing similarity operations, not novelty claims.

Optional relevance_mode=description scores a document-derived description vector.
combined mixes centroid and description cosine scores with description_weight
(default 0.5). Model/dimension compatibility is checked, and absent metadata
excludes the source in metadata modes. Centroid remains the default. Topics are
cached via MCP registration, not fetched by exposing the query to every node.
See [metadata pilot](15-mcp-metadata-pilot.md) for the measured limitations.

Missing evidence or authorization rejects the source. Incompatible/nonfinite
profile arrays are excluded. Invalid query vectors or configuration fail
validation. Zero-vector queries produce no useful sources. Duplicate source IDs
are rejected; deterministic ties are resolved by source ID.

## 3. Source profile registry and evidence

Profiles hold centroids, version, policy labels, document-count bucket and other
metadata. They are not trustworthy merely because they were published.
Registry version checks exist; signature validation is still a placeholder.

Smart trust is stored separately from advertised profile trust and from legacy
BoundedTrustUpdate. Its neutral prior is 0.5. Changing/removing a profile resets
smart observations. This also permits reputation reset abuse until identities
and profile changes are handled more strongly.

## 4. Marginal selection rule

For source i and the set S already selected:

```text
r_i = mean or max of clipped centroid-query cosines
t_i = max(0, observed_trust_i - u / sqrt(observations_i + 1))
d_i(S) = maximum positive centroid cosine between i and any source in S
g_i(S) = r_i * t_i * (1 - rho * d_i(S))
```

Only authorized sources with t_i >= minimum_trust are eligible.
Only candidates with g_i(S) > minimum_gain and whose cost fits are considered.
Select the highest g_i(S)/cost_i, then update overlap estimates and repeat.

Default u=0.1, rho=1 and minimum_gain=0.05 are provisional, not optimized.
Profile overlap is an imperfect redundancy proxy, not semantic evidence coverage.
There is no optimality theorem or verified novelty claim for this greedy rule.

## 5. Strict exposure constraint

```text
sum(cost_i for i in selected) <= exposure_budget
len(selected) <= max_sources
```

All costs are positive and finite; the implementation requires at least 1e-12.
Default unit cost counts recipients. Configured costs are declared coordinator
assumptions, not measured leakage probabilities. The budget is per query.

No genuine source is exempt. Zero budget or zero fan-out gives no contacts.
An expensive source does not prevent choosing another affordable source.
There is no forced minimum-k; the algorithm can abstain.

Stop reasons are no_eligible_sources, insufficient_gain, exposure_budget,
max_sources or candidates_exhausted. Selection cost remains reserved even when a
later retrieval fails. There are no decoys or automatic fallback contacts.

## 6. Perturbation and decoys

Query perturbation and decoy anonymity sets belong to the legacy pipeline.
Smart mode rejects nonzero query sigma and does not add decoys. Previously
published profile noise can still affect its inputs and must be recorded.

Any future decoy experiment must count decoy contacts in the same hard budget,
enforce authorization/trust eligibility and test both leakage and additional
exposure. Gaussian noise is empirical perturbation unless a formal DP mechanism
and its assumptions are separately established.

## 7. Adaptive stopping

Selection is adaptive because gain changes as overlapping profiles are selected,
and affordability changes as the budget is spent. max_sources is a cap, not a
target. The live API ignores legacy genuine_k in smart mode.

This is pre-dispatch adaptation, not iterative retrieval-driven planning or
a trained confidence model. Coverage and uncertainty are heuristics to test.

## 8. Trust feedback and security limits

The coordinator embeds returned passages in the routing space and measures each
passage's best clipped similarity to the source's profile. Their mean is the
consistency signal; empty/failed retrieval yields zero.

```text
new_trust = (old_trust * (n + 2) + consistency) / (n + 3)
new_observations = n + 1
```

Remote retrieval scores and advertised trust do not drive this update.
This mechanism is EvidenceTrust, not TASR. It does not verify factual accuracy,
provenance, signatures or source honesty. Test bait documents, forged profiles,
cold starts, re-registration and legitimate profile changes before claiming
hijacking resistance.

## 9. Implementation and evaluation order

1. Keep the tested selector and API integration as the first prototype.
2. Connect consistent semantic embeddings and freeze data/profile manifests.
3. Run local controls and reproduce the official RAGRoute comparison.
4. Measure constrained selection quality and exposure at matched conditions.
5. Run trust, overlap, threshold, aggregation and fixed-k ablations.
6. Evaluate A2 independently of contact count, and A3 against honest and malicious sources.
7. Measure real MCP costs separately from in-memory scaling.
8. Consider decoys/perturbation only as a separately justified extension.

See [experiments](05-experiments.md) for acceptance evidence and
[implementation guide](13-smart-router-implementation.md) for exact API usage.

## Relative policy experiment

`SmartConfig(selection_policy="relative")` disables centroid-overlap penalties.
It selects the best affordable relevance/trust/cost score, and compares later
scores with `relative_score_floor` (default 0.8) times the first selected score.
The reference excludes unaffordable sources. This avoids treating shared
collection topics as proof of duplicate evidence. It adds the stop reason
`relative_score_floor`; absolute minimum gain, authorization, trust eligibility,
the contact budget and max-source cap still apply.

It is not retrieval-feedback-driven planning or a guarantee of recall. Equal
scores can consume the full budget; zero positive scores still abstain.
The API forwards both new fields in smart mode and rejects relative selection
in legacy mode. The default remains `overlap` for backwards compatibility.

The offline study uses max aggregation, zero absolute gain floor, no uncertainty
penalty, and both four- and sixteen-centroid profiles. The live API retains its
existing uncertainty penalty, hashing encoder and EvidenceTrust update.
TASR integration in the study is an evaluation-only post-layer adapter.
See [frozen protocol](16-routing-study-protocol.md).

## Centering experiment and budget-filling control

`relevance_mode="centered"` is experimental; `centering_strength` must lie in
[0, 1]. Normalize each centroid, average within each source, and average those
source means. Subtract strength times that background from both the normalized
query and each centroid, renormalize, then use the configured max/mean aggregation.
Zero vectors remain zero. Excluded sources cannot change the background.
The source ordering and score ties remain deterministic. Audit steps preserve
both raw_centroid_relevance and the transformed centroid_relevance.

This is a known geometry correction, not a novelty claim. It does not protect
published embeddings; malicious or Sybil sources can influence the background.
The development experiment selected strength 0 rather than any positive value.
It uses labelled development queries to choose a hyperparameter, but does not
train an encoder or router model. Keep the option experimental and retain the
negative result; do not promote its default strength of 1 for deployment.

With relative_score_floor=0 and minimum_gain=0, relative selection becomes a
positive-score, trust/cost-ranked budget-filling control. It still abstains on
zero useful scores, applies authorization and trust gates, and obeys weighted
cost and source caps. With unit costs and equal trust it reduces to positive-score
top-k, not a new adaptive-coverage algorithm. Higher recall than early stopping
can simply result from more contacts. See [development/transfer protocol](18-centered-routing-protocol.md).

## Legacy compatibility

pipeline.py, exposure.py, anonymity.py, perturb.py and trust.py are preserved.
The old live path still uses zero exposure/cost placeholders and the legacy
budget helper exempts genuine selections. It is not the strict-budget smart
algorithm. Do not report its behaviour as evidence for the new constraint.
