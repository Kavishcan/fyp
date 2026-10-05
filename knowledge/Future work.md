---
tags: [hub]
updated: 2026-10-05
---

# Future Work

[[Next steps]] distinguishes urgent correctness/evaluation work from longer-term extensions.

Longer-term candidates:
- [[Anonymous role tokens]] for credential unlinkability.
- [[Verifiable OPRF]] for consistent server evaluation.
- Delegated (threshold) OPRF key servers: contact 2–3 servers instead of every hospital without a pattern leak.
- Two-level unlock: embeddings first, text only for the top-k (cuts G3 release).
- [[PIR tier]] in the deployed client; two-server or offline/online PIR for cheaper hospital scans.
- Trained clinical de-identifier (~440 MB) evaluated on a fresh test set; credentialed clinical gold standards if access is granted.
- Per-document private fetching/scoring rather than opening clusters.
- Explicit source metadata protection rather than public centroid heuristics.
- Larger real-network federations, changing membership and concurrent users.
- Clinical expert-reviewed de-identification and multilingual identifiers.
- Key lifecycle, backup and cache-retention policy.

Not implemented, not part of claimed POC results. Existing source-control, side-channel and malicious-content limitations should remain visible.
