---
tags: [type/result]
updated: 2026-10-05
---

# De-identification results

> Superseded as headline by [[Safe Harbor de-identification results]] (held-out benchmark, docs/54). The rows below are the docs/44 `basic` level.

Separate fixture results from public-text alteration and downstream utility.

- Cued identifiers: zero observed leakage in tested fixtures.
- Bare-name fixtures: rules alone miss all; a matching name registry removes them; earlier NER misses about 12.6% versus stock Presidio 8.1%.
- Latest rules+registry public text alteration: about 2.2% nfcorpus and 3.3% scifact; reported recall unchanged in those tests.
- Earlier PMC NER comparison: 11.68% documents altered versus stock Presidio 84.1%.

An alteration is not automatically semantic damage. Public corpora do not provide complete clinical PII labels. Fixing NIC/date/address/relative canaries does not prove no identifiers remain. Disabling de-identification changes every claim.

See [[Node-side de-identification]], [[Presidio NER backend]], [[Dataset strategy]].

## Implementation / Experiment Sources

- [docs/44-node-side-deidentification.md](../../docs/44-node-side-deidentification.md)
- [docs/results/node_deid_20260929-220631.csv](../../docs/results/node_deid_20260929-220631.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
