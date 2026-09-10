# Privacy pipeline v2: implementation and integrity controls

## Verdict

v2 removes the plaintext query from the wire, puts genuine and decoy contacts
under one budget with no exemption, and adds profile signing. It is a
**hardening and honest-accounting change, not a privacy guarantee**.

The comparison is now run ([docs/31](31-mode-comparison-results.md)): at
matched contacts and sigma 0, **v2 ties legacy exactly** — 0.711 source recall
and 4.45 audit cost for both, A2 precision 0.258 versus 0.259 with overlapping
seed ranges. v2 is not a better router. Its measured benefit is that it makes
perturbation unnecessary: sigma cost 0.198 recall for 0.094 A2 precision, and
A2 protection comes from the decoys, not the noise.

One design decision was **reversed by measurement**: the E3 decoy-aware trust
exemption was implemented, measured, and then left OFF by default because it
produced a perfect decoy-identification side channel (E4, below).

Opt-in through `routing_mode="v2"`. Legacy remains the API and dashboard
default; legacy and smart code paths are untouched and remain independent
controls.

## What v2 changes

| Stage | Legacy | v2 |
|---|---|---|
| Routing input | perturbed embedding, coordinator-local | raw embedding, coordinator-local |
| Sent to node | **raw query text**, or unperturbed routing vector | **shared-routing-space vector only** |
| Budget | decoys constrained; genuine sources exempt (`protected`) | one budget covers genuine **and** decoy contacts |
| Per-node payload | varies by node type | identical bytes to every contacted node |
| Trust | `BoundedTrustUpdate` prototype | `EvidenceTrust`, every contact updated |
| Profile integrity | `_signature_valid` returned `True` unconditionally | Ed25519 verify, key binding, optional plausibility check |

### 1. Routing is local

Relevance is scored in the coordinator against published profiles. Nothing
leaves the process at this stage, so perturbing the routing vector protects
nothing and v2 does not do it. `sigma` instead perturbs the single vector that
is dispatched (§3).

### 2. One budget, no genuine exemption

`router/v2.select_dispatch` fills the genuine set from the local ranking, then
pads with topic-stable decoys, charging every contact against
`exposure_budget`. If the budget runs out mid-genuine-set, fewer genuine
sources are contacted — there is no `protected` set and no fallback broadcast.
Costs must be positive and are coordinator-supplied.

### 3. Vector dispatch, identical payload

Every contacted node receives exactly `{"vector": [...], "top_n": n}` — same
vector, same `top_n`, no role marker — so a decoy request is byte-for-byte
indistinguishable from a genuine one at the recipient. `InProcessNode` and the
MCP server both gained a `retrieve_vector` path; nodes keep a second index in
the shared routing space to serve it.

**Cost of this choice:** v2 retrieval uses the shared encoder, not each node's
own local model. Heterogeneous local embedders remain available in legacy and
smart modes; v2 trades that for removing plaintext.

**This is not query secrecy.** A routing-space vector can still be inverted
toward the query (`attacks/a1_inversion.py` measured exactly this). v2 removes
plaintext from the wire; it does not make the query confidential. Real
confidentiality needs the HE tier below. Gaussian `sigma` is empirical
embedding perturbation, not differential privacy.

### 4. Deferred hardening tier

HE similarity at the node (rung 2.5, `docs/05-experiments.md`) and PIR for the
fetch are **not implemented**. HE addresses A1 only; the published prediction is
that A2 leakage is unchanged under ranking-preserving encrypted routing, so
anonymity sets remain necessary alongside it.

### 5. Return path

Passages return to the coordinator in the clear. The coordinator must read them
to answer, so this is inherent, not an oversight. The coordinator is inside the
trust boundary; the nodes and the routing observer are not.

### 6. Trust — the exemption that measurement rejected

**E3 (implemented, then disabled by default).** Exempt decoy-selected contacts
from trust updates, so honest decoys are not penalised for returning off-topic
passages.

