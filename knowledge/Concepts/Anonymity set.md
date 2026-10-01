---
tags: [type/concept]
updated: 2026-09-30
---

# Anonymity set

The set of plausible relevant sources depends on what the attacker observes and already knows. In this design, uniform all-node contacts avoid narrowing relevance through the contact set itself.

This is not stated as a universal PIR lower bound. Grouped contacts, changing membership or external information can still narrow the set.

See [[Anonymity cells]], [[Blind unlock]], [[Threat model]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
