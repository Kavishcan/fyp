# Anchored feedback: development and exploratory transfer results

## Verdict

The targeted follow-up is implemented and tested, but positive feedback was
NOT selected by the predeclared development criterion. The winning strength
was alpha=0: no feedback, equivalent to cosine top-C with equal quotas.
There is no new demonstrated retrieval advantage. Keep the failed alternatives
as experimental controls and use `method=equal` for the simple reference path.

The change was motivated by [query-level failure attribution](23-query-failure-analysis.md).
It replaces residual-profile suppression with anchored query refinement only
for source selection, using already-paid passages. Equal quotas, raw node
queries and final cosine ranking remain fixed. This is a pseudo-relevance-
feedback experiment, not a claim of missing-fact detection or novel PRF.

## Development selection

Fixed before execution: [protocol](24-feedback-routing-protocol.md).
807 SciFact train questions plus 323 NFCorpus dev questions, normalized-text
overlap with historical test queries removed, three partition seeds, C=3,
B=12, K=5, alpha in {0, 0.1, 0.25, 0.5}. No model weights were trained, but
alpha selection is supervised hyperparameter tuning on development judgments.

Candidate recall, percent; macro gives each dataset equal weight:

| Strength | SciFact development | NFCorpus development | Macro |
|---|---:|---:|---:|
| 0 | 28.544% | 6.036% | 17.290% |
| 0.1 | 28.076% | 6.146% | 17.111% |
| 0.25 | 27.129% | 6.354% | 16.742% |
| 0.5 | 25.993% | 6.012% | 16.002% |

Moderate feedback helped NFCorpus development but hurt SciFact more. Do not
describe every positive setting as worse on every dataset. A per-dataset
parameter was not selected: it was not part of the predeclared protocol.
Across 13,560 development decisions, there were zero budget violations.

## Frozen exploratory evaluation

Alpha=0 was saved with code/protocol/development hashes before a separately
invoked test run. Historical SciFact (300 questions), NFCorpus (323) and SCIDOCS
(1,000), three seeds, four methods, C=3/B=12/K=5: 19,476 decisions.

These test questions had ALREADY been inspected and informed the diagnosis.
This is exploratory transfer/regression, not an untouched held-out confirmation.
No parameter was changed after observing these test results.

| Dataset | Equal candidate recall | Frozen feedback candidate recall | Equal/frozen final Recall@5 |
|---|---:|---:|---:|
| SciFact | 28.557% | 28.557% | 27.791% |
| NFCorpus | 6.625% | 6.625% | 5.280% |
| SCIDOCS | 7.197% | 7.197% | 5.819% |

All 4,869 feedback/equal query-partition pairs had identical source selections,
quotas and final document IDs. Paired differences in candidate/final/source
recall are zero, with [0,0] bootstrap intervals. This is baseline equivalence
by construction at alpha=0, NOT a successful new algorithm.

All 14,607 rerun equal/proportional/old-joint control cases reproduced the saved
original candidate recall, final recall, source recall, contacts, requests and
final document IDs exactly. Timing is not expected to reproduce exactly.

All methods respected the client and candidate caps. Across development and
test stages combined: 33,036 decisions, zero budget violations. No downloads,
external LLM calls, model training, or new profiles were required.

## Cost and scope

The frozen feedback code still executes the selection-phase machinery even
when alpha=0. Cached allocation time was about 1.90-2.06 ms versus 1.61-1.72 ms
for the direct equal baseline. There is no reason to pay that overhead when
the outputs are identical; prefer the explicit equal method for this control.
These times exclude embeddings, local search, MCP transport and generation.

The API and real MCP pagination path support positive feedback for experimentation.
The live API still uses hashing, not MiniLM; the semantic benchmark's quality
does not automatically transfer. The API's illustrative default feedback
strength 0.25 is not the selected setting: explicitly use `method=equal` or
`method=feedback, feedback_strength=0` for the development-selected behavior.
The overall API/studio defaults have NOT changed.

There are no answer-quality, true multi-hop completeness, attack-resilience,
privacy or 1,000-live-client claims from these experiments.

## Artifacts

- `experiments/routing-study-diagnosis-v1/`: 14,607 detailed query rows,
  document-level attribution, helped/hurt examples and readable report.
- `experiments/routing-study-feedback-dev-v1/`: all development decisions,
  per-dataset summary, selection criterion and frozen alpha.
- `experiments/routing-study-feedback-test-v1/`: frozen comparison decisions,
  paired intervals and input/code/protocol provenance.

All directories are gitignored alongside the cached corpora. This tracked
report records the outcome; no older experiment output was overwritten.

Verification: 300 Python tests passed, including real MCP pagination with the
feedback method and selection-freeze checks. TypeScript checking and
`git diff --check` passed. Follow-up changes are local and uncommitted on
`research/evidence-budget-routing`; no commit or push was performed in this turn.

## What should happen next

Do not add more coefficients to fit these historical test queries. First
establish whether realistic topic-based client profiles carry enough source
information, using a separately designed development benchmark and richer
profile controls. Retain random shards as a control instead of dropping the
setting that produced negative results. An untouched multi-evidence QA test,
official baseline reproduction and matched-token answer evaluation are still
pending. The implementation work is useful; a superior research method is
not yet established.
