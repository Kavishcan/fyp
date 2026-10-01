---
tags: [type/mechanism]
updated: 2026-09-30
---

# Role-based access

Node-side allow-lists determine roles and permitted collections. Collection-specific OPRF keys and permitted table/profile views restrict what the client can evaluate and unlock.

The client cannot gain a role merely by claiming it in a request in tested gated configurations. Open nodes and misconfigured publication have different guarantees. Authorisation does not revoke already obtained plaintext or old keys.

See [[RBAC results]], [[Credential gate]], [[Role-scoped publication]].

## Implementation / Experiment Sources

- [backend/privacy/credentials.py](../../backend/privacy/credentials.py)
- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/45-role-based-access.md](../../docs/45-role-based-access.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
