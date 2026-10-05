---
tags: [type/code]
updated: 2026-10-05
---

# external baselines

`backend/baselines/external_fedrag.py`:
- `RAGRouteRouter`: copied CorpusRoutingNN plus its training loop;
- `FlowerClientIndex`: FAISS IVF L2;
- `flower_merge_documents`: RRF.

Harness: `eval/run_external_baselines.py`. Run it with `OMP_NUM_THREADS=1` on macOS (FAISS and torch OpenMP clash). See [[External baselines results]].

## Implementation / Experiment Sources

- [backend/baselines/external_fedrag.py](../../backend/baselines/external_fedrag.py)
- [backend/eval/run_external_baselines.py](../../backend/eval/run_external_baselines.py)
- [backend/tests/test_external_baselines.py](../../backend/tests/test_external_baselines.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
