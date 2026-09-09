# Experiment plan

The separate [candidate-budget protocol](20-evidence-budget-protocol.md) and
[completed pilot](21-evidence-budget-results.md) cover the non-privacy routing
branch. They compare joint selection/allocation against fixed controls and
ablations with matched C/B caps. Across 48,690 decisions there were no budget
violations, but the proposed policy did not improve retrieval. These historical
test sets are exploratory; a new held-out QA study remains necessary.

The [failure diagnosis](23-query-failure-analysis.md) and
[anchored-feedback follow-up](25-feedback-routing-results.md) add stage-level
attribution and a development-frozen source-refinement test. Positive strengths
were rejected by macro development recall; alpha=0 exactly reproduces equal
quotas. This is not a new successful algorithm or fresh held-out evidence.

The [rich-profile protocol](26-rich-profile-protocol.md) and
[completed results](27-rich-profile-results.md) add development-frozen hybrid
source selection, topic/random partitions, a byte-matched dense control and
same-information lexical/RRF controls. Across 80,460 decisions there were zero
budget violations. FiQA transfer improves over semantic16 but not conclusively
over semantic21 in candidate recall; lexical ties on random layouts. This is not
LLM answer evaluation, an official RAGRoute reproduction or a privacy result.

The [stronger-control audit](29-strong-controls-results.md) completes development
tuning of weighted RRF/min-max and their frozen FiQA comparisons, then an
exploratory 49-source MultiHop evidence pilot. Hybrid is competitive but not
uniformly superior; min-max wins MultiHop candidate recall. Prepared answer
requests are not answer-quality results: actual generation remains pending.

The [routing improvement protocol](16-routing-study-protocol.md) fixes the
new clean, matched-profile and cloned-profile stress comparisons before their
execution. It separates representation improvements from stopping behaviour.
The [completed results](17-routing-study-results.md) report 57,939 cases on
SciFact and NFCorpus, including negative findings and limitations.

This is the evaluation plan for the independent smart router, not a report of
completed scientific results. Existing legacy sweep outputs must not be
relabelled as smart-router results.

An initial [SciFact pilot](14-smart-router-pilot.md) is now measured: 300 unique
queries, 30 randomly partitioned sources and three partition seeds. Defaults
underperform cosine top-3 despite strict budget compliance. This is exploratory
evidence, not the completed experiment program below.

## Comparison systems

| System | Role | Important condition |
|---|---|---|
| Broadcast | All eligible sources; coverage/contact reference | Declare when it exceeds the smart budget |
| Random top-k | Weak selection control | Repeat seeds and match contact caps |
| Cosine top-k | Training-free relevance control | Same semantic profiles and aggregation where comparable |
| Official RAGRoute | Published learned source-selection comparator | Preserve upstream features, embeddings and threshold; label adaptations |
| TASR/security comparator | Published trust/attack comparison | Run actual upstream code and distinguish it from EvidenceTrust |
| SmartRouter | Proposed method | Strict budget, adaptive gain, overlap and uncertainty-adjusted trust |
| Oracle | Diagnostic qrel-based reference | Never expose test labels to deployed routing or tuning |

HERouter and DP-CR may be useful optional privacy comparisons when their exact
method/artifacts and threat boundaries are verified. Do not describe simulated
encryption or a home-grown approximation as a reproduced official method.

Published selection rules may differ from fixed top-k. Report native behaviour
and any matched-budget adaptation separately; changing RAGRoute's threshold to
top-k is an adaptation, not its unmodified result.

## Data and split controls

Freeze source manifests, corpus/document/query IDs, qrels, query splits,
embedding model/version, profile settings and seeds. Tune on validation only.
Use identical held-out queries and retrieval/generation conditions wherever
the systems' contracts allow; disclose unavoidable differences.

A first RAGRoute comparison can use the 13-source configuration in the vendored
upstream FeB4RAG mode. Larger custom partitions are separate conditions and may
require baseline retraining or adaptation. Do not conflate source counts from
the full benchmark, the upstream configuration and locally loaded demo nodes.

## Primary measurements

