# Repository guidance

## Current research direction

Docs/32 measures v2 under A1 and A3; both are negative and must be preserved.
A1: vector dispatch gives NO inversion resistance (exact recovery 1.000 at
sigma 0), and noise cannot fix it — at sigma 0.10 retrieval agreement is
already 0.265 while recovery is still 0.997, so utility dies faster than the
attack. Do not describe sigma as an A1 lever. A3: v2's trust is INERT because
`select_dispatch` uses it only as an exclusion gate, and raising the gate above
the 0.5 cold-start prior deadlocks the network entirely (honest recall 0.000) —
a defect in v2, not a tuning result; do not adopt a fix without re-running the
ablation. The plausibility check blocks the attacker only by rejecting 17.7 of
24 honest sources; keep it off by default. A2 decoys remain the only measured
defence.

Docs/30-31 cover the opt-in `routing_mode="v2"` privacy pipeline: local
routing, one exposure budget covering genuine AND decoy contacts with no
exemption, shared-routing-space vector dispatch instead of raw query text, and
Ed25519 profile signing. Preserve these results. v2 TIES legacy at matched
contacts (0.711 recall, 4.45 audit, A2 0.258 vs 0.259) — it is not a better
router, and its benefit is that sigma becomes unnecessary. Two findings must
not be quietly reversed: the E3 decoy-trust exemption identified decoys at
precision/recall 1.00 and is therefore OFF in the API path, and low A2
precision alone does not mean private (smart posts 0.072 only because its
selections are poor). A routing-space vector is not query secrecy — it stays
invertible. Signing proves integrity and key binding, never truthfulness; a
signed forged profile verifies. Legacy remains the API/dashboard default.

FedSafeRouter is a training-free, exposure-constrained and trust-aware adaptive
source router for Federated RAG. The user explicitly chose to implement the
smart router itself. RAGRoute is a comparison baseline, not its required engine.

The current implementation contract is backend/router/smart.py and
docs/13-smart-router-implementation.md. See docs/03-architecture.md and
docs/04-router-design.md for boundaries and the exact selection rule.
The earlier instruction prohibiting a new router is superseded.

## Engineering and evidence rules

- Preserve the legacy pipeline and published baseline semantics as independent
  controls. Do not silently change old experiment outputs or call legacy RAGRoute.
- Smart mode is opt-in through POST /query; legacy remains the API/dashboard
  default. Update documentation and tests if those defaults change.
- Every smart source contact must fit the positive-cost per-query budget.
  There is no genuine-source exemption, decoy dispatch or fallback broadcast.
- Relevance, trust and overlap are heuristics. Do not claim novelty, optimality,
  privacy guarantees or hijacking resistance from implementation tests.
- Call Gaussian noise empirical embedding perturbation, not DP without a
  separately established formal mechanism and assumptions.
- Source trust starts at 0.5 with an uncertainty penalty. Smart EvidenceTrust
  uses coordinator-embedded passage consistency, not self-advertised trust or
  remote retrieval scores. It is not TASR.
- The coordinator sees raw queries and returned passages; contacted MCP nodes
  receive raw queries. Do not describe the live implementation as query-secret.
- Signature validation, production authentication and complete de-identification
  are not implemented. Policy labels are only a demo selection hook.
- Hashing is still the live demo encoder. Semantic-model evaluation must use
  compatible query/profile spaces and record model/version/preprocessing.
- A cloned repository is not a reproduced result. Pin code/artifacts and save
  commands, environments, splits and raw per-query outputs.
- Distinguish real MCP transport, in-process simulation and virtual source
  partitions. A 1,000-profile synthetic test does not demonstrate 1,000 servers.
- Do not invent measured costs or leakage. Unit contact cost is an explicit
  exposure definition, not an estimated attack probability.
- Keep paper literature summaries in the student's own writing; repository
  planning/specification notes are support material, not submission-ready prose.
- Inspect existing datasets first. The user disallowed downloads above 500 MB;
  do not silently fetch larger datasets.

## Module map

| Path | Role |
|---|---|
| backend/router/smart.py | SmartConfig, SourceEvidence, SmartRouter, SmartDecision, EvidenceTrust |
| backend/router/v2.py | V2Config, V2Decision, select_dispatch, dispatch_payload, DecoyAwareEvidenceTrust (exemption OFF by default, see docs/30) |
| backend/nodes/signing.py | Ed25519 profile signing; integrity and key binding only, not truthfulness |
| backend/router/pipeline.py | Preserved legacy baseline-plus-layer path |
| backend/router/exposure.py | Legacy proxy accounting; genuine exemptions mean it is not smart budget enforcement |
| backend/router/trust.py | Legacy BoundedTrustUpdate, not official TASR |
| backend/baselines/ | Local controls and external adapters; RAGRoute remains a stub |
| backend/nodes/ | Profile/index construction, MCP client/server, simulator and embedders |
| backend/api/ | Stateful demo coordinator; smart/legacy routing selection |
| backend/attacks/, backend/eval/ | Existing attack/evaluation building blocks |
| frontend/lib/api.ts | Hand-maintained mirror of backend/api/schemas.py |
| docs/ | Current design, planned experiments and limitations |

Python 3.10+ is required. Keep tests independent of optional heavy model
dependencies and downloaded corpora where possible. Existing MCP tests use
synthetic fixtures with genuine subprocess transport.

## Verification

Run .venv/bin/pytest -q from the repository root. When API types change, run
frontend/node_modules/.bin/tsc --noEmit --incremental false from frontend.
Do not treat test counts as experimental quality or privacy results.

New code may extend the independent selector, but scientific claims require
the controls and ablations in docs/05-experiments.md. No baseline training is
required by SmartRouter; reproducing a learned comparison method may still
require its offline training or checkpoint.
