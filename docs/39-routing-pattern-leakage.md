# Does the routing pattern leak the query? The decoy ablation

## Verdict

**Yes — and the topic-stable decoys built for docs/30 do not stop it.**

An observer who sees only which sources were contacted for a query — never
its text, vector, or which contacts were decoys — names the query's origin
engine **49.6%** of the time under a plain cosine router (13 classes, chance
7.7%), and places it in its top three guesses **84%** of the time. The
privacy problem the proposal describes is real and measured.

Topic-stable decoys (the pattern v2 and psi modes produce) leave topic
inference **unchanged** (0.495 against 0.454 for the same fan-out without
decoys) while cutting the source-identity attack from 0.744 to 0.564: they
hide *which* contact is genuine, but the cover set itself is a topic
fingerprint. Random decoys do the opposite — topic inference falls to
0.336–0.380 while the source attack returns to 0.667–0.692. **No decoy
strategy measured here reduces both leaks; only broadcast does, at 13
contacts.** The two leakages the research gap names are in tension under a
fixed contact budget.

"Topic-stable" is also less stable than the name suggests: same-origin
queries share decoys at Jaccard 0.23, because the live topic key
(`api/topic.assign_topic_key`) is the nearest of 39 published centroids,
not the engine.

## Setup

`eval/run_leakage.py`. FeB4RAG requests whose origin engine (`rid_mapping.tsv`)
is one of the 13 engines with local corpora: 640 requests. Topic label =
origin engine (13 classes) and its vertical (6 classes: biomedical, finance,
general, scientific, wiki, debate). Profiles as docs/36 (1,500 sampled
documents per engine, bge-base, k=3), seeds 11/22/33; contact cap 4,
`genuine_k=2`, `coarse_k=8`.

Attackers (`attacks/a2_topic_inference.py`):
- **learned observer** — multinomial naive Bayes over the multi-hot contact
  vector, trained on a labelled half of the requests, tested on the other
  half. Models an insider or an observer who learned topics for past
  queries.
- **metadata floor** — knows only each source's public domain and guesses
  one contacted source's domain at random.
- **source attack** — `attacks/a2_source_inference`: name the origin engine
  from per-topic contact counts (the docs/31 direction).
- **decoy stability** — mean Jaccard between decoy sets of same-origin
  queries.

Conditions: random top-4; broadcast; cosine top-2 (the "normal router") and
top-4; v2 `select_dispatch` (2 genuine + 2 topic-stable decoys from the
coarse pool — psi's pattern); 2 genuine + 2 random decoys from the coarse
pool; 2 genuine + 2 random decoys from all engines; oracle (best-graded
engines). No cryptography is involved anywhere: the attack acts on
identities, so psi and v2 share the sticky-decoy row.

## Results (mean of 3 seeds; std ≤ 0.03 on every attack figure)

| Condition | Contacts | Origin reached | Graded gain | Topic acc (13) | Floor | Top-3 | Macro-F1 | Topic acc (6) | Source attack | Decoy Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 4.0 | 0.303 | 0.495 | 0.065 | 0.091 | 0.218 | 0.062 | 0.276 | 0.077 | — |
| broadcast | 13.0 | 1.000 | 1.000 | 0.059 | 0.080 | 0.200 | 0.009 | 0.305 | 0.077 | — |
| cosine@2 | 2.0 | 0.678 | 0.775 | **0.496** | 0.318 | 0.841 | 0.451 | 0.581 | 0.692 | — |
| cosine@4 | 4.0 | 0.817 | 0.772 | 0.454 | 0.196 | 0.832 | 0.408 | 0.580 | 0.744 | — |
| sticky decoys (v2/psi) | 4.0 | 0.787 | 0.720 | **0.495** | 0.188 | 0.826 | 0.459 | 0.590 | **0.564** | 0.23 |
| random decoys, pool | 4.0 | 0.764 | 0.722 | 0.380 | 0.169 | 0.769 | 0.349 | 0.489 | 0.692 | 0.15 |
| random decoys, any | 4.0 | 0.732 | 0.674 | **0.336** | 0.186 | 0.702 | 0.307 | 0.441 | 0.667 | 0.12 |
| oracle | 1.5 | 0.509 | 1.000 | 0.449 | 0.447 | 0.692 | 0.434 | 0.623 | 0.538 | — |

Chance: 0.077 (13 classes), 0.167 (6). Random and broadcast sit at chance,
as they must. The oracle's 0.449 shows that the best-graded engine set is
itself informative — the leak is intrinsic to good routing, not an artefact
of the cosine router.

## Reading

- **Experiment 1 of the review (prove the leak) is done.** 0.496 vs 0.077.
- **Sticky decoys buy source-identity privacy at zero topic-privacy gain.**
  This is the mechanism docs/30–31 measured as "the only working defence";
  it was measured against the source attack only. Against the topic attack
  it does nothing.
- **Random decoys buy topic privacy at a source-identity cost**, and drawing
  them from all engines rather than the coarse pool helps topic privacy
  further (0.336) at a routing cost (origin reached 0.732 vs 0.787).
- Utility cost of decoys is small: graded gain 0.772 → 0.720 at equal
  fan-out; origin reached 0.817 → 0.787.
- The docs/37 psi result (0 of 3 sensitive values exposed) concerns query
  *content* and stands. This table concerns the *pattern*, which psi does
  not change. The two are the two leaks the research gap names, and the
  current design fixes one.

## What this does not establish

- A defence. None was tested that lowers both attacks; a diversity-aware
  decoy policy (cover sets spanning verticals, kept stable per topic) is
  the obvious candidate and is not built.
- Leakage under an attacker with the query text or vector, or one who
  combines patterns with timing and sizes.
- Anything about same-domain federations, where all engines share a
  vertical and the 6-class attack collapses by construction; that is the
  planned healthcare hard case.
- Stability with a coarser topic key (e.g. per engine) — a design change
  that would raise Jaccard and, on this evidence, raise topic leakage too.

## Reproduce

```
python -m eval.run_leakage
```

Tests: `tests/test_a2_topic_inference.py`. Test counts are not privacy results.
