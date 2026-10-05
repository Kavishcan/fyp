---
tags: [type/experiment]
updated: 2026-10-05
---

# De-identification benchmark

`eval/run_deid_benchmark.py`: fictional identifiers in 15 HIPAA Safe Harbor categories injected into real PMC-Patients case reports, 6 per report, 400 reports per split.

**Splits:**
- dev: rules were written against it;
- test: first held-out run;
- test2: fresh, written after the last fix, run once.

**Leak:** any key string survives as a whole word. Also measured: clean-report alteration on 1,000 untouched reports, and centralized PMC MRR with the corpus de-identified.

Synthetic identifiers, real prose. Real clinical gold standards (PhysioNet, n2c2) are credentialed and were not used.

Results: [[Safe Harbor de-identification results]].

## Implementation / Experiment Sources

- [backend/eval/run_deid_benchmark.py](../../backend/eval/run_deid_benchmark.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