| Area | Measure | Interpretation |
|---|---|---|
| Source selection | Relevant-source recall, multi-source evidence coverage, selected count | Evaluate variable-size sets, not only a fixed-k rank |
| Retrieval | Recall/nDCG/MRR where qrels support them | Preserve source-to-document mappings |
| Answer quality | EM/F1 or other suitable labelled metrics, grounding/citations | Hold generator and prompting fixed; report unavailable generation |
| Exposure | Reserved/attempted recipients, irrelevant recipients, declared weighted contact cost | Not a DP budget or measured secrecy |
| Security | Malicious-source selection rate, honest-source exclusion, recovery | Include benign cold-start and profile-change cases |
| Observer privacy | A2 source/topic inference and repeated-route linkability | Independent of contact count |
| Efficiency | Routing/end-to-end latency, retrieval calls, bytes, memory | Separate actual measurements from configured costs |

Candidate recall and final recall should remain distinguishable. The current
smart selector scans eligible profiles rather than using a top-k coarse
shortlist; its candidate trace records that eligible pool.

## Required ablations

1. Equal trust and uncertainty_penalty=0: remove learned-from-observation trust effects.
2. redundancy_weight=0: remove overlap-based diminishing gain.
3. Mean versus max centroid aggregation.
4. Budget sweep, including a loose-budget reference.
5. minimum_gain sweep and a genuinely fixed-k comparison.
6. Trust threshold and uncertainty-penalty sweeps.
7. Unit versus justified heterogeneous contact costs.

Control trust state across runs: reset it for independent trials or use an
identical documented query stream. No future-query evidence or test qrels may
enter the router. A2 topic labels must come from the stated attacker knowledge,
not silently from the relevant-source answer key.

## Attack design

A3 should include forged broad profiles, copied profiles, matching bait passages,
negative-history resets and legitimate drift. Consistency trust alone may fail
these attacks; that is a result to report. Use the same malicious fraction and
query sequence across baselines.

A2 observes the explicitly allowed route identities/timing. Compare against
nonprivate controls at similar retrieval quality. A smaller route can be more
identifying; do not assume a privacy improvement.

A1 embedding inversion is only meaningful under an embedding-only observation
boundary. The live coordinator receives raw queries, so inversion resistance
cannot be claimed as protection against that coordinator.

## Scaling

Use cross-domain sources and a same-domain hard split. Evaluate the initial
13-source comparison, verified larger real-data partitions, and planned
100/300/1,000 logical-client conditions as separate experiments.

Report real MCP process counts and transport separately from in-memory routing.
The existing synthetic 1,000-profile unit test establishes only a budget/cap
invariant. It is not a latency, recall or distributed scalability result.

## Optional legacy extension

Existing sigma/m sweeps and E1-E4 decoy/TASR interference experiments belong to
the earlier legacy design. They are optional extensions, not prerequisites to
calling smart.py or evidence about its decoy-free operation. Preserve unmodified
TASR before testing decoy exemptions; label hypotheses rather than asserting a
collision must occur.

## Deliverables

Save exact code versions, model/artifact fingerprints, split manifests,
parameters, hardware, seeds, query order and raw decisions before aggregate
tables. Include uncertainty intervals across repeated trials where appropriate.

Useful figures: retrieval quality versus contact exposure, attack success versus
budget, cold-start behaviour and latency versus source count. Do not prescribe
the direction of a result before running it.

## Development-selected ranking study

The [centering protocol](18-centered-routing-protocol.md) separates official
SciFact train / NFCorpus dev selection from a frozen additional SCIDOCS test.
It reuses identical 16-centroid profiles, selects among five declared strengths,
and removes exact normalized test-text overlaps from development queries.
Selection chose zero centering: the baseline won on development.

The frozen evaluation therefore checks budget-filling parity with cosine top-k
and recovery relative to early stopping, not superiority of a new ranking.
Previously inspected SciFact/NFCorpus test results are exploratory regressions.
SCIDOCS is an additional one-pass benchmark, not an unaudited claim that nobody
has ever examined these public data. Query-cluster bootstrap intervals average
the three partition seeds before resampling. Online feedback streams remain
descriptive because their decisions are history-dependent.
