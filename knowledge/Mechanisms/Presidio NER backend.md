---
tags: [type/mechanism]
updated: 2026-09-30
---

# Presidio NER backend

Optional PERSON-focused spaCy/Presidio processing complements rules and known-identifier registries. Earlier bare-name canaries missed about 12.6% versus stock Presidio's 8.1%, while altering substantially less public text.

That is a tested trade-off, not uniformly better name detection. The exact registry and NER configuration determine the result. Clinical validation, multilingual identifiers and quasi-identifiers remain open.

See [[De-identification results]].

## Implementation / Experiment Sources

- [backend/privacy/deidentify.py](../../backend/privacy/deidentify.py)
- [docs/44-node-side-deidentification.md](../../docs/44-node-side-deidentification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
