# Experiments

Keep configurations, provenance and raw per-query outputs for each named method.
Inspect .gitignore and the actual tracked files before assuming results are
committed. A CSV without model/split/config provenance is not sufficient evidence.

The independent smart router is evaluated against separate baseline runs and
ablations, not by relabelling existing legacy outputs. See
[experiment plan](../docs/05-experiments.md).

Existing sigma/m and E1-E4 runners belong to the optional legacy decoy/TASR study.
For smart.py, freeze budgets, gain/trust settings, aggregation, source costs,
embeddings, manifests and query order. Reset trust for independent runs or
document the identical stream used across conditions.

Record external code/artifact versions and exact commands. Distinguish a clone,
a passing adapter test, a reproduction and an adapted benchmark.
