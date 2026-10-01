# De-identification: Safe Harbor level and a held-out benchmark

## Verdict

| | Before (docs/44, the node setting in docs/46–53) | Now (`level="safe_harbor"` + NER) | + the hospital's registry |
|---|---|---|---|
| Held-out recall, 2,400 injected identifiers, 15 categories | **0.528** | **0.928** | **0.975** |
| Categories fully missed | 8 (accounts, licences, vehicles, devices, postcodes, residence, partial dates, institutions) | 0 | 0 |
| Clean PMC reports altered | 13.8% | 24.2% (most of the rise is real dates and hospital names, see below) | — |
| Dense retrieval (PMC, centralized MRR; raw 0.4433) | 0.4433 | 0.4404 (−0.003, 95% CI [−0.007, +0.001], p = 0.12, n.s.) | — |
| Cost | 46 ms per document (NER) | 46 ms per document | 47 ms |

**Safe sentence:** "Node-side de-identification (rules for the HIPAA Safe
Harbor identifier types + full-name NER + the hospital's registry) removed
97.5% of 2,400 injected identifiers on held-out templates and names (92.8%
without a registry). It is a synthetic benchmark on real case-report text,
not a validated clinical de-identifier."

Do not say "PII is removed" or "HIPAA compliant". Safe Harbor also
requires no actual knowledge of re-identifiability, and quasi-identifiers
(rare disease + age + town) are not handled.

## What changed

`privacy/deidentify.Deidentifier(level="safe_harbor")` is opt-in. The
default (`"basic"`) is byte-identical, so every earlier measured number is
unchanged. Nodes select it with `"deid_level": "safe_harbor"` in the node
JSON (nodes/mcp_server) or `deid_level=` (nodes/simulator).

| Safe Harbor identifier | Basic | Safe-harbor level adds |
|---|---|---|
| Names | honorific / self-identification / relative cues; NER (full names); registry | names directly followed by what only a person does in a case report (", a 45-year-old", "was admitted", "'s mother"); clinician roles (attending, consultant, seen by, signed); "A. Garcia, MD"; header labels ("NAME: RAHUL MENON", "Patient: …", surname-first); consent statements ("consent was obtained from …") |
| Geographic subdivisions | street addresses | residence cues (resident of, lives in, born in, from the village of …), "in Town, Country", UK / US postcodes, labelled ZIP |
| Dates | full dates | dates without a year ("3 March", "March 3rd", "on 12/03"), two-digit-year dates, **month-year reduced to the year** ("March 2019" → "[DATE] 2019"; Safe Harbor allows the year) |
| Ages over 89 | yes | — |
| Phone, fax | phone | labelled fax |
| Email, URL, IP, SSN, MRN, national IDs | yes | — |
| Health-plan, account, certificate/licence, vehicle, device numbers | only if labelled ID/MRN | any value with ≥ 3 digits after a label (policy, member, account, licence, registration, plate, VIN, serial, S/N, …) |
| Institutions (i2b2 category) | — | "… Hospital / Medical Center / Clinic / Infirmary …" |
| Biometrics, photos | not text | — |

With the safe-harbor level, NER runs after the rules, so it cannot split an
address ("Temple Road" tagged as a person left the town behind in the dev
run). In the basic level the order is unchanged.

## The benchmark (`backend/eval/run_deid_benchmark.py`)

No public clinical de-identification corpus is available without a data
use agreement (i2b2/n2c2, PhysioNet). So fictional identifiers are injected
into **real clinical prose**: PMC-Patients case reports, 6 per report, 400
reports per split.

- **Held out:** every category has DEV and TEST templates with different surface forms. Name, town, street and saint pools are disjoint between the halves.
- The rules were written against DEV only. False positives were inspected on a separate clean slice.
- TEST was run once; its misses were **not** fixed (see "Known gaps").
- Both halves were written by the same author. It is not an independent annotation.

