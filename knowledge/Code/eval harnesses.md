---
tags: [type/code]
updated: 2026-09-30
---

# eval harnesses

Implementation: [evaluation folder](../../backend/eval/).

Current evidence includes run_hyfedrag_compare, bootstrap_compare, run_session_attack, run_answer_quality, run_node_deid and role/transport/privacy harnesses.

The existing [scorecard](../../backend/eval/scorecard.py) assembles older leakage, healthcare, privacy_cases, feb4rag, a3_trust, transport and answer_quality paths. It does not yet unite all current blind partition/session results; its answer rerun settings differ from docs/50.

See [[Results index]], [[Next steps]].
