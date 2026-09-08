# Evaluation

Existing helpers include instrument.py, metrics.py, sweep.py, ablation.py and
reproduce.py. Their presence does not mean all metrics have been collected.

Legacy sigma/m sweeps evaluate the older perturbation/decoy pipeline.
The independent SmartRouter needs the matched baselines, budget/threshold/trust
ablations and attack experiments in [the plan](../../docs/05-experiments.md).

Smart API traces include candidate/selected IDs, per-step features, costs,
configuration, exclusions, stopping reason, routing latency and retrieval errors.
Byte counters and other optional log fields are not automatically measured.
Keep reserved contact costs separate from actual network measurements.

Record query/model/partition provenance, seeds and trust history. Never derive
router features or attacker-side topic labels silently from test relevance
answers. Separate software tests, synthetic scaling and scientific results.
