# Experiment plan

This is the evaluation plan for the independent smart router, not a report of
completed scientific results. Existing legacy sweep outputs must not be
relabelled as smart-router results.

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
