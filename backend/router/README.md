# Proposed routing privacy layer

This package wraps a reproduced source-routing baseline. It does not rebuild the
ordinary router unless the baseline acceptance gate proves that adaptation is
unavoidable.

- `exposure.py` — exposure proxies, budget accounting and fan-out constraint
- `perturb.py` — empirical query/profile perturbation
- `anonymity.py` — topic-stable decoy sampling under the exposure budget
- `trust.py` — decoy-aware wrapper around unmodified TASR
- `pipeline.py` — composition of baseline ranking and proposed privacy layer

Max-over-centroid, mean and top-r mean are ablation conditions. Do not present one
as universally correct before measuring it.