**E4 (measured, `eval/run_v2_interference.py`).** The exemption is observable: a
node that is contacted but whose trust never moves was a decoy.

| Condition | Exemption attacker precision | recall | A2 frequency attacker precision |
|---|---:|---:|---:|
| E1 unmodified (exemption off) | 0.000 | 0.000 | 0.645 |
| E3 decoy-aware (exemption on) | **1.000** | **1.000** | 0.633 |

360 queries, 9 sources from arguana/nfcorpus/scifact, hashing encoder,
`max_nodes=6`, `genuine_k=2`, seed 42. The exemption traded a partial leak
(~0.64 precision, frequency analysis) for a total one against an observer of
trust values. In this application that observer is trivially available:
`GET /nodes` publishes per-source trust.

**E1's premise also did not hold for this mechanism.** Unmodified, decoy-heavy
sources ended at mean trust 0.852 versus 0.855 for genuine-heavy — a 0.003 gap.
`EvidenceTrust` scores passage-to-profile consistency, not query relevance, so a
decoy returning its own on-profile passages is barely penalised. The exemption
addressed a failure mode TASR's relevance-based rule has and this one does not.

**Decision:** the API path updates trust for every contact. The flag remains for
the A/B in the eval script and must not become the default without a new
experiment that resolves E4. Caveats: one run, one configuration, hashing
encoder, and the two attackers are not equally realistic — this does not
generalise to trust exemptions as a class.

### 7. Integrity

`nodes/signing.py` signs profiles with Ed25519. `SourceRegistry` now verifies
any signature present, can require signatures (`require_signatures`, default
off so existing flows are unchanged), rejects republication under a changed
public key, and can reject implausibly generic profiles
(`plausibility_threshold`, default off).

**What a signature establishes:** the profile was not altered after signing, and
successive versions come from the same key holder.

**What it does not:** who that holder is (no PKI or trust anchor — the public
key travels with the profile), or that the profile is truthful. A malicious node
signs a forged profile just as validly — `test_signed_forged_profile_still_verifies`
asserts this. Signing addresses impersonation and tampering, not A3
self-misrepresentation.

The plausibility check catches the *specific* generic-attractor shape used by
the A3 forgery in `eval/run_attacks.py` (a centroid near the registry mean). A
forgery targeting one real topic passes it. It is a heuristic on published
metadata, not detection.

For simulated nodes the coordinator holds the signing key itself, so the
signature exercises the verification path but proves nothing about a remote
party. Only MCP nodes hold their own key (beside their data file, persisted so a
fresh process per call keeps one identity).

## Threat-model coverage after v2

| Attack | Status |
|---|---|
| A1 query inversion | Improved, not solved. Plaintext gone from the wire; vector still invertible. Real fix is the deferred HE tier. |
| A2 source inference | Unchanged mechanism (topic-stable decoys), now honestly budgeted. No v2-vs-legacy leakage comparison run yet. |
| A3 routing hijack | Tampering/impersonation addressed by signing; self-misrepresentation still open. Live trust remains a heuristic, not the validated TASR condition. |

## Not done

- No answer-quality measurement; docs/31 covers routing only.
- HE and PIR not implemented.
- TLS is irrelevant to this threat model (adversaries are the coordinator, nodes
  and routing observer, not a wire eavesdropper) and is a deployment concern.
- Live trust is still `EvidenceTrust`/`BoundedTrustUpdate`, not reproduced TASR.
- Signature verification is not required by default, so an unsigned profile
  still registers.

## Code and tests

`router/v2.py`, `nodes/signing.py`, `router/registry.py`,
`nodes/simulator.py`, `nodes/mcp_server.py`, `nodes/mcp_client.py`,
`api/state.py`, `api/schemas.py`, `eval/run_v2_interference.py`.

`tests/test_v2_router.py`, `tests/test_v2_api.py`, `tests/test_signing.py`,
`tests/test_mcp_integration.py`. Suite: 247 passed. Test counts are not
experimental quality or privacy results.
