# Large hospitals: a PIR tier for blind unlock

## Verdict

Blind unlock's per-question protocol does not grow with a hospital's data:
- every hospital still gets P points;
- each hospital still does P key multiplications;
- the same P clusters are disclosed.

The one-time **download of every sealed table** does grow. It is about 1.1× the hospital's text (5,000 PMC patients: 13.9 MB of text → 15.1 MB of tables), so a hospital with 100 GB of text would need about 110 GB per key epoch. That part breaks.

The architecture therefore has two tiers, chosen per hospital by size and never by a question:

| | Tier 1: download (docs/47) | Tier 2: PIR (this document) |
|---|---|---|
| For | tables below the break-even (~70 MB at one record per column) | larger tables |
| Offline, per key epoch | the whole sealed table | a hint (`per_column` × 67 MB, independent of the number of records) + a tag map (20 B per record) |
| Per question, round 1 | P blinded points → OPRF (unchanged) | same |
| Per question, round 2 | — (local lookup) | exactly F = P × (max columns per cluster) PIR queries, padded with random columns |
| What the hospital learns | this credential sent P points | the same + F LWE-encrypted queries it cannot read |
| Hospital work per question | P scalar multiplications (ms) | the same + one pass over its whole table per query (PIR cannot avoid touching every byte) |
| What opens an envelope | the OPRF output (credential, budget, role keys) | same: PIR fetches sealed bytes, it opens nothing |

`privacy.pir.recommended_tier(table_bytes, records, record_bytes, per_column)`
returns the tier. It depends only on the hospital's size.

Measured (numpy prototype, one core, Apple M5):

| | Tier 1 | Tier 2 |
|---|---|---|
| PMC (8 small hospitals, 986 questions, P = 8 hybrid): MRR | 0.5062 | **0.5062**, identical top-10 on 100% of questions |
| PMC offline download | **11.3 MB** | 538 MB of hints (8 × 67 MB): tier 2 is the wrong choice for small hospitals, as the tier rule says |
| 1 GB table (measured) | 1 GB download | **67 MB hint + 1.3 MB map**; 2.5 MB per question; 0.6 s hospital time |
| 2 GB table (measured) | 2 GB download | **135 MB hint + 2.5 MB map**; 3.1 MB per question; 1.2 s hospital time |
| **100 GB of text ≈ 110 GB of tables (EXTRAPOLATED)** | 110 GB download per epoch | **≈1.2 GB once** (1.08 GB hint + 134 MB map); ≈22 MB per question; ≈66 s of one core per question at the hospital (≈7 s on 10 cores) |


**Safe sentence:** "Blind unlock's per-question cost is independent of a
hospital's corpus size; its one-time table download is not (≈1.1× the
text). For large hospitals the architecture switches to a PIR tier
(SimplePIR): the device downloads a fixed-size hint instead of the table,
and the hospital scans its table once per query."

Do not call the PIR tier new: it is SimplePIR (Henzinger et al., USENIX
Security 2023) used to fetch blind-unlock envelopes. Tiptoe (SOSP 2023)
uses PIR for private search over a public corpus in the same spirit.

## Design

```text
Hospital (offline, per key epoch)
  de-identify → embed → clusters → sealed chunks (docs/47, unchanged)
  tier 2: pack each cluster's chunks into columns of `per_column` records
          (first-fit; empty slots random bytes; column order shuffled)
          hint = D·A mod 2^32 (rows × 1024 × 4 B), tag map = sorted (tag → column, slot)

Device (offline)          download profile + hint + tag map (tier 2) or table (tier 1)
Device (per question)
  plan: global top-P clusters, P real-or-dummy points to EVERY hospital (unchanged)
  round 1: OPRF replies → unblind → chunk tags of the real clusters
  round 2 (tier 2 only): look up tags in the map → the columns holding them;
           pad to exactly F columns with random others; F PIR queries to every tier-2 hospital
  recover the columns, open the real clusters' chunks with the OPRF-derived keys
```

Choices and why:
- **Tags, not cluster ids, in the map.** The map stays as uninformative as the docs/47 table: pseudorandom tags, sorted. A cluster's chunks are packed together but nobody can see where a run starts.
- **Fixed F per hospital per question.** The number of PIR queries is the same whatever the question. A cover round (docs/52) sends F queries for random columns.
- **Two rounds.** The column of a cluster is known only after its tag, and the tag only after the OPRF, so this costs one extra round trip.
  - A public cluster → column map would allow a single round but would publish cluster sizes. Kept as an option, not used.
- **Public collection only** in this prototype. Each restricted collection (docs/45) would get its own PIR database, served only to its roles, as the tier-1 tables are.

## Costs (exact formulas)

Definitions: record R = 16,424 B (one sealed 16 KB chunk); k = per_column; N = number of records; n = 1024.

