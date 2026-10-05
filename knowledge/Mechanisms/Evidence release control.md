---
tags: [type/mechanism]
updated: 2026-10-05
---

# Evidence release control

Two knobs set how much source content one question releases to the device:
- **cluster granularity:** `build_cluster_index(docs_per_cluster=, min_size=)`;
- **probe count:** P.

Records released ≈ P × cluster size.

**Guidance:**
- Keep min_size ≥ 5 (docs/35: never publish document embeddings as centroids).
- 5/5 at P=16 matched the default's quality at P=16 with 19% fewer records.
- Smaller minimums cut release further but raise centroid proximity to single patients.

Other release controls:
- [[Role-based access]] and the [[Credential gate]] budget limit what can be opened at all.
- Device-side ranking ([[Hybrid rerank]]) limits what is passed on.

See [[Release results]], [[Source-content exposure]].

## Implementation / Experiment Sources

- [backend/privacy/cluster_index.py](../../backend/privacy/cluster_index.py)
- [docs/56-source-content-release.md](../../docs/56-source-content-release.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
