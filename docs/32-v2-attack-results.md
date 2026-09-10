# v2 under A1 and A3: measured results

## Verdict

Both are negative, and one is a defect in v2 itself rather than a tuning
problem.

**A1.** v2's vector dispatch provides **no** inversion resistance at its shipped
setting: a nearest-neighbour attacker recovers the exact query with probability
**1.000** at sigma 0. Perturbation cannot rescue it — at sigma 0.10 retrieval
agreement has already fallen to 0.265 while A1 exact recovery is still 0.997.
Utility degrades faster than the attack does, at every setting tested. The
dispatched vector is simultaneously the attack surface and the retrieval
signal, so no noise level separates them.

**A3.** Neither shipped control works. Evidence trust is **inert by
construction** — `select_dispatch` uses trust only as an exclusion gate, never
as a ranking term, so at the default `minimum_trust=0.0` it cannot affect
selection at all; the `trust` and `none` conditions are identical to three
decimals. Raising the gate does not fix it: at `minimum_trust=0.75` the network
**deadlocks completely** (honest recall 0.000), because trust starts at the 0.5
neutral prior, nothing clears the gate, nothing is selected, no evidence is
gathered, and trust never rises. The plausibility check does block the attacker,
but by rejecting **17.7 of 24 honest sources** and cutting honest recall from
0.694 to 0.460.

These correct an earlier framing in this project's notes that sigma "helps A1."
It does reduce inversion in isolation; measured against what it costs
retrieval, it is not a usable lever for either A1 or A2.

## Setup

24 sources (arguana, nfcorpus, scifact; 8 balanced random shards each), ~450
judged queries, seeds 11/22/33, `BAAI/bge-base-en-v1.5` normalized, 6-contact
cap, `genuine_k=2`, `coarse_k=12`, unit contact cost. Mean [min, max] across
seeds; seeds share documents and questions, so ranges show partition
sensitivity, not confidence intervals. `eval/run_v2_a1.py`,
`eval/run_v2_a3.py`.

## A1: residual inversion of the dispatched vector

Attacker: `attacks/a1_inversion.NearestNeighbourInversion`, matching the
dispatched vector against a reference pool of the real queries. A transparent
baseline, not a trained inversion model — these figures are a **lower bound**
on a stronger attacker.

Utility is `retrieval_agreement`: does a contacted source still return the
top-1 document it would have returned unperturbed? Sigma cannot change which
sources are contacted in v2, only what they retrieve, so routing recall would
show a flat line and hide the cost. Agreement is not a relevance measure.

| sigma | A1 term recovery | A1 exact recovery | Retrieval agreement |
|---:|---:|---:|---:|
| 0.00 | 1.000 | **1.000** | 1.000 |
| 0.10 | 0.999 | 0.997 | 0.265 [0.257, 0.273] |
| 0.25 | 0.489 [0.455, 0.536] | 0.470 | 0.062 [0.057, 0.065] |
| 0.50 | 0.104 [0.093, 0.119] | 0.080 | 0.020 |
| 1.00 | 0.039 [0.031, 0.044] | 0.017 | 0.011 |

At sigma 0.10 the defender has destroyed 73% of retrieval fidelity and reduced
exact recovery by 0.003. By sigma 0.25, where recovery finally halves,
agreement is 0.062 — retrieval is essentially arbitrary. There is no setting at
which noise buys inversion resistance at usable retrieval quality.

**Caveat on the sigma grid.** `router/perturb.py` adds raw per-dimension
Gaussian noise, so sigma is not scale-free: at 768 dimensions sigma 0.1 already
means a noise vector roughly 2.8x the norm of the unit-length signal. A
calibrated experiment would parameterise by signal-to-noise ratio. That makes
this grid harsher than the numbers suggest, but it does not change the
structural conclusion, which does not depend on the scale.

**Implication.** Removing plaintext from the wire (docs/30) is worth doing and
is not inversion resistance. The only route to real A1 protection here is
cryptographic — the deferred HE tier — not a tuning exercise.

## A3: defence ablation against a forged profile

