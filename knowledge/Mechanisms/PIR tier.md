---
tags: [type/mechanism]
updated: 2026-10-05
---

# PIR tier

Tier 2 of [[Blind unlock]] for large hospitals.

**What the device downloads instead of the table:**
- a fixed-size SimplePIR hint (`per_column` × 67 MB);
- a sorted tag map (20 B per record).

**Per question:**
1. The OPRF round, unchanged.
2. Exactly F PIR queries to every tier-2 hospital, padded with random columns, for the columns holding the real clusters' sealed chunks.

LWE parameters: n = 1024, q = 2³², σ = 6.4, p = 256 (SimplePIR's).

**Properties:**
- PIR hides which column was fetched. The OPRF still decides what can be opened.
- The hospital scans its whole table per query.
- `recommended_tier` chooses by size only, never by question.
- Not new: SimplePIR applied to blind-unlock envelopes. See [[Tiptoe and SimplePIR]], [[PIR tier results]].

## Implementation / Experiment Sources

- [backend/privacy/pir.py](../../backend/privacy/pir.py)
- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)
- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/55-large-hospitals-pir-tier.md](../../docs/55-large-hospitals-pir-tier.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
