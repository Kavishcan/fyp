---
tags: [type/mechanism, type/building-block]
---

# OPRF (oblivious pseudorandom function)

Client sends B = r·H(x); node returns k·B; client computes r⁻¹·k·B = k·H(x). The node learns nothing about x; the client learns F only for inputs the node evaluated. Ed25519 prime-order group via PyNaCl (`privacy/psi.py`). Basis of [[Labeled PSI]], [[Per-query PSI dispatch]], [[Blind unlock]]. Security: one-more gap DH in the random-oracle model ([[Formal leakage]] claim 3). Privacy Pass uses a verifiable OPRF ([[Anonymous role tokens]], [[Verifiable OPRF]]).
