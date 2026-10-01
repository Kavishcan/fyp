---
tags: [type/experiment]
updated: 2026-09-30
---

# PMC-Patients

Official public dataset: [PMC-Patients on Hugging Face](https://huggingface.co/datasets/zhengyun21/PMC-Patients).

Current study uses 5,000 public case-report summaries, 986 patient-to-patient retrieval queries and eight simulated nodes. Cross-article relevance is used. This is not live clinical patient data or eight real hospitals.

The same corpus is partitioned three ways for [[Hospital splits]]. Source text can remain sensitive despite being publicly published; fictional canaries supply separate identifier ground truth.

See [[Robustness results]], [[Dataset register]].

## Implementation / Experiment Sources

- [backend/eval/run_hyfedrag_compare.py](../../backend/eval/run_hyfedrag_compare.py)
- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
