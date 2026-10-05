---
tags: [type/literature]
updated: 2026-10-05
---

# Flower FedRAG

The `fedrag` example of the Flower framework (Apache-2.0).

**Design:**
- The server sends the question text to every client.
- Each client embeds it (all-MiniLM-L6-v2) and searches FAISS IndexIVFFlat (L2, nlist √N, default nprobe 1).
- The server merges with reciprocal rank fusion (k = 60).

**Reproduced in [[External baselines results]]:**
- merge function and client index copied;
- k-nn 8 → 10 so every system scores the same top-10;
- no LLM evaluation;
- MedRAG corpora replaced by PMC.

Low PMC MRR (.26) is partly its defaults (MiniLM truncation, IVF nprobe 1); `flower_fedrag_bge` separates the embedder.

## Implementation / Experiment Sources

- [backend/baselines/external_fedrag.py](../../backend/baselines/external_fedrag.py)
- [docs/53-external-baselines-cost.md](../../docs/53-external-baselines-cost.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
