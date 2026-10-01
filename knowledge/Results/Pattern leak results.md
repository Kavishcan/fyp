---
tags: [type/result]
updated: 2026-09-30
---

# Pattern leak results

Historical FeB4RAG contact-set attack:
- Cosine/selective routing topic accuracy .496; balanced-origin floor about .077.
- Topic-stable decoys .495: stable cover sets fingerprint topic.
- Random decoys topic .336-.380, but genuine-source identification .667-.692.

These are bounded attacker/configuration results, not a theorem that every possible decoy strategy fails. All-node contact removes this design's query-dependent contact-set signal; broader timing/session channels need separate tests.

See [[Topic inference attack]], [[Session attack]], [[Blind unlock]].

## Implementation / Experiment Sources

- [docs/39-routing-pattern-leakage.md](../../docs/39-routing-pattern-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
