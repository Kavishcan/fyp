---
tags: [type/result]
updated: 2026-09-30
---

# Answer quality results

Latest archived run: MIRAGE 150 questions (30 per subset), six BEIR sources, local Qwen3.5-9B.

| Condition | Accuracy | Comparison |
|---|---|---|
| Closed-book | .547 | Reference |
| PSI+cells | .593 | Gain .047, CI [-.007,.100], p=.10 |
| Blind dense | .613 | Gain .067, CI [.007,.133], p=.035 vs closed-book |
| Blind hybrid | .573 | Difference -.040 vs blind dense, p=.07 |
| Broadcast rerun | .540 | Machine-contention caveat; avoid superiority conclusion |

Blind dense versus PSI+cells: +.020, p=.34. This establishes neither superiority nor equivalence. One model and 150 questions limit generality.

Historical docs/38 reported .627 in a different eight-node run. Do not combine that figure with this six-node comparison. Retrieval MRR and answer accuracy are different endpoints.

See [[MIRAGE]], [[Paired bootstrap]], [[Claims ledger]].

## Implementation / Experiment Sources

- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)
- [docs/results/answer_quality_20260929-201656.csv](../../docs/results/answer_quality_20260929-201656.csv)
- [docs/results/answer_quality_20260929-201656_per_question.csv](../../docs/results/answer_quality_20260929-201656_per_question.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