| Quantity | Formula |
|---|---|
| hint | k · R · n · 4 B = k × 67.3 MB |
| tag map | 20 · N B |
| per query, up | (N / k) · 4 B |
| per query, down | k · R · 4 B = k × 65.7 KB |
| server work per query | one pass over the table (N · R multiply-adds) |

## Results

### A. PMC: tier 2 returns exactly what tier 1 returns

Setup: the docs/46 setup (5,000 patients, 8 k-means hospitals, rules + NER
de-identification), all 986 questions, P = 8, hybrid ranking, `per_column` = 1.

| | Tier 1: download | Tier 2: PIR |
|---|---|---|
| MRR | 0.5062 | 0.5062 |
| Identical top-10 | — | 100% of questions |
| Clusters truncated | — | 0 |
| Offline download (8 hospitals) | 11.3 MB | 538 MB hints + 14 KB maps |
| PIR queries per hospital per question | 0 | 48 (P = 8 × the largest cluster's 6 columns) |
| Per question, up / down (all hospitals) | 4.6 / 5 KB | 135 KB / 24 MB |
| Slowest hospital per question | 9.3 ms | 12.9 ms |
| Device unlock per question | 13 ms | 449 ms |

At this size the hint (67 MB per hospital) is far larger than the table
(~1.4 MB per hospital). `recommended_tier` keeps these hospitals on tier 1.
One large cluster (6 chunks) forces 48 queries instead of 8. A tier-2
hospital should cap clusters at one column (split larger ones), so F = P.

### B. Scaling: PIR cost against table size (random records of the sealed-chunk size, 8 queries)

| Table | Layout (rows × columns) | Hint | Map | Hint build | Up per question | Down per question | Hospital time | Device time |
|---|---|---|---|---|---|---|---|---|
| 64 MB | 16,424 × 3,896 | 67 MB | 0.08 MB | 1 s | 0.12 MB | 0.53 MB | 39 ms | 170 ms |
| 256 MB | 16,424 × 15,586 | 67 MB | 0.31 MB | 3 s | 0.50 MB | 0.53 MB | 152 ms | 260 ms |
| 1 GB | 16,424 × 62,347 | 67 MB | 1.25 MB | 12 s | 2.00 MB | 0.53 MB | 614 ms | 662 ms |
| 2 GB | 32,848 × 62,348 | 135 MB | 2.49 MB | 23 s | 2.00 MB | 1.05 MB | 1,174 ms | 778 ms |

- Hospital throughput was a steady 13–14 GB/s of (table × queries) on one core: exact 16-bit-split float64 BLAS (`privacy/pir._mul_mod32`).
- Hospital time is linear in the table. The hint stays fixed until the column limit forces `per_column` up.

### C. A 100 GB hospital (extrapolated from B with the exact formulas; not run)

100 GB of text ≈ 110 GB of sealed tables ≈ 6.7 M records.

| `per_column` | Columns | Device download once per epoch | Up per question | Down per question | Hospital time per question |
|---|---|---|---|---|---|
| 16 | 419 k | 1.08 GB hint + 134 MB map | 13.4 MB | 8.4 MB | ≈ 66 s on one core at 13.4 GB/s |
| 103 | 65 k | 6.9 GB hint + 134 MB map | 2.1 MB | 54 MB | ≈ 66 s |

The device regenerates the public matrix from its seed (columns × 1,024
words: 1.7 GB at 419 k columns) rather than storing it.

Compared with tier 1's 110 GB per epoch, tier 2 downloads about 90–100×
less. The price is about a minute of single-core work at the hospital per
question, roughly 7 s across 10 cores if it parallelises linearly (not
measured). The paper's C implementation reports ~10 GB/s per core, similar
to the BLAS path here.

## What this does not establish

- The numpy prototype is not optimised. The paper's C implementation reports ~10 GB/s per core; our numbers are an upper bound on time.
- The LWE parameters are SimplePIR's and were not re-estimated.
  - The public matrix comes from a seeded PCG64 stream.
  - A deployment would use an AES/SHAKE expansion, as the paper does.
- Tier 2 is not wired into the MCP transport or the standalone client yet. It is measured in-process (`eval/run_pir_tier.py`), with the real OPRF and the real PIR maths.
- Server time grows linearly with the table, per query. Cover rounds cost the same as real ones, so a hospital must budget one scan per tick per client.
- Alternatives not built:
  - offline/online PIR with client preprocessing (sublinear server time, more client state);
  - two-server PIR (much cheaper, needs two non-colluding servers).

## Reproduce

```
cd backend
OMP_NUM_THREADS=1 python -m eval.run_pir_tier --sizes-mb 64 256 1024
```

Tests: `tests/test_pir_tier.py`.
- PIR returns the asked record from any slot.
- PIR unlock opens exactly what the full-download unlock opens, with a fixed number of queries per hospital.
- The tier rule keeps PMC-sized hospitals on download and moves 100 GB hospitals to PIR.
