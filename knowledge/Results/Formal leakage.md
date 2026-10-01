---
tags: [type/result]
updated: 2026-09-30
---

# Formal leakage

Treat docs/51 as the project's security argument, not an externally reviewed protocol proof.

| View | Intended Protection | Still Visible / Unsettled |
|---|---|---|
| Valid node input points | Fresh blinding hides cluster input; real and dummy points match in the intended group model | Credential, collections, P, timing, refusals |
| Contact-set observer | Every enrolled node is contacted | Session participation, delays, failures, setup size |
| Authorised client | Only evaluated permitted label keys are obtained under assumptions | Many records/chunks per label; saved old outputs; collusion |

**Corrections to stronger earlier wording**
- B charged point evaluations do not necessarily equal B envelopes/documents: each permitted collection can return outputs and a label can hold many chunks/records.
- Key rotation cannot revoke saved outputs or plaintext.
- A finite cover schedule does not establish universal timing secrecy.
- Arbitrary malicious-server integrity, side channels and implementation compositional security remain open.

See [[Threat model]], [[OPRF]], [[Source reconciliation]].

## Implementation / Experiment Sources

- [docs/51-formal-leakage.md](../../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
