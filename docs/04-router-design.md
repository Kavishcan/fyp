# Router and privacy-layer design

The project reuses a runnable published source router and implements a privacy and
trust layer around a common adapter. The contribution is not another ordinary
router implementation.

## 1. Baseline adapter

Every runnable router must expose this experiment-facing contract:

```python
class SourceRouter:
    def register_sources(self, profiles: list[SourceProfile]) -> None: ...

    def rank(self, query_embedding, top_k: int) -> RoutingResult: ...
```

`RoutingResult` contains ranked source aliases, comparable scores where available,
router latency and optional internal metrics. The adapter must not silently change
the baseline's ranking logic.

Implementation priority:

1. Official RAGRoute: primary peer-reviewed source-routing baseline.
2. Mu and Li's routing-hijacking repository: A3, HERouter and TASR integration.
3. Broadcast, random and cosine top-k: local controls.
4. RAGRouter: adjacent methodology or optional black-box comparison only if it can
   accept custom knowledge-source profiles and return ranked source IDs.

If an implementation is unavailable but an executable, package, checkpoint or API
can accept the same queries and profiles and return ranked source IDs, it is usable
as a black-box baseline. Published numbers alone are literature comparison, not a
direct benchmark.

## 2. Baseline acceptance gate

Before selecting a router, verify:

- custom sources can be registered;
- FeB4RAG queries can be submitted programmatically;
- ranked source IDs are returned;
- top-k is configurable or observable;
- the same split and source profiles can be used by the proposed method;
- latency and sources contacted can be measured;
- runs are repeatable with fixed seeds;
- the licence permits academic adaptation and evaluation.

If official RAGRoute cannot pass this gate, adapt only the minimum published
routing module required to reproduce it. Do not invent a stronger or weaker
substitute and continue calling it RAGRoute.

## 3. Source profile registry

The privacy layer operates on the source profiles expected by the baseline:

```text
source_alias -> {
    centroids: ndarray(c x d),
    trust_mean: float,          # neutral prior, normally 0.5
    trust_observations: int,
    document_count_bucket: str,
    policy_labels: list[str],
    expected_latency_ms: float,
    profile_version: int,
    profile_signature: bytes
}
```

New sources do not start at full trust. Use a neutral prior with an uncertainty
penalty until evidence observations accumulate. Profiles are signed, versioned and
checked for abrupt drift, copied profiles and implausibly broad topic coverage.

## 4. Candidate ranking

Official RAGRoute supplies the main learned source ranking. A transparent cosine
baseline uses L2-normalised query and profile vectors with FAISS inner product.
With inner product, larger values are better; with an L2 index, smaller distances
are better. The implementation must state which convention it uses.

For a multi-centroid source, use maximum similarity as the initial aggregation and
compare it with mean and top-r mean in an ablation. Max-over-centroid is a design
hypothesis, not an assumed universal rule.

## 5. Exposure-constrained reranking

For candidate source `i`, normalise features to `[0, 1]`:

```text
score_i = wr * relevance_i
        + wt * trust_i
        + wa * authorization_i
        - we * exposure_cost_i
        - wc * communication_cost_i
        - wl * expected_latency_i
        - wh * hijack_risk_i
```

Apply hard constraints before ranking:

```text
authorization_i = 1
trust_lower_bound_i >= minimum_trust
projected_exposure(selected + i) <= exposure_budget
source_i is available
fan_out < maximum_fan_out
```

Measure exposure rather than using privacy as an undefined label:

```text
exposure_cost_i = a * sensitive_token_fraction_sent_i
                + b * query_specificity_i
                + c * probability_source_is_irrelevant_i
                + d * route_linkability_i
```

The first implementation may use measured proxies for these terms. Every proxy,
normalisation and weight must be reported and included in sensitivity analysis.

## 6. Query and profile perturbation

Query and profile embeddings may be perturbed before ranking. Gaussian noise alone
is not described as differential privacy. Unless sensitivity, adjacency and a
privacy budget are formally defined, call this **empirical embedding
perturbation** and claim only measured resistance to A1/A2 under the evaluated
attacker.

Sweep perturbation magnitude and log coarse candidate recall separately from final
source recall. If the relevant source is removed before reranking, later stages
cannot recover it.

## 7. Anonymity set

Let `k` be genuine selected sources and `m` the dispatched set after decoys:

```python
def add_decoys(real, candidates, m, exposure_budget):
    pool = [s for s in candidates if s not in real]
    decoys = topic_stable_sample(pool, m - len(real))
    dispatched = shuffled(real + decoys)
    return enforce_exposure_budget(dispatched, exposure_budget)
```

Design requirements:

- sample decoys from plausible coarse candidates, not the entire source pool;
- shuffle dispatch order;
- compare random and topic-stable decoys under repeated-query intersection;
- pad observable request metadata if timing/size is part of A2;
- enforce maximum fan-out and audit-cost budgets;
- report both route-set privacy and additional query exposure to decoys.

The router constructs the genuine and decoy lists, so the anonymity set does not
hide that distinction from the router itself. It is evaluated against the separate
A2 routing observer.

## 8. TASR and decoy-aware trust

Reuse TASR's evidence feedback through an adapter. Preserve an unmodified TASR
condition as the security baseline before adding any decoy-aware change.

Maintain separate trust components:

```text
trust_signal_i = w1 * evidence_relevance_i
               + w2 * profile_consistency_i
               + w3 * cross_source_agreement_i
               + w4 * provenance_validity_i
               + w5 * service_reliability_i
```

Use a bounded moving update and report every component:

```text
trust_i(t+1) = clip((1-alpha) * trust_i(t) + alpha * signal_i, 0, 1)
```

The central RQ03 experiment tests whether decoys are mistaken for hijackers by
unmodified TASR, and whether exempting decoys leaks their identity. Do not assume
the decoy-aware fix works before running E1-E4.

## 9. Build order

1. Reproduce official RAGRoute on FeB4RAG.
2. Implement the adapter and simple controls.
3. Reproduce A3 and TASR from the routing-hijacking repository.
4. Instrument unprotected A1/A2 leakage.
5. Add empirical query/profile perturbation.
6. Add exposure-constrained anonymity sets.
7. Run privacy-utility-cost sweeps.
8. Run TASR interference experiments.
9. Add MCP transport after the in-process research pipeline is stable.

The first result is a reproduced baseline table and an unprotected leakage number,
not a visual studio or a newly written standard router.
