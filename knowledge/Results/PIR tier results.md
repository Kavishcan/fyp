---
tags: [type/result]
updated: 2026-10-05
---

# PIR tier results

Large-hospital tier ([[PIR tier]]). Blind unlock's per-question cost does not grow with corpus size. The one-time table download does: about 1.1× the text.

| Test | Tier 1 (download) | Tier 2 (PIR) |
|---|---|---|
| PMC, 986 questions, P=8 hybrid | MRR .5062 | MRR .5062; identical top-10 on 100% of questions |
| PMC offline | 11.3 MB | 538 MB of hints (wrong tier for small hospitals) |
| 1 GB table, measured | 1 GB | 67 MB hint; 2.5 MB per question; 0.6 s hospital time |
| 2 GB table, measured | 2 GB | 135 MB hint; 3.1 MB per question; 1.2 s hospital time |
| 100 GB of text, **extrapolated** | ~110 GB | ~1.2 GB once; ~22 MB per question; ~66 s of one core per question |

Hospital throughput: 13–14 GB/s of (table × queries) on one core, using exact 16-bit-split float64 matrix maths.

**Limits:**
- numpy prototype, not wired into MCP or the client.
- Public collection only.
- Cover rounds cost a full scan per tick.
- SimplePIR parameters were not re-estimated.

## Implementation / Experiment Sources

- [docs/55-large-hospitals-pir-tier.md](../../docs/55-large-hospitals-pir-tier.md)
- [backend/privacy/pir.py](../../backend/privacy/pir.py)
- [backend/eval/run_pir_tier.py](../../backend/eval/run_pir_tier.py)
- [docs/results/pir_tier_20261001-210828.csv](../../docs/results/pir_tier_20261001-210828.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
