---
tags: [type/attack]
updated: 2026-09-30
---

# Scoring tool embedding theft

Chosen inputs to the experimental scoring endpoint recovered all tested embeddings in three unauthenticated requests, including restricted rows.

Audit fixes disable that tool by default/on gated nodes and limit enabled access to public data. Do not treat this experimental endpoint as a secure private-scoring implementation.

See [[Paillier encrypted scoring]], [[Security audit results]].

## Implementation / Experiment Sources

- [backend/privacy/encrypted_scoring.py](../../backend/privacy/encrypted_scoring.py)
- [docs/49-security-audit.md](../../docs/49-security-audit.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
