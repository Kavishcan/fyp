# Thesis planning map

Repository documents are engineering/research planning notes, not final
student-authored dissertation prose. Verify the university template and
supervisor requirements; this file does not certify chapter completion or the
state of an external literature spreadsheet.

| Chapter area | Repository material | Remaining student work |
|---|---|---|
| Introduction / problem | 01-research-gap.md, 02-proposal.md | Verify gap evidence, motivation and final scope |
| Literature review | Literature matrix plus baseline references | Read original papers and write thematic critical synthesis independently |
| Methodology | 05-experiments.md, 06-datasets.md, 10-baseline-selection.md | Justify splits, baselines, attackers and analysis |
| Requirements | 08-deployment.md | Elicitation, stakeholders, use cases, priorities and learning-outcome mapping |
| Ethics / professional practice | Deployment limitations and public-data strategy | Discuss exposure, misuse, licenses, governance and appropriate domain advice |
| Design | 03-architecture.md, 04-router-design.md | Explain actual components, trust boundaries and design alternatives |
| Implementation | 13-smart-router-implementation.md and source code | Explain the algorithm and deviations from the plan |
| Testing | Unit/integration tests and 05-experiments.md | Separate software correctness from scientific validation |
| Critical evaluation | Baseline/ablation/attack results once produced | Analyze uncertainty, failures and external feedback |
| Conclusion | Completed evidence | Bound claims and identify unresolved work |

## Core claim mapping

- Constrained adaptive selection: exact rule, strict-budget tests, matched
  retrieval/exposure curves and fixed-k comparisons.
- Trust-aware selection: coordinator consistency mechanism, A3 and benign
  cold-start tests, plus no-trust controls.
- Scalability: measured source-count/latency/communication curves, distinguishing
  local logical profiles from real MCP processes.
- Privacy: explicit exposure definition and A2 measurements; never substitute
  fewer contacts for proven secrecy or source anonymity.

## Status discipline

The independent selector and API integration are implemented and tested.
The dashboard remains legacy-oriented; semantic integration and comparative
research results remain pending. Unit-test success does not complete a
research question or establish a publishable contribution.

The earlier decoy/TASR interference narrative is an optional extension.
Do not make it the central conclusion of the current decoy-free smart router.

## Supervisor discussion

Confirm the revised independent-router scope, threat model, dataset manifests,
required comparators and what counts as sufficient evidence. Agree the writing
and review schedule against actual submission dates rather than an inferred
nine-month calendar.
