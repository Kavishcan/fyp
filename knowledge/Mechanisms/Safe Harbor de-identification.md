---
tags: [type/mechanism]
updated: 2026-10-05
---

# Safe Harbor de-identification

Opt-in level `Deidentifier(level="safe_harbor")`; node JSON `"deid_level"`. The default `basic` level is byte-identical, so earlier results hold.

**Adds:**
- labelled account, plan, licence, vehicle, device, record and identity-card numbers (labels never cross a full stop);
- fax numbers;
- dates without a year; month-year reduced to the year;
- institutions;
- residence cues, "in Town, Country", postcodes;
- names without an honorific: person-verb frames, clinician roles, "A. Garcia, MD", header labels, consent statements, appositives;
- uncommon capitalised words, using a PMC-derived common-word list (`privacy/data/common_words.txt.gz`), with eponym, ethnicity and Fig/Table exclusions.

NER runs after the rules at this level. Measured in [[Safe Harbor de-identification results]]. Extends [[Node-side de-identification]].

## Implementation / Experiment Sources

- [backend/privacy/deidentify.py](../../backend/privacy/deidentify.py)
- [backend/eval/build_common_words.py](../../backend/eval/build_common_words.py)
- [backend/nodes/mcp_server.py](../../backend/nodes/mcp_server.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
