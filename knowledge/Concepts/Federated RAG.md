---
tags: [type/concept]
updated: 2026-09-30
---

# Federated RAG

RAG over knowledge held by multiple owners can federate model training, query-time retrieval, or both. This project focuses on query-time retrieval; it does not train a new router model.

Owners keep control of current evaluation keys, roles and budgets while clients cache encrypted permitted data. Saved authorised outputs/plaintext cannot be retroactively revoked.

See [[Source routing]], [[Key epochs and rotation]], FedE4RAG (P03 in [[Paper register]]).

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
