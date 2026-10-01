---
tags: [hub, research-support]
updated: 2026-09-30
---

# Source Reconciliation

Reviewed 2026-09-30 against code commit 67796309ed20a83f7586965808bad15f2770b368 and the five live research tabs. The Google Sheet was read, not edited.

| Source Disagreement | Current Interpretation |
|---|---|
| Sheet gap plan: select 3-10 sources across 30-1,000 clients | Current blind mode contacts every enrolled node with P points. Selective older modes are controls |
| Sheet: trust-aware router proposed | Blind cluster planner is cosine-only; older trust-term results are not a blind defence |
| Dataset strategy: blind answer/significance/split experiments pending | Saved docs/50 experiments now exist; results below remain limited to those configurations |
| Sheet MIRAGE federation: eight nodes | Latest docs/50 answer run uses six nodes; older docs/38 used a different configuration |
| Sheet themes cover only papers 1-53 | [[Literature themes]] includes all 63 imported papers |
| Old vault: rotation revokes cached records | False for saved old unlock outputs, keys or plaintext; rotation only controls future evaluations |
| Old vault: cover traffic hides request time universally | Finite scheduling tested; session start/stop, late rounds and device/transport side channels remain |
| docs/51: B evaluations imply at most B envelopes | Must account for permitted collections, multi-chunk labels and many records per cluster; do not assert B-record disclosure |
| Old vault: no public profile can expose restricted structure | Restricted-only nodes fall back to all documents in public_view; this remains an open disclosure issue |
| Old vault: signed connection guaranteed | Registry default accepts unsigned profiles; signature validity does not establish source identity or truthfulness |
| Old vault: 1,000-node scalability / full unified evaluator | Blind scale extrapolation only; scorecard omits some latest blind/split/session results |
| Historical dense float16 values mixed with int8 cache size | [[Blind unlock results]] separates initial and int8 runs |
| Nonsignificant k-means comparison called equivalent | p=.08 is not proof of equivalence or noninferiority |
| Text alteration called damage | Alteration counts do not directly measure semantic damage or identifier recall |
| De-id canary misses claimed fully fixed | Regression fixes are limited examples, not complete clinical validation |

**Source hierarchy:** code for implemented behaviour; saved per-query results for measured outcomes; experiment docs for setup; primary papers for literature; worksheet comments for working interpretation. Disagreements stay visible rather than being silently merged.

## Implementation / Experiment Sources

- [backend/router/registry.py](../backend/router/registry.py)
- [backend/nodes/simulator.py](../backend/nodes/simulator.py)
- [backend/privacy/blind_unlock.py](../backend/privacy/blind_unlock.py)
- [backend/eval/scorecard.py](../backend/eval/scorecard.py)
- [docs/50-robustness-significance-sessions.md](../docs/50-robustness-significance-sessions.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
