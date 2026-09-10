# Matched-budget comparison: legacy, smart and v2

## Verdict

**v2 is not a better router than legacy — it is exactly as good.** At sigma 0
the two are identical on source recall (0.711 both, overlapping seed ranges)
and audit cost (4.45 both), because at that setting they make the same
selection and add the same topic-stable decoys. v2's value is the wire property
and the budget accounting, not retrieval quality. Do not present it as a
routing improvement.

**What v2 does buy, measured:** it makes sigma unnecessary. Perturbation cost
0.198 source recall (0.711 → 0.513) to move A2 precision 0.094 (0.259 → 0.165),
and at sigma 0.25 the A2 change was inside the seed spread — indistinguishable
from nothing. A2 protection here comes from decoys, not from noise, so v2 runs
at sigma 0 and keeps the recall legacy was paying away.

**smart is worse than both on this task** — recall 0.556 against 0.711 at the
same six contacts, with higher audit cost. Its low A2 precision (0.072) is not
a privacy win; see the warning below.

## Setup

- 24 simulated sources: arguana, nfcorpus, scifact, 8 balanced random shards each.
- 450 test questions with positive qrels (449 on seeds 22/33 — see Data note).
- Seeds 11, 22, 33 repartition sources and reshuffle the query stream.
- `BAAI/bge-base-en-v1.5`, normalized, cached; no training, no downloads.
- Three centroids per source, existing NumPy clustering, no profile noise.
- Every mode capped at **6 contacts**; unit cost per contact; neutral trust 0.5
  with no feedback; `genuine_k=2`, `coarse_k=12`.
- CPU, macOS arm64. `eval/run_mode_comparison.py`, seed-aggregated CSV plus
  per-seed raw output in `data/eval_results/`.

Same-domain, randomly partitioned sources. Not a 24-hospital deployment, not a
measurement of MCP transport, and not an independent-sample study: the three
seeds share documents and questions, so the ranges show partition sensitivity,
not confidence intervals.

## Results

Mean [min, max] across seeds. A2 precision is the observer's precision at
naming a topic's genuine sources from dispatch patterns — **lower is better**.

| Mode | sigma | Source recall | Contacts | Audit cost | A2 precision |
|---|---:|---:|---:|---:|---:|
| broadcast | — | 1.000 | 24.00 | 21.30 | 0.030 [0.029, 0.031] |
| oracle | — | 1.000 | 2.36 | 0.00 | 1.000 |
| smart | 0.00 | 0.556 [0.543, 0.570] | 6.00 | 5.44 | 0.072 [0.047, 0.092] |
| **v2** | 0.00 | **0.711 [0.706, 0.720]** | 6.00 | 4.45 | 0.258 [0.197, 0.333] |
| legacy | 0.00 | 0.711 [0.706, 0.720] | 6.00 | 4.45 | 0.259 [0.179, 0.310] |
| legacy | 0.25 | 0.631 [0.610, 0.651] | 6.00 | 4.78 | 0.253 [0.195, 0.283] |
| legacy | 1.00 | 0.513 [0.506, 0.520] | 6.00 | 5.08 | 0.165 [0.119, 0.203] |

## Reading these numbers

**v2 versus legacy at sigma 0 is a tie, not a win.** 0.711 versus 0.711,
4.45 versus 4.45, A2 0.258 versus 0.259 with heavily overlapping ranges. This
is the expected result: same genuine selection, same decoy mechanism. The
comparison exists to show v2 costs nothing, not to show it gains anything.

**Perturbation is a poor trade, now with seed ranges.** From sigma 0 to 1.0,
recall falls 0.198 while A2 precision falls 0.094. At sigma 0.25 the A2
movement (0.259 → 0.253) sits inside the seed spread and establishes nothing.
This reproduces the earlier finding that noise is the wrong lever against A2.

**Low A2 precision does not by itself mean private.** smart posts the lowest
A2 of the three routers (0.072) while contacting the same six sources — because
its selections correlate poorly with the truth, so the observer's inference is
also poor. That is leakage through weak retrieval, not through design. A2 must
always be read next to recall; smart's 0.072 costs 0.155 recall against v2.

**The bounds show the real tension.** oracle contacts only relevant sources and
is therefore perfectly identifiable (A2 = 1.000). broadcast is nearly
unidentifiable (A2 = 0.030) by contacting all 24 sources at audit cost 21.30.
Perfect utility implies perfect leakage; near-zero leakage implies maximum
exposure. Every practical mode sits between them.

## Data note

`eval/sweep.py:collect_documents` raised on any qrel referencing a doc id
absent from `corpus.jsonl`, so a run's success depended on which queries the
seed sampled — seed 11 passed and seed 22 crashed. Tolerance is now opt-in
(`allow_missing=True`), default unchanged so prior experiments are
byte-identical, and dropped queries are reported: 0, 1 and 1 across the three
seeds. This was a latent defect on `main`, not a change of experimental
conditions.

## What this does not establish

- No answer-quality measurement. Source recall is whether a relevant source was
  contacted, not whether the final answer was correct.
- No privacy guarantee. One attacker, one budget policy, one dataset family,
  three shared-data partitions.
- No claim about v2's wire property. That plaintext no longer leaves the
  coordinator is a code fact asserted by tests, not something these metrics show.
- No scaling result. 24 sources, in-process simulation.
- smart was run with `minimum_gain=0` so it fills the cap; its own tuned
  configuration was not searched here.

## Reproduce

```
python -m eval.run_mode_comparison \
  --corpora arguana nfcorpus scifact --nodes-per-corpus 8 \
  --n-queries-per-corpus 150 --max-nodes 6 --genuine-k 2 \
  --coarse-k 12 --seeds 11 22 33
```

Tests: `tests/test_mode_comparison.py`. Suite at time of writing: 258 passed.
Test counts are not experimental quality or privacy results.
