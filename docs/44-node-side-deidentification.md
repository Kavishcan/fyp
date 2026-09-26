# Node-side de-identification: does PII leave a hospital node?

## Verdict

**Before this change, every node served raw PII.** Redaction ran only inside
`embed_documents`, so the vectors and centroids were clean — but the text the
node actually *serves* (legacy/smart/v2 retrieve results and every PSI
envelope) was the raw document. On a corpus with injected patient records, a
credentialed client recovered **100% of names, record numbers, dates of
birth, phones and emails**. PSI hid the *query* from the node; nothing hid
the *patients* from the client.

**Now the node de-identifies its documents once, at load, before anything
else sees them** (`privacy/deidentify.py`, called from `nodes/mcp_server` and
`nodes/simulator`). Embeddings, the public profile (centroids, description,
topics), the PSI cluster table, every envelope and every retrieve result are
built from the same redacted text. There is no path from the raw document to
the wire. Measured through the real serving paths:

| Canary records in node documents | Condition | Name | MRN | DOB | Phone | Email |
|---|---|---:|---:|---:|---:|---:|
| with a cue ("Patient Rahul Menon, MRN …") | none (before) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| | **rules** | **0.000** | **0.000** | **0.000** | **0.000** | **0.000** |
| bare ("Rahul Menon was admitted …") | none (before) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| | rules | **1.000** | 0.000 | 0.000 | 0.000 | 0.000 |
| | **rules + registry** | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 |

(fraction leaked to a fully authorised client that opens every envelope,
reads every retrievable document and the public profile; 6 nodes × 60
nfcorpus documents, 30% carrying a fictional record)

The one gap is stated in the table: **a bare name with no cue is not
detectable by rules.** The node's own registry of its patients' and staff
names — which every hospital has — closes it. A validated NER-based tool
(Presidio, Philter) plugs in at the same point (`Deidentifier.backend`) and
was not installed or measured here.

**Cost on clean text is zero on retrieval.** On 2,000-document nfcorpus and
scifact pools with no injected PII, 1.2% and 2.2% of documents were altered
(URLs, dates, author names after "Dr", a few emails), and dense recall@10 of
the judged queries was **unchanged** (0.800 → 0.800, 0.850 → 0.850).

On the project's 200 synthetic privacy cases the old embed-only regex
removed 1 of 3 value types (email); the new rules remove all three (name,
email, reference id). Those cases put every name after "My name is", so
this is a cued-name result, not a general one — part B above is the honest
test.

## What the node now does, in order

```text
raw documents  (never leave the process, never indexed)
  → Deidentifier: registry (institution's names/ids) → institution id formats
      → email, URL, IP, labelled ids (MRN/NHS/SSN/ID/Record), SSN, card (Luhn),
        dates, phones → names after a cue (Mr/Mrs/Dr/Prof/Patient, "my name is")
  → embed (same routing model as the federation)
  → signed profile: centroids + cluster centroids + description/topics
      (placeholders stripped so "[NAME]" never becomes a topic)
  → cluster table → AEAD envelopes          (PSI path)
  → local index                             (legacy/smart/v2 retrieve)
```

Node configuration (in the node's data file): `known_identifiers` (the
registry), `id_patterns` (its own record formats, e.g. `"\\bTEST-\\d{4}\\b"`),
`"deidentify": false` to opt out explicitly (tests use it to reproduce the
old leak).

Deliberately absent: a bare `ABC-123` identifier rule. In biomedical text
that shape is a compound, drug or cell line (PCB-153, MB-231, GS-9620) far
more often than a person; the first version redacted 129 of them across the
two pools. An institution adds its real record format through `id_patterns`.

## What this does not establish

- Clinical-grade de-identification. Rules + registry miss free-text
  addresses, uncued names outside the registry, relatives' names, and
  quasi-identifiers (rare diagnosis + age + town). HIPAA Safe Harbor lists 18
  identifier types; this covers the structured ones and cued/registered
  names.
- Anything about re-identification from de-identified passages.
- That the ~36 passages per contact (docs/35) are harmless — they are now
  de-identified passages, which is the point, but still over-disclosure.
- Real patient data. Every value here is fictional (`example.invalid`,
  generated names).

## Reproduce

```
python -m eval.run_node_deid
```

Tests: `tests/test_deidentify.py` — each identifier type, clinical and
scientific text left untouched, registry needed for bare names, no serving
path returns raw PII (simulated and real MCP), opting out reproduces the old
leak. Test counts are not a de-identification validation.
