---
tags: [type/result]
updated: 2026-09-30
---

# v2 negative results

Embedding dispatch does not stop the tested inversion attack. Noise and plausibility/trust hard gates lose honest utility before giving useful protection.

The earlier exclusion-only trust path was ineffective against A3; a plausibility setting rejected about 17.7 of 24 honest sources. Later trust-term experiments are separate and still partial.

These negative findings justify changing the design rather than claiming vector dispatch private.

See [[Embedding inversion]], [[Trust term results]].

## Implementation / Experiment Sources

- [docs/32-v2-attack-results.md](../../docs/32-v2-attack-results.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
