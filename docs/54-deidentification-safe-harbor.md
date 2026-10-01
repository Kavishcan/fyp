# De-identification: Safe Harbor level and a held-out benchmark

## Verdict

| Held-out recall (2,400 injected identifiers per set) | Before (docs/44 rules + NER, the docs/46–53 node setting) | Safe-harbor rules + NER | + the hospital's registry |
|---|---|---|---|
| **Test v2: fresh set, written after the last rule change, run once** | **0.459** | **0.832** | **0.853** |
| Test v1: first held-out run, before its gaps were fixed | 0.528 | 0.928 | 0.975 |
| Test v1 after fixing its gaps (no longer held out) | — | 1.000 | 1.000 |
| Dev (tuned on) | 0.618 | 1.000 | 1.000 |

| Cost | Before | Safe-harbor + NER |
|---|---|---|
| Clean PMC reports altered | 13.8% | 28.9% (mostly real dates, hospitals and places; see below) |
| Centralized PMC MRR (raw 0.4433) | 0.4433 | 0.4401 (−0.003, 95% CI [−0.008, +0.001], p = 0.12, n.s.) |
| Time per document | 48 ms | 48 ms |

**The finding:** rules close every gap they are shown, but a fresh set with
new surface forms still leaks about 15%. The new forms were:
- "12-Mar-1984" and "95 years of age"
- "Cochlear implant SN …" and a plate with no label
- "St Joseph Hospital, Bristol"
- "a Kegalle resident" and "travelling home to …"

Rule-based de-identification does not generalise to unseen phrasing. The
small spaCy NER added nothing on the fresh set (0.832 with and without). A
trained clinical de-identification model is the next step, not more rules.

**Safe sentence:** "Node-side de-identification (HIPAA Safe Harbor rules +
NER + the hospital's registry) removed 85% of 2,400 injected identifiers on
a fresh held-out set (46% for the earlier rules), with no significant
retrieval loss. Rules do not generalise to unseen phrasing; it is not a
validated clinical de-identifier."

Do not say "PII is removed" or "HIPAA compliant". Safe Harbor also requires
no actual knowledge of re-identifiability, and quasi-identifiers (rare
disease + age + town) are not handled.

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
| Record / identity-card numbers with compound labels | one connector only | "Medical record number: …", "record #…", "Identity card …" (labels never cross a full stop) |
| Uncued towns and names | — | a capitalised word whose lower-case form is NOT a common PMC word (`privacy/data/common_words.txt.gz`, 31,388 words from 30,000 reports not used by the benchmark; `eval/build_common_words.py`) after from/in/at/near, or two such words together; eponyms (followed by disease, syndrome, test, curves …), ethnicity (followed by male, descent …) and Fig/Table are excluded. "of"/"to" are not cues (tetralogy of Fallot) |
| Appositive and surname-first names | — | "The patient, Nadia Petrov, …"; the first name left after "Petrov, Lucas" |
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

### Fresh held-out TEST v2 (2,400 identifiers, run once)

| Condition | Recall | Misses (recall) |
|---|---|---|
| basic | 0.390 | patient name 0, partial dates 0, device 0, institution 0, licence 0, postcode 0, residence 0, vehicle 0.01, … |
| basic + NER (docs/46–53 setting) | 0.459 | same zeros except patient name 0.68 |
| safe_harbor | 0.832 | age > 89 0.43 ("95 years of age"), device 0.43 ("SN"), residence 0.47 ("a Kegalle resident", "home to"), date 0.54 ("12-Mar-1984"), vehicle 0.59 (no label), institution 0.67 ("St Joseph Hospital, Bristol"), patient name 0.80, address 0.96 |
| safe_harbor + NER | 0.832 | same (NER added nothing here) |
| **safe_harbor + NER + registry** | **0.853** | same minus patient name |

### TEST v1 (2,400 identifiers; first held-out run, BEFORE the gap fixes)

Categories not listed under misses are at 1.00.

| Condition | Recall | Misses (recall) |
|---|---|---|
| basic (docs/44 rules) | 0.455 | account 0, device 0, licence 0, vehicle 0, postcode 0, residence 0, partial dates 0, institution 0, patient name 0.16, clinician 0.33, MRN 0.53, relative 0.90, address 0.92, SSN/NIC 0.91 |
| basic + NER (docs/46–53 node setting) | 0.528 | same zeros (institution 0.04), patient name 0.64, clinician 0.66, address 0.76, MRN 0.53 |
| safe_harbor | 0.906 | patient name 0.55, MRN 0.53, residence 0.72, SSN/NIC 0.91, relative 0.98, address 0.99 |
| **safe_harbor + NER** | **0.928** | patient name 0.75, MRN 0.53, residence 0.72, SSN/NIC 0.91, relative 0.98, address 0.99 |
| **safe_harbor + NER + registry** | **0.975** | residence 0.72, SSN/NIC 0.91, address 0.99 |

After its misses were fixed, TEST v1 scores 1.000 in every safe_harbor
condition; it is no longer held out. DEV: 0.618 → 1.000 (tuned on).

### Cost on 1,000 untouched PMC case reports

| Condition | Reports altered | Placeholders / 1,000 words | Main placeholders |
|---|---|---|---|
| basic | 4.5% | 0.31 | DATE 80 |
| basic + NER | 13.8% | 0.62 | NAME 124, DATE 80 |
| safe_harbor | 24.1% | 1.58 | DATE 315, NAME 129, ORGANIZATION 82, LOCATION 52 |
| safe_harbor + NER | 28.9% | 1.84 | DATE 315, NAME 232, ORGANIZATION 82, LOCATION 52 |

The uncommon-word rules mostly hit real places and manufacturer names
("San Diego", "Biosense Webster"). That is over-removal, but harmless for
retrieval (below). Most of the rise is not a false positive. Journals leave in month-year
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
| safe_harbor + NER (final rules) | 0.4401 (paired bootstrap vs raw: −0.003 [−0.008, +0.001], p = 0.12) |

## Known gaps (TEST v2 misses, not fixed)

| Gap | Example |
|---|---|
| Day-month-name-year with hyphens | "DOB 12-Mar-1984" |
| Age over 89 in words | "95 years of age" |
| Bare serial labels | "Cochlear implant SN 48213390" |
| Unlabelled plates | "his motorcycle (KLM 4821)" |
| Saint-hospital-comma-town | "St Joseph Hospital, Bristol" |
| Town as an adjective, or after "to" | "A Kegalle resident", "travelling home to Chilaw" |
| Bare names with common first names | "We are grateful to Oliver Hughes …" |
| Quasi-identifiers | rare disease + age + town |

Fixing them would make TEST v2 a development set too. The honest next
step is a trained clinical de-identifier, e.g. a ~440 MB transformer
fine-tuned on i2b2, evaluated on a TEST v3. Not installed: it needs the
user's approval to download.

## Reproduce

```
cd backend
OMP_NUM_THREADS=1 python -m eval.run_deid_benchmark            # dev, test, test2 + clean cost + retrieval
python -m eval.run_deid_benchmark --split dev --skip-retrieval   # development loop
```

Result files: `docs/results/deid_benchmark_all_20261001-185248.csv` (final: dev, v1 after fixes, v2 fresh) and `deid_benchmark_both_20261001-181506.csv` (the first held-out run of v1). Tests:
`tests/test_deidentify.py` (safe_harbor cases, clinical values left alone,
default level unchanged).
