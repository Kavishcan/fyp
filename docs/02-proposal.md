# Proposal planning notes

**Working title:** Training-Free Exposure-Constrained and Trust-Aware Adaptive
Source Routing for Scalable Federated Retrieval-Augmented Generation.

These notes support design and supervisor discussion. They are not final
student-authored dissertation prose or a verified literature review.

## Problem and aim

Distributed knowledge sources should not all receive every question.
Source selection must balance relevant evidence, the cost of disclosing a query
to additional recipients, and uncertain or misleading source profiles.

The aim is to design and evaluate an independent training-free router that
selects a useful subset under an explicit exposure budget. Healthcare is the
intended public-data case study, not a clinically validated deployment.

## Intended contribution

One coherent algorithmic contribution: adaptive, trust-aware source selection
under a strict contact-exposure budget, supported by a reproducible evaluation.
RAGRoute is a comparator, not a dependency of the proposed selection rule.

The first implementation uses centroid similarity, profile-overlap penalties,
uncertainty-adjusted consistency trust and greedy gain-per-cost selection.
Each ingredient is established; novelty and benefit of the combined method
must be checked against existing methods and simple ablations.

## Research questions

| ID | Question | Required evidence |
|---|---|---|
| RQ01 | What retrieval/exposure trade-off does constrained adaptive selection achieve against fixed-k and published source routers? | Matched-query quality, coverage, recipient counts and budget curves |
| RQ02 | How does profile-consistency trust affect manipulation resistance and honest-source access? | A3, bait/profile-change/cold-start tests and no-trust controls |
| RQ03 | How do routing-pattern inference and system costs change with constraints and source scale? | A2, timing/communication measurements and explicit simulated/real transport splits |

Reduced recipient exposure is not presumed to improve routing-pattern secrecy.
An unfavorable or null result should be reported rather than hidden.

## Objectives

1. Verify the literature gap and define adversaries, protected assets and trust boundaries.
2. Freeze query splits, source construction, embeddings, costs and evaluation labels.
3. Implement and test the independent constrained selector.
4. Reproduce comparable controls and the official RAGRoute baseline.
5. Evaluate thresholds, trust uncertainty, centroid aggregation and overlap ablations.
6. Measure attacks and costs separately from answer quality and unit-test correctness.
7. Demonstrate the method through existing MCP/in-process retrieval and document limits.

Objective 3 has a first tested implementation. The others require evidence;
do not mark them complete because modules or dataset files exist.

## Scope

Included: source profiling, pre-dispatch adaptive selection, exposure accounting,
coordinator-observed trust, routing attacks, baseline comparison and a FedRAG
demo. No task-specific ML training is required by the proposed router.
Pretrained semantic embeddings remain compatible with that scope.

Outside the current implementation: production authentication, signed identity,
formal DP or encrypted retrieval, end-to-end query secrecy, clinical deployment,
and a 1,000-server distributed deployment. Smart mode has no decoys or query
perturbation; the old mechanisms remain separate legacy experiments.

Generation is an optional downstream component, not the research contribution.
The live external-provider option exposes its prompt; local generation for a
controlled evaluation remains planned.

## Main risks

- Overlap can suppress distinct useful documents held by similar sources.
- Low initial trust can exclude legitimate new sources.
- Matching bait text can satisfy profile-consistency checks.
- Re-registration resets reputation; identities are not bound cryptographically.
- Budget reduction may hurt recall or make source identity easier to infer.
- Cross-domain partitions may make routing unrealistically easy.
- Existing routing work may already cover parts of the proposed combination.

See [architecture](03-architecture.md), [algorithm](04-router-design.md),
[experiments](05-experiments.md) and [roadmap](07-roadmap.md).
