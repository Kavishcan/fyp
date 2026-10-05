---
tags: [type/concept]
updated: 2026-10-05
---

# Source-content exposure

Gap 3 of the thesis, renamed from "source-data leakage": **sensitive source content released during federated retrieval beyond what the query needs.** It is separate from [[Query leakage]] (what hospitals learn) and [[Access-pattern leakage]] (what contacts reveal).

**Measured as:**
- records unlocked per question vs the top-10, and release precision ([[Release results]]);
- identifier recall of de-identification ([[Safe Harbor de-identification results]]).

**Controls:** [[Safe Harbor de-identification]], [[Role-based access]], [[Credential gate]], [[Evidence release control]].

**Status:** measured and controlled, not eliminated. Broadcast releases fewer records at equal quality but shows the question to every hospital.

## Implementation / Experiment Sources

- [docs/56-source-content-release.md](../../docs/56-source-content-release.md)
- [docs/54-deidentification-safe-harbor.md](../../docs/54-deidentification-safe-harbor.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
