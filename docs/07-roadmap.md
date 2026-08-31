# Roadmap

Nine months. Writing runs in parallel, not at the end. Three university gates plus
a paper.

## Gates

| Gate | Approx. month | What it needs |
|---|---|---|
| **PPRS** | 2 | Proposal plus requirements specification. Rich picture, stakeholder analysis, elicitation, context diagram, use cases, FRs and NFRs by MoSCoW. **No running code required.** |
| **Interim** | 5 | Working two-node demo plus one real result: the A2 leakage number against an unprotected router. |
| **Paper** | 7 | 6 to 9 pages, RQ01 and RQ02, FeB4RAG only. Workshop or short-paper track. |
| **Final** | 9 | Full system, all curves, both datasets, the RQ03 interference result. |

Do not code for the PPRS. It is a specification document; month 1 is better spent
on baselines and the literature chapter.

## Schedule

| Month | Build | Write |
|---|---|---|
| 1 | Reproduce official RAGRoute on FeB4RAG; clone and verify Mu and Li's A3/TASR repo; save baseline outputs. | Chapter 2 literature review |
| 2 | Threat model. Instrumentation. A1 and A2 against the unprotected router. | **PPRS: Chapter 4 requirements spec** |
| 3 | Noisy profiles and query perturbation. **Noise calibration pilot.** | Chapter 3 methodology |
| 4 | Anonymity sets. HE baseline (rung 2.5). Full cost instrumentation including audit cost. | Chapter 6 design |
| 5 | Compose with TASR. Run A3. Interference experiments E1 and E2. | **Interim submission.** Chapter 7 implementation |
| 6 | E3 and E4. MultiHop-RAG and MedQA. Ablation ladder. Scaling to 100/300/1000. | Chapter 8 testing |
| 7 | Freeze code. Reproducibility pass. Release repo. | **Write and submit paper** |
| 8 | Buffer. Deployment hardening if time allows. | Chapter 9 critical evaluation. Recruit external evaluators. |
| 9 | — | Chapter 10 conclusion. Full draft, revisions, defence prep |

Month 8 as buffer is not padding. Something will break in month 4 or 5.

## Week 1 baseline gate

1. Run official RAGRoute on FeB4RAG and obtain ranked source IDs and metrics.
2. Run the routing-hijacking/TASR reference evaluation.
3. Record commits, licences, environments, commands and outputs.
4. Decide adapter, black-box or minimal-reimplementation status for each baseline.

RQ03 depends on a reproducible TASR condition. RQ01 and RQ02 remain viable if that
integration fails. Do not spend the first month rebuilding an ordinary router
before completing this gate.

Repos:

- https://github.com/sacs-epfl/ragroute
- https://github.com/Junjie-Mu/routing-hijacking-fedrag

## External evaluators

Chapter 9 requires expert evaluation with documented selection criteria and
results. Start identifying evaluators in month 5, not month 8. Candidates:
healthcare IT or information governance staff, federated learning researchers,
privacy engineers. Two to four is typical.

## Paper vs thesis

**Paper** (6 to 9 pages): RQ01 and RQ02, FeB4RAG only, ablation ladder, A1 to A3.

**Thesis**: the paper plus the full literature review, MultiHop-RAG and MedQA,
scaling study, the interference experiments, and the negative results cut from the
paper.

Target a privacy or trust-in-NLP workshop, or an IR short-paper track. Submission
status of "pending" is acceptable for the dissertation; acceptance is not required.

## Risk register

| Risk | Trigger | Mitigation |
|---|---|---|
| Perturbation collapses recall before privacy gain is meaningful | Month 3 pilot | Fall back to anonymity sets only. Weaker, still publishable. |
| A2 shows leakage is small | Month 2 | Strong adversary design makes the null result informative |
| Trust-defence repo does not run | Week 1 | Drop RQ03, keep RQ01 and RQ02 |
| Cross-domain split makes routing too easy | Month 1 | Same-domain BEIR hard split |
| Competing publication appears | Any time | RQ01 measured early is defensible regardless |
| Scope creep toward end-to-end pipeline privacy | Any time | Re-read the scope boundaries in the proposal |
| Production hardening eats research time | Months 4 to 6 | Hardening belongs in month 8 buffer only |

## Standing task

Set an arXiv alert for federated RAG routing. The papers defining this gap are
recent; treat the routing-hijacking work as emerging preprint evidence unless its
peer-reviewed status is verified. Re-check before the PPRS and paper submission.
