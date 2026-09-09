# Roadmap

This roadmap follows the revised independent-router direction. It is ordered by
remaining work, not an assumed academic calendar. Confirm formal meeting,
submission and dissertation requirements with the supervisor.

## Current implementation

- Independent smart selector and coordinator consistency trust exist.
- Strict budgets, adaptive stopping, exclusions and trace output are tested.
- Smart API mode reaches in-process and real MCP sources.
- Legacy remains the dashboard/API default.
- The implementation was checked with 261 Python tests; the frontend contract
  remains unchanged by the separate evidence endpoint.
- Scientific benefit, formal privacy and hijacking resistance are not established.

The [evidence-budget branch](20-evidence-budget-protocol.md) adds sequential
candidate allocation, paginated MCP reads, equal/proportional controls,
ablation tests and offline oracle diagnostics. Its [first pilot](21-evidence-budget-results.md)
did not establish an improvement. Pending: a justified better evidence signal,
new development/held-out QA splits, realistic topic-skewed/overlapping sources,
official routing baseline reproduction and matched-token generation results.

The [development-selected ranking experiment](19-centered-routing-results.md)
rejected positive centering strengths; retain raw cosine as the control.
Coverage-oriented budget filling is not a new ranking algorithm. Preliminary
quality/attack studies advance milestones 3, 5 and 6, but do not complete the
official baseline reproduction, broader threat model or end-to-end evaluation.

## Next milestones

| Order | Work | Completion evidence |
|---|---|---|
| 1 | Review the selection rule and threat model with the supervisor | Agreed scope, exposure definition and research questions |
| 2 | Connect compatible semantic query/profile embeddings | Model provenance and end-to-end consistency tests |
| 3 | Freeze datasets and partitions | Manifest, qrels, source IDs, train/validation/test split and licenses |
| 4 | Run local controls and official RAGRoute comparison | Reproduction records and raw matched-query outputs |
| 5 | Evaluate smart-router quality/exposure and ablations | Curves, controls, uncertainty and negative results |
| 6 | Test trust under manipulation and benign changes | A3, bait, cold-start and reputation-reset results |
| 7 | Evaluate routing-pattern inference independently | A2 with a defensible observation model and no label leakage |
| 8 | Measure transport and scale | Real-MCP costs separated from logical-client scaling |
| 9 | Complete end-to-end evidence handling | Reranking, controlled generation and measured answer quality |
| 10 | Update studio and prepare release/report | Mode-aware UI, reproducible commands, limitations and student-written analysis |

The dashboard is a demonstration surface, not a substitute for milestones 4-8.
The current backend can be exercised without changing that UI.

## Baseline work can run separately

The smart algorithm does not wait for RAGRoute to serve queries. Scientific
comparison does require a runnable, comparable baseline. Obtain matching
upstream weights/statistics or reproduce its offline training and document any
adaptation. Training a learned comparison does not train the proposed router.

Do not assume a model for 13 upstream sources can accept arbitrary new source
identities or embedding spaces without changes.

## Scope controls

Decoys, query perturbation, HE/DP mechanisms, persistent distributed sessions and
A2A are optional future work unless a research question needs them. Keep MCP
as the current source interface. Do not expand into a general workflow product.

## Risks and responses

| Risk | Response |
|---|---|
| No advantage over simple cosine/weighted selection | Report it; revise the hypothesis rather than claiming novelty |
| Budget harms coverage | Show the trade-off and abstentions, including multi-source questions |
| Trust penalizes honest new sources | Evaluate cold starts and uncertainty settings |
| Bait or re-registration defeats consistency | Record the limitation; assess stronger identity/evidence checks |
| RAGRoute artifacts unavailable | Document access attempts and distinguish adaptation from reproduction |
| Same-domain sources are much harder | Report both partitions rather than only the easy case |
| Large datasets exceed the user's limit | Inspect local data first; do not download files above 500 MB |
| External generation discloses context | Use public data; build a controlled local option before privacy-sensitive use |

Publication is a potential outcome, not a guarantee or a fixed page-count target.
Choose a venue only after the experiment scope and evidence are clear.
