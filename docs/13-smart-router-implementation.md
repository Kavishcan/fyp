# Smart router: first implementation

This is an implementation specification, not a literature summary or a claim
of proven novelty. It follows the user's revised direction: build an independent
router and compare it with published routing systems.

## In plain language

1. Embed the question in the same space as the registered source profiles.
2. Reject sources without permission or sufficient coordinator-observed trust.
3. Estimate each source's relevance from its profile.
4. Select the useful, affordable source with the greatest gain per exposure cost.
5. Reduce the estimated value of sources whose profiles overlap selected ones.
6. Repeat until nothing useful fits, the fan-out cap is reached, or candidates end.
7. Only then contact selected nodes through MCP or in-process retrieval.
8. Independently embed returned passages and update profile-consistency trust.

It does not contact all nodes to calculate routing relevance. It reads their
already-registered profiles. There are no decoys or routing-embedding noise in
this mode, and no automatic fallback contacts after a source fails.

## Exact decision rule

For source i, with unit-normalized query q and source centroids c:

```text
r_i = mean(max(0, cosine(q, c)))                # max is an explicit ablation
t_i = max(0, observed_trust_i - u / sqrt(n_i + 1))
d_i(S) = max(0, cosine(c_i, c_j)) over centroids of sources j already in S
g_i(S) = r_i * t_i * (1 - rho * d_i(S))

eligible: authorized_i and t_i >= minimum_trust
useful:   g_i(S) > minimum_gain
affordable: sum(cost_j for j in S) + cost_i <= budget

next source = argmax g_i(S) / cost_i among eligible, useful, affordable sources
```

Ties use gain, then source ID, so input registration order does not change the
result. Defaults: u=0.1, rho=1, minimum_gain=0.05, minimum_trust=0. These are
provisional engineering settings, not empirically optimal values. Mean/max
aggregation and rho/u/gain thresholds require validation and ablations.

The redundancy score is a coarse profile-overlap proxy, not verified answer
coverage. This is a greedy heuristic; it has no claimed optimality guarantee.
In particular, it may stop early on near-duplicate profiles even when those
sources hold different useful documents. That is an evaluation question.

## Exposure and authorization

The default cost is one unit for every contacted source. Thus budget=2 means
at most two recipients, regardless of a source's relevance or trust. A trusted
coordinator may configure different positive costs through
`AppState.source_exposure_costs`. Costs cannot be self-advertised by a node or
set in a query payload. They are not learned privacy-leakage probabilities.

All genuine contacts count; there is no exemption for a high-relevance source.
The exposure budget is per query, not a cumulative cross-query privacy budget.
Failed retrievals still count, since the query may already have reached them.
No evidence means no generation call. The trace reports selection/reservation
cost, not packet-level network instrumentation.

In the demo, sources with no policy labels are public. Every label on a
restricted source must be in the coordinator's `allowed_policy_labels` set.
This is a fail-closed selection hook, not multi-user authentication, signed
policy enforcement or production access control. Registration and the legacy
API are not secured. Do not deploy this prototype with private documents.

## Trust observations

The smart mode ignores source-advertised trust and remote retrieval scores
when updating its own trust. It re-embeds returned passages locally and uses
mean best-centroid similarity, clipped to [0, 1], as profile-consistency evidence.
Empty/failed retrieval gives zero. Each query counts as one observation:

```text
new_trust = (old_trust * (n + 2) + consistency) / (n + 3)
new_n = n + 1
```

The initial trust is 0.5 with a two-observation neutral prior. Republishing a
profile or removing a source clears smart-mode observations. Legacy-mode trust
is separate, so the two mechanisms do not silently share observations.

Consistency is not honesty: a malicious source can return matching bait text;
re-registration can escape negative history; signatures and identity binding
are not implemented. A full profile-hijacking defence remains unproven.

## Run it

From the repository root, using the existing environment:

```sh
.venv/bin/uvicorn api.app:app --app-dir backend --port 8001
```

Register a harmless local demo source (omit this if suitable nodes are loaded):

```sh
curl -X POST http://localhost:8001/nodes/register \
  -H 'Content-Type: application/json' \
  -d '{"node_id":"demo-medical","documents":["Research on COVID treatment and recovery."]}'
```

Call the independent smart router:

```sh
curl -X POST http://localhost:8001/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"COVID treatment research","routing_mode":"smart","max_nodes":5,"exposure_budget":2,"minimum_gain":0.05,"minimum_trust":0,"aggregation":"mean"}'
```

`genuine_k` is a legacy-only parameter. Smart mode adapts the number of sources;
`max_nodes` is a ceiling, not a target. If omitted, budget defaults to max_nodes.
`sigma` must be zero in smart mode. `routing_mode` defaults to `legacy` to
preserve the dashboard's previous behaviour and existing control experiments.
No new dependencies, dataset downloads or external API calls are required by
the algorithm. The existing optional generator still follows backend settings;
it is not made privacy-preserving by this router.

The response and `/audit/{query_id}` include `routing_details`: config, selected
sources, costs, relevance, uncertainty-adjusted trust, redundancy, marginal
gain, exclusions, routing latency, stop reason and retrieval failures. Audit
logs expose route identities and must remain in a trusted environment.

## Files and tests

- `backend/router/smart.py`: pure selector plus coordinator trust observations.
- `backend/api/state.py`: optional smart-mode execution before node dispatch.
- `backend/api/schemas.py`: validated request parameters and audit response.
- `backend/tests/test_smart_router.py`: deterministic synthetic algorithm tests.
- `backend/tests/test_api.py`: budget, access, audit, failure and integration tests.

```sh
.venv/bin/pytest -q
```

The 1,000-profile test checks an in-memory selection invariant on synthetic
vectors. It is not evidence of 1,000 real MCP servers or a scalability result.

## Still required for the research

- Use semantic embeddings consistently across queries and published profiles;
  the current live API/MCP demo still uses hashing, explicitly labelled in logs.
- Compare broadcast, cosine top-k, official RAGRoute and this router on identical
  source sets and held-out queries. Preserve upstream behaviour in baselines.
- Test no-trust (equal trust, u=0), no-redundancy (rho=0), loose-budget and fixed-k
  conditions. Select hyperparameters on validation data, not test results.
- Evaluate source/retrieval recall, answer quality, actual contact counts,
  communication, latency, routing-pattern inference and profile manipulation.
- Separate synthetic partitions from real institutions and real MCP transport
  from in-memory scaling. Include legitimate new-source cold-start tests.
- Assess manipulated profiles, matching bait passages, source churn and trust
  feedback loops before calling this mechanism attack-resilient.

Raw queries are still visible to the coordinator and contacted nodes. A smaller
recipient set is exposure reduction, not query secrecy, source anonymity,
differential privacy or an end-to-end privacy guarantee.