Attacker: one source publishing the mean of the real query distribution (the
generic-attractor forgery from `eval/run_attacks.py`), whose actual documents
belong to an unrelated honest source, so the profile lies while retrieval
behaviour stays honest.

### Default gate (`minimum_trust=0.0`, as shipped)

| Condition | Attacker rate | first ⅓ → last ⅓ | Honest recall | Honest rejected |
|---|---:|---|---:|---:|
| none | 0.520 | 0.560 → 0.495 | 0.694 | 0 |
| plausibility | 0.000 | 0.000 → 0.000 | **0.460** | **17.67 / 24** |
| trust | **0.520** | 0.560 → 0.495 | 0.694 | 0 |
| both | 0.000 | 0.000 → 0.000 | 0.460 | 17.67 / 24 |

`trust` equals `none` exactly. The attacker's trust does fall (0.691 against
0.787 for honest sources) and it changes nothing, because trust is only ever
compared against `minimum_trust`. The mild 0.560 → 0.495 decline appears in the
undefended condition too, so it is not the mechanism working.

### Engaged gate (`minimum_trust=0.75`)

| Condition | Attacker rate | Honest recall |
|---|---:|---:|
| all four | 0.000 | **0.000** |

Total deadlock. Sources start at the 0.5 neutral prior, so none clears a 0.75
gate; nothing is dispatched; no evidence is observed; trust never rises. The
gate is unusable at any value above the cold-start prior, and inert at or below
it. The attacker settles at 0.691, so even the narrow band between 0.691 and
0.787 could not be reached from a 0.5 start.

**This is a defect in `router/v2.select_dispatch`, not a tuning result.** A hard
gate above the cold-start prior cannot bootstrap. Fixing it needs one of: trust
as a ranking term that demotes rather than excludes; an exploration allowance
so unproven sources are still sampled (upstream TASR has `explore_interval`);
or a prior above the gate. None of these is implemented, and none should be
adopted without re-running this ablation.

Note that `tests/test_v2_router.py::test_minimum_trust_excludes_low_trust_sources`
passes: it hands the selector a pre-set low trust value. Unit tests confirmed
the gate excludes what it is told to exclude; only the experiment showed the
gate can never be reached.

### Plausibility collateral

Blocking the attacker cost 17.67 of 24 honest sources and 0.234 honest recall.
With same-domain shards, honest sources genuinely sit near the registry mean, so
"close to average" does not separate attacker from neighbour. The check stays
off by default (`plausibility_threshold=None`) and should not be enabled for a
same-domain deployment on this evidence.

## Standing after this

| Attack | Status |
|---|---|
| A1 | **No defence.** Plaintext removed from the wire; exact inversion at 1.000. Noise measured as unusable. HE remains the only route and is not built. |
| A2 | Topic-stable decoys remain the one measured defence (2–4x leakage reduction, docs/31). |
| A3 | **No working defence.** Trust inert then deadlocking; plausibility unusable at same-domain scale. Live path still lacks the validated TASR condition. |

## What this does not establish

- One attacker per threat, one forgery strategy, one dataset family, three
  shared-data partitions. A targeted forgery aimed at a single topic was not
  tested and would likely pass the plausibility check.
- The A1 attacker is a nearest-neighbour floor; a trained inversion model would
  do better, so the sigma column understates the risk.
- No answer-quality measurement anywhere here.
- The deadlock result is specific to a hard gate with a 0.5 prior; it does not
  show trust mechanisms in general cannot work.

## Reproduce

```
python -m eval.run_v2_a1 --corpora arguana nfcorpus scifact \
  --nodes-per-corpus 8 --n-queries-per-corpus 150 --seeds 11 22 33
python -m eval.run_v2_a3 --corpora arguana nfcorpus scifact \
  --nodes-per-corpus 8 --n-queries-per-corpus 150 --seeds 11 22 33
python -m eval.run_v2_a3 ... --minimum-trust 0.75
```

Tests: `tests/test_v2_attacks.py`. Test counts are not experimental quality or
privacy results.
