---
tags: [type/concept]
updated: 2026-09-30
---

# Inference floor

Use a no-signal baseline appropriate to the label distribution, often majority-class prediction rather than 1/number-of-labels.

PMC per-query topic floors are .239, .210 and .141 for k-means, Dirichlet and random. Session held-out topic floor is about .238. Matching a floor for one attacker does not prove resistance to every possible attacker.

See [[Robustness results]], [[Session attack]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
