---
tags: [type/mechanism]
updated: 2026-09-30
---

# Node-side de-identification

When enabled, de-identification runs before embedding, profiles and table publication. Layers include known name/ID registries, structured patterns, cued-name rules and optional NER.

Nodes can be configured with de-identification disabled. Unregistered names, quasi-identifiers and semantic clues remain risks. Test-case fixes do not establish clinical anonymisation or legal compliance.

Measure identifier misses, unrelated text alterations and downstream retrieval separately. See [[De-identification results]], [[Presidio NER backend]].

## Implementation / Experiment Sources

- [backend/privacy/deidentify.py](../../backend/privacy/deidentify.py)
- [backend/nodes/simulator.py](../../backend/nodes/simulator.py)
- [docs/44-node-side-deidentification.md](../../docs/44-node-side-deidentification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
