---
tags: [type/experiment]
updated: 2026-09-30
---

# MIRAGE

Source: [MIRAGE official repository](https://github.com/gzxiong/MIRAGE).

150 questions, thirty each from BioASQ, MedMCQA, MedQA, MMLU-medical and PubMedQA. Latest answer experiment uses six BEIR stores: three medical and three distractor; local Qwen3.5-9B.

MIRAGE is the QA benchmark, not the actual knowledge corpus. Full MedRAG corpora are not used. Historical eight-node configurations must remain separate.

See [[Answer quality results]], [[Dataset register]].

## Implementation / Experiment Sources

- [backend/eval/run_answer_quality.py](../../backend/eval/run_answer_quality.py)
- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
