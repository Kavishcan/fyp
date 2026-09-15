# Trust as a ranking term: the docs/32 ablation re-run

## Verdict

**The first routing-level A3 result that moves.** docs/32 showed v2's trust
*gate* is inert at or below the 0.5 prior and deadlocks above it, and named
a ranking term as one of three fixes to be adopted only after re-running the
ablation. Re-run, with `V2Config.trust_weight` re-ordering the coarse pool
by `relevance + w · (trust − 0.5)`:

| trust_weight | Attacker selected | first ⅓ → last ⅓ of the stream | Honest recall | Attacker / honest final trust |
|---:|---:|---|---:|---|
| 0 — gate only (docs/32) | 0.520 | 0.560 → 0.495 | 0.694 | 0.691 / 0.787 |
| **0.5** | **0.362** | 0.422 → **0.301** | 0.680 | 0.684 / 0.787 |
| 1.0 | 0.356 | 0.391 → 0.306 | 0.668 | 0.683 / 0.786 |
| 2.0 | 0.365 | 0.393 → 0.326 | 0.638 | 0.683 / 0.785 |

- At w = 0.5 the forged-profile attacker is selected 30% less often and —
  unlike the gate — its rate keeps falling as evidence accrues (0.42 → 0.30),
  for 1.4 points of honest recall. No deadlock: a demoted source stays in the
  pool and recovers if its evidence improves.
- Above 0.5 the attacker rate is flat and recall falls (0.680 → 0.638). The
  floor is not the weight; it is the **trust signal**. Coordinator-embedded
  passage-to-profile consistency separates the attacker from honest sources
  by 0.11 (0.68 vs 0.79), and a linear demotion cannot turn that into
  exclusion. A better signal, not a bigger weight, is what would lower it
  further.
- The docs/32 finding stands and is sharpened: a hard gate cannot bootstrap;
  a ranking term can, and buys about a third of the attacker's selections.

Adopt: `trust_weight=0.5` as the recommended v2/psi setting. It is **not**
the default — `0` keeps every earlier result byte-identical (verified by
test) — so turning it on is a documented choice, and the docs/32 numbers
remain reproducible.

## Setup

`eval/run_v2_a3.py --trust-weight {0.5, 1.0, 2.0}`, otherwise exactly
docs/32: 24 sources (arguana, nfcorpus, scifact; 8 shards each), ~450
queries, seeds 11/22/33, bge-base, 6-contact cap, `genuine_k=2`,
`coarse_k=12`, one forged-profile attacker at the query mean whose real
documents belong to a donor source; `EvidenceTrust` updated on every
contact; `minimum_trust=0.0` (gate off). Conditions `none` and `trust`;
`plausibility` unchanged from docs/32 and not repeated here.

Implementation: `router/v2.select_dispatch` sorts the coarse candidates by
the adjusted score when `trust_weight > 0`, recording per-candidate
relevance, trust and adjusted score in `decision.steps` (role
"candidate"). Exposure accounting and decoy policies are unchanged.

## What this does not establish

- Anything on the docs/37 attack cases, where the attacker's queries share a
  PII preamble and its profile is unusually attractive; not re-run with the
  term.
- Robustness to an attacker that returns on-profile bait (trust would stay
  high); the attacker here returns off-profile documents, the case the
  signal is designed for.
- Interaction with cells (`decoy_policy="cells"`): the term orders the
  genuine choice, cells decide the cover; not measured jointly.
- Honest false-rejection is not applicable (nothing is rejected); the cost is
  the recall column.

## Reproduce

```
python -m eval.run_v2_a3 --trust-weight 0.5
python -m eval.run_v2_a3 --trust-weight 1.0
python -m eval.run_v2_a3 --trust-weight 2.0
```

Tests: `tests/test_v2_router.py` (byte-identical at 0; demotes without
excluding). Test counts are not attack results.
