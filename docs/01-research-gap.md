# Research gap hypotheses

These are research-planning notes, not a completed literature synthesis.
The student must verify the closest papers and write the review independently.
No claim that a gap is globally unoccupied is established by this repository.

## Main question

Can a training-free source router maintain useful federated retrieval under an
explicit recipient-exposure budget while adapting source count and accounting
for uncertain or manipulated source profiles?

The implemented greedy selector is a candidate answer, not evidence that the
answer is better than existing methods.

## Consolidated gaps to investigate

| Gap | Existing work to check | Missing evidence to establish | Planned test |
|---|---|---|---|
| Joint relevance, exposure and trust trade-off | RAGRoute; privacy-aware routing; routing-hijacking/TASR | Whether comparable methods jointly satisfy a declared contact budget and retain useful retrieval under malicious profiles | Matched-data baseline comparison and budget curves |
| Adaptive selection without task-specific router training | Source-profile/cosine routing and learned source selectors | Whether adaptive gain/overlap stopping improves the trade-off over fixed-k and simple combinations | Fixed-k, no-overlap and equal-trust ablations |
| Robustness of profile-based trust | TASR and profile-hijacking attacks | How cold starts, profile changes, bait passages and reputation resets affect constrained selection | A3, honest-source exclusion and recovery experiments |
| Distinction between fewer recipients and routing-pattern privacy | HE/DP routing methods and metadata-leakage analyses | Whether contact reduction changes observer inference, independently of retrieval loss | A2 with held-out queries, matched quality and explicit observer knowledge |
| Scaling under realistic source partitions | Federated retrieval benchmarks and distributed systems evaluations | How quality and measured transport costs change with domain overlap and source growth | Cross-domain/same-domain partitions; separate real-MCP and in-memory runs |

These rows consolidate overlapping concerns rather than treating every metric
as a separate novelty claim.

## What this project may contribute

An explicit constrained selection rule, a declared exposure-accounting model,
and reproducible evaluation of the relevance/exposure/trust trade-off.
The contribution depends on results and on differentiation from the closest
verified literature, not on having an MCP interface or a visual studio.

Centroids, cosine similarity, greedy selection and trust updates are established
ingredients. Their composition is not automatically novel. A baseline using a
simple weighted score or fixed-k selection is necessary to test added value.

## Claims to avoid

- No privacy-aware routing frameworks exist.
- Encryption always yields exactly identical rankings: approximate arithmetic
  and near ties require empirical checking, and key boundaries matter.
- Contacting fewer nodes guarantees source anonymity or query secrecy.
- A consistent returned passage proves source honesty.
- Decoys necessarily harm every trust defence in the same way.
- Passing synthetic tests proves clinical usefulness or publication readiness.

## Optional earlier hypothesis

The legacy design examined whether decoy contacts interfere with TASR feedback.
That remains a possible extension, not the main implemented smart-router
contribution. Smart mode has no decoys. Run unmodified and modified conditions
before making any privacy/trust interference claim.

Use [baseline selection](10-baseline-selection.md) to record evidence status and
[experiments](05-experiments.md) to turn these hypotheses into falsifiable tests.
