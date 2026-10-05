---
tags: [type/result]
updated: 2026-10-05
---

# Safe Harbor de-identification results

Held-out synthetic benchmark on real PMC prose: 15 Safe Harbor categories, 2,400 injected identifiers per set, dev / test / test2 templates and name pools disjoint.

| Recall | basic + NER (docs/46–53 node setting) | safe_harbor + NER | + registry |
|---|---|---|---|
| **Fresh test2 (run once, headline)** | .459 | **.832** | **.853** |
| Test v1, before its gaps were fixed | .528 | .928 | .975 |

- Test v1 is now 1.000 but is no longer held out. NER (spaCy small) added nothing on test2.
- Remaining test2 misses: "12-Mar-1984", "95 years of age", "SN" serials, unlabelled plates, "St X Hospital, Town", "a Kegalle resident", bare common first names.
- Cost: clean reports altered 13.8% → 28.9% (mostly real dates, places and companies). Centralized PMC MRR .4433 → .4401 (n.s.).

**Never say** "HIPAA compliant" or "PII removed". The next step is a trained clinical de-identifier on a fresh test v3.

See [[Safe Harbor de-identification]], [[De-identification results]], [[Hospital-side PII]].

## Implementation / Experiment Sources

- [docs/54-deidentification-safe-harbor.md](../../docs/54-deidentification-safe-harbor.md)
- [backend/privacy/deidentify.py](../../backend/privacy/deidentify.py)
- [backend/eval/run_deid_benchmark.py](../../backend/eval/run_deid_benchmark.py)
- [docs/results/deid_benchmark_all_20261001-185248.csv](../../docs/results/deid_benchmark_all_20261001-185248.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
