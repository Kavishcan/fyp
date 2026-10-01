---
tags: [type/attack]
updated: 2026-09-30
---

# Topic inference attack

A classifier learns from labelled multi-hot contact sets and predicts query topic on held-out cases. Compare to majority-class floor and disclose the split/training procedure.

Historical FeB4RAG selective accuracy .496 versus about .077; PMC cosine .318 versus .239. All-node blind sets lack per-query variation for this attacker.

Floor-level accuracy is not a universal theorem against attackers with timing, payload or external information.

See [[Pattern leak results]], [[Session attack]].

## Implementation / Experiment Sources

- [backend/attacks/a2_topic_inference.py](../../backend/attacks/a2_topic_inference.py)
- [docs/39-routing-pattern-leakage.md](../../docs/39-routing-pattern-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
