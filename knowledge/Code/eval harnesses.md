---
tags: [type/code]
updated: 2026-10-05
---

# eval harnesses

Implementation: [evaluation folder](../../backend/eval/).

Current evidence includes run_hyfedrag_compare, bootstrap_compare, run_session_attack, run_node_deid and role/transport/privacy harnesses, plus (docs/53–56) run_external_baselines ([[External baselines results]]), run_deid_benchmark and build_common_words ([[De-identification benchmark]]), run_pir_tier ([[PIR tier results]]) and run_release ([[Release results]]). run_answer_quality is out of scope since 2026-10-02.

The existing [scorecard](../../backend/eval/scorecard.py) assembles older leakage, healthcare, privacy_cases, feb4rag, a3_trust, transport and answer_quality paths. It does not yet unite all current blind partition/session results; its answer rerun settings differ from docs/50.

See [[Results index]], [[Next steps]].
