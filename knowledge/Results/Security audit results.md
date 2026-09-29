---
tags: [type/result]
---

# Security audit results (docs/49)

Fixed (each a regression test): [[Scoring tool embedding theft]], [[Open retrieve dump]], [[Budget reset]], world-readable key files, unsigned restricted centroids accepted, trust laundering on re-registration, broken re-registration of signed nodes; plus the de-identification gaps.

Open (stated): [[Cell churn intersection]], self-declared cell labels, shared HMAC client key across nodes, replay within a day, `psi_envelopes` size leak, unauthenticated node registration (Sybil), prompt injection (unmeasured).
