---
tags: [type/mechanism]
---

# Node-side de-identification (`privacy/deidentify.py`, docs/44)

Runs once at load, before embedding, profile, tables and serving — no path from raw text to the wire. Layers: registry (institution's names/ids, incl. surname-first and initialled forms) → institution id formats → structured rules (email, URL, IP, labelled ids, NIC, passports, SSN, card, dates in many formats, ages over 89, phones, addresses) → cued names (honorifics, "my name is", relatives/carers) → optional [[Presidio NER backend]].

**Mitigated, not solved:** cued/registered identifiers 0% leaked; ~13% of uncued unregistered names missed even with NER; quasi-identifiers out of reach. Results: [[De-identification results]].