How leaks are counted:
- **Leak:** any key string of the injection survives as a whole word. Keys are the value; each name word; the longest digit run of a number; the street and town of an address.
- **Registry condition:** the node's registry holds its own patients' and clinicians' full names and record numbers. Relatives are not in it.

## Results

### Held-out TEST split (2,400 identifiers)

Categories not listed under misses are at 1.00.

| Condition | Recall | Misses (recall) |
|---|---|---|
| basic (docs/44 rules) | 0.455 | account 0, device 0, licence 0, vehicle 0, postcode 0, residence 0, partial dates 0, institution 0, patient name 0.16, clinician 0.33, MRN 0.53, relative 0.90, address 0.92, SSN/NIC 0.91 |
| basic + NER (docs/46–53 node setting) | 0.528 | same zeros (institution 0.04), patient name 0.64, clinician 0.66, address 0.76, MRN 0.53 |
| safe_harbor | 0.906 | patient name 0.55, MRN 0.53, residence 0.72, SSN/NIC 0.91, relative 0.98, address 0.99 |
| **safe_harbor + NER** | **0.928** | patient name 0.75, MRN 0.53, residence 0.72, SSN/NIC 0.91, relative 0.98, address 0.99 |
| **safe_harbor + NER + registry** | **0.975** | residence 0.72, SSN/NIC 0.91, address 0.99 |

DEV split, for the record: 0.618 → 1.000. It was tuned on, so it is not evidence.

### Cost on 1,000 untouched PMC case reports

| Condition | Reports altered | Placeholders / 1,000 words | Main placeholders |
|---|---|---|---|
| basic | 4.5% | 0.31 | DATE 80 |
| basic + NER | 13.8% | 0.62 | NAME 124, DATE 80 |
| safe_harbor | 16.7% | 1.17 | DATE 315, ORGANIZATION 82, LOCATION 16 |
| safe_harbor + NER | 24.2% | 1.48 | DATE 315, NAME 125, ORGANIZATION 82 |

Most of the rise is not a false positive. Journals leave in month-year
dates ("In March 2015 …"), treatment dates and real hospital and city
names, all of which are identifiers under Safe Harbor or i2b2. Lab ranges
("12.0-16.0"), "from 3.2 mEq/L" and pain scores ("7/10") were false
positives in the DEV run and are now excluded (tested).

Retrieval on the docs/46 PMC task (5,000 patients, 986 queries, centralized
bge, corpus de-identified, queries not):

| Corpus | MRR |
|---|---|
| raw | 0.4433 |
| basic + NER | 0.4433 |
| safe_harbor + NER | 0.4404 (paired bootstrap vs raw: −0.003 [−0.007, +0.001], p = 0.12) |

## Known gaps (from the TEST misses, not fixed)

| Gap | Example | Why |
|---|---|---|
| MRN with a compound label | "Medical record number: 12345678", "record #1234567" | the basic ID rule allows only one connector after the label |
| Bare names in a new frame | "The patient, Liam Walsh, consented to publication." | no cue the rules know; small-model NER misses about a quarter. The registry catches the hospital's own patients |
| Residence with an uncued preposition | "A fisherman from Matara …" | "from" alone is too broad to act on |
| 12-digit NIC after "Identity card" | "Identity card 199012345678" | the unlabelled NIC rule requires birth year 19xx/20xx followed by 0–8 |
| Quasi-identifiers | rare disease + age + town | needs k-anonymity reasoning, not pattern matching |

Fixing these would need a fresh held-out set to report again.

## Reproduce

```
cd backend
OMP_NUM_THREADS=1 python -m eval.run_deid_benchmark            # both splits + clean cost + retrieval
python -m eval.run_deid_benchmark --split dev --skip-retrieval   # development loop
```

Result file: `docs/results/deid_benchmark_both_*.csv`. Tests:
`tests/test_deidentify.py` (safe_harbor cases, clinical values left alone,
default level unchanged).
