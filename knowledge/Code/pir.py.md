---
tags: [type/code]
updated: 2026-10-05
---

# pir.py

`backend/privacy/pir.py`:
- `public_matrix`
- `_mul_mod32`: exact float64 BLAS modular product
- `pack`: first-fit column layout, random filler, shuffled columns
- `PIRServer`: hint, answer
- `PIRClient`: query, fetch, recover
- `recommended_tier`

Node side: `PSINode.pir_database`. Device side: `blind_unlock.pir_unlock`. Tests: `tests/test_pir_tier.py`. See [[PIR tier]].

## Implementation / Experiment Sources

- [backend/privacy/pir.py](../../backend/privacy/pir.py)
- [backend/tests/test_pir_tier.py](../../backend/tests/test_pir_tier.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
