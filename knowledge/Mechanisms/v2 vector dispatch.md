---
tags: [type/mechanism]
updated: 2026-09-30
---

# v2 vector dispatch

Version-two dispatch replaces query text with an embedding and adds local routing/signing/budget components. The tested embedding inversion succeeds, so this is not query secrecy.

Keep it as a negative control showing that hiding literal text is insufficient. See [[Embedding inversion]], [[v2 negative results]].

## Implementation / Experiment Sources

- [backend/router/v2.py](../../backend/router/v2.py)
- [docs/30-privacy-pipeline-v2.md](../../docs/30-privacy-pipeline-v2.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
