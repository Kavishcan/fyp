# Routing mechanisms

## Current proposed router

smart.py contains the independent training-free SmartRouter, SmartConfig,
SourceEvidence, SmartDecision and EvidenceTrust.

It greedily selects useful sources under a strict contact-exposure budget,
using relevance, uncertainty-adjusted trust and profile overlap. It can stop
before the cap or select nothing. It has no decoys or query perturbation.
Coordinator-observed passage consistency is a heuristic, not verified honesty.

See [design](../../docs/04-router-design.md) and
[usage](../../docs/13-smart-router-implementation.md).

## Preserved legacy path

- registry.py: shared profile registry; version checks exist, signatures are a placeholder.
- pipeline.py: cosine/baseline shortlist, weighted rerank and decoys.
- exposure.py: legacy proxy-cost helper; genuine sources can exceed its budget.
- perturb.py: empirical Gaussian perturbation, not automatically DP.
- anonymity.py: legacy deterministic/topic-stable decoy construction.
- trust.py: local BoundedTrustUpdate; not the upstream TASR implementation.

Legacy remains the live dashboard/API default. Smart mode is explicit through
routing_mode=smart. Keep experiment identities separate; legacy results do not
evaluate the new greedy selector.
