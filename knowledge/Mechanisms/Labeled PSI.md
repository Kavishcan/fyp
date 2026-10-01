---
tags: [type/mechanism]
updated: 2026-09-30
---

# Labeled PSI

Labelled private lookup associates permitted payloads with privately queried items. In this application an item is a cluster identifier; its label contains encrypted passages and embeddings.

The project uses a group-OPRF/table design, not Chen-Laine-Rindal's FHE protocol. One label can contain many records and chunks. Do not describe one evaluation as exactly one document disclosed.

See [[Chen-Laine-Rindal 2018]], [[Blind unlock]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
