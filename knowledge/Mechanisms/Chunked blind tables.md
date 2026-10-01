---
tags: [type/mechanism]
updated: 2026-09-30
---

# Chunked blind tables

Each cluster payload is compressed and split into padded 16 KB encrypted chunks indexed by derived tags. Clients download the full permitted table, rather than query-dependent partial chunks.

The current int8 k-means run reports 15,037,120 cached bytes across eight nodes. Historical padded/float16 layouts were roughly 83-86 MB. Total collection size, number of chunks and opened-label sizes remain observable; padding does not make all metadata secret.

See [[Blind unlock results]], [[Scaling of blind unlock]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/47-blind-unlock.md](../../docs/47-blind-unlock.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
