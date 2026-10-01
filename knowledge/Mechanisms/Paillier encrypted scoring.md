---
tags: [type/mechanism]
updated: 2026-09-30
---

# Paillier encrypted scoring

Experimental encrypted in-cluster scoring is not the recommended path. The earlier benchmark reported high key-generation cost and small row limits.

An exposed chosen-input scoring endpoint leaked embeddings; audit fixes disable it by default and on gated nodes, restricting enabled use to public data. Correct encrypted arithmetic alone does not secure the endpoint.

See [[Scoring tool embedding theft]], [[Security audit results]].

## Implementation / Experiment Sources

- [backend/privacy/encrypted_scoring.py](../../backend/privacy/encrypted_scoring.py)
- [docs/49-security-audit.md](../../docs/49-security-audit.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
