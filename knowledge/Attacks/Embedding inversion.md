---
tags: [type/attack]
updated: 2026-09-30
---

# Embedding inversion

The earlier nearest-neighbour attack recovers dispatched queries from vectors with accuracy 1.000 without noise. At tested noise .10, utility agreement falls to .265 while recovery remains .997.

This establishes a concrete weakness in the tested vector path, not that every embedding is exactly invertible. Blind dispatch avoids sending the query embedding.

See [[v2 vector dispatch]], [[v2 negative results]].

## Implementation / Experiment Sources

- [backend/attacks/a1_inversion.py](../../backend/attacks/a1_inversion.py)
- [docs/32-v2-attack-results.md](../../docs/32-v2-attack-results.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
