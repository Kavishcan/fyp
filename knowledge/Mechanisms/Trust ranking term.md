---
tags: [type/mechanism]
updated: 2026-09-30
---

# Trust ranking term

Older routing experiments add a weighted centred trust term to relevance. At weight .5, attacker selection falls from .520 to .362, with honest recall .694 to .680.

The current blind plan_probes function selects by cosine similarity; this term is not present there. Do not describe the recommended blind router as having the same measured trust defence.

See [[Trust term results]], [[Next steps]].

## Implementation / Experiment Sources

- [backend/router/v2.py](../../backend/router/v2.py)
- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)
- [docs/42-trust-ranking-term.md](../../docs/42-trust-ranking-term.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
