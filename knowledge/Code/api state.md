---
tags: [type/code]
updated: 2026-09-30
---

# api state

Implementation: [state.py](../../backend/api/state.py).

The Studio coordinator handles modes, blind retrieval and local/API ranking. It therefore sees raw query text in the demonstration path, even if nodes receive only blinded points.

Do not equate this hosted API boundary with standalone user-only query visibility. Record routing mode and generator settings in every run.

See [[studio]], [[Device]], [[Threat model]].
