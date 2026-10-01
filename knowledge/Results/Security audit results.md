---
tags: [type/result]
updated: 2026-09-30
---

# Security audit results

Audit fixes and regression cases cover scoring-tool embedding theft, gated open-retrieval dumping, restart budget reset, key-file permissions and several signing/trust/de-identification faults.

Remaining limitations include restricted-only public-profile fallback, optional signature enforcement, registry/Sybil trust, cross-node credential sharing, replay, cell churn, metadata-size disclosure and prompt injection. VOPRF/server integrity is not implemented.

A passing regression suite is evidence that specified bugs were checked, not a universal security certification.

See [[Source reconciliation]], [[Threat model]], [[Next steps]].

## Implementation / Experiment Sources

- [docs/49-security-audit.md](../../docs/49-security-audit.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
