# Evidence-budget pilot: results

## Verdict

The implementation works within its budget contract, but this version does
NOT demonstrate an improvement over cosine top-C with equal or proportional
quotas. Keep it experimental; do not replace the default router or present
it as a validated research contribution.

The joint heuristic had lower mean candidate recall on all three datasets.
Its paired 95% intervals versus equal/proportional quotas include zero, so
these results establish neither an improvement nor a statistically resolved
regression at this sample size. They also do not establish equivalence.

## Completed experiment

Command and exact rule: [frozen protocol](20-evidence-budget-protocol.md).
Artifact directory: `experiments/routing-study-candidates-v1/` (gitignored).

- 30 disjoint random virtual clients; seeds 11, 22, 33; 16-centroid profiles.
- SciFact: 5,183 documents, 300 queries. NFCorpus: 3,633 documents, 323 queries.
  SCIDOCS: 25,657 documents, 1,000 queries.
- 1,623 unique benchmark questions, repeated across three partitions, two
  candidate budgets and five methods: 48,690 evaluated decisions.
- Cached all-MiniLM-L6-v2, snapshot
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, max sequence length 256.
- C=3 source cap; B=6 or 12 candidate requests; final K=5 cosine reranking.
- Zero budget violations. The joint and fixed equal/proportional policies
  contacted exactly three sources and received exactly B candidates per query.
- No dataset/model downloads, training, external LLM calls or attack tests.
- All are previously inspected test sets, so this is exploratory evidence,
  NOT fresh held-out confirmation. The rule was fixed before this run and was
  not retuned after inspecting these outcomes.

## Primary result: candidate recall, B=12

Percent of judged-relevant documents recovered among the paid candidates;
averaged over questions and partition seeds. This is not answer accuracy.

| Dataset | Equal quotas | Proportional quotas | Profile-only ablation | Allocation-only ablation | Joint policy |
|---|---:|---:|---:|---:|---:|
| SciFact | 28.557% | 28.557% | 28.557% | 28.580% | 27.974% |
| NFCorpus | 6.625% | 6.599% | 6.582% | 6.596% | 6.207% |
| SCIDOCS | 7.197% | 7.197% | 7.183% | 7.232% | 7.027% |

Joint minus equal, percentage points; 10,000-resample paired query-cluster
bootstrap, averaging seeds within each query. Descriptive, unadjusted intervals:

| Dataset | Difference | 95% interval |
|---|---:|---:|
| SciFact | -0.583 | [-1.961, +0.778] |
| NFCorpus | -0.419 | [-1.111, +0.188] |
| SCIDOCS | -0.169 | [-0.462, +0.129] |

At B=6 the joint means were also lower: SciFact 27.063% vs equal 27.613%;
NFCorpus 5.021% vs 5.363%; SCIDOCS 5.610% vs 5.794%. Full metrics, all methods,
all budgets and paired comparisons are retained in summary.csv/intervals.json.

## Final Recall@5, B=12

| Dataset | Equal | Proportional | Allocation-only | Joint |
|---|---:|---:|---:|---:|
| SciFact | 27.791% | 27.791% | 27.791% | 27.407% |
| NFCorpus | 5.280% | 5.280% | 5.280% | 4.878% |
| SCIDOCS | 5.819% | 5.819% | 5.819% | 5.678% |

The tiny candidate-recall changes for allocation-only do not improve final
Recall@5 here. This matters: more candidates are not useful if the final
evidence reaching the generator is unchanged or worse.

## Is there any allocation headroom?

The offline oracle sees gold labels and finds an exact best prefix allocation.
It is a diagnostic upper bound, not an executable unsupervised routing method.

| Dataset, B=12 | Equal quotas | Best quotas within the same cosine top-3 | Best joint source/quota choice, up to 3 sources |
|---|---:|---:|---:|
| SciFact | 28.557% | 29.691% | 97.167% |
| NFCorpus | 6.625% | 7.672% | 26.315% |
| SCIDOCS | 7.197% | 9.131% | 51.019% |

Within the SAME sources, perfect quota decisions offer only about 1.13, 1.05
and 1.93 percentage points over equal quotas in this setting. The much larger
joint upper bound suggests source identification dominates the available
headroom here. It does not imply that current profiles contain enough
information to identify those sources without gold labels.

One plausible failure explanation is that centroid similarity to an already
seen passage suppresses a source that still contains useful complementary
documents. Another is that random shards have very similar relevance priors,
making proportional quotas almost uniform. These are hypotheses, not causal
findings. More feedback terms should not be added merely to fit this pilot.

## Cost and implementation boundaries

At B=12, joint allocation averaged about 1.76-1.85 ms per query in the cached
simulator, versus 1.63-1.72 ms for equal quotas. This excludes model encoding,
local index search, real transport and generation; it is NOT an end-to-end
latency measurement. All methods execute one candidate per request for this
controlled comparison. Fixed methods could batch their predetermined quotas
in a deployment and avoid some of the sequential policy's request overhead.

Mean text payloads at B=12 were roughly 14.1-18.3 KB depending on dataset;
equal candidate counts do not imply equal bytes/tokens. Full MCP wire traffic
and exact context-token budgets were not measured. No answer-quality claims
can be made from this pilot.

The live `/query/evidence` endpoint uses the existing hashing demo encoder,
not the benchmark's MiniLM. Real MCP tests check paginated transport and budget
accounting with synthetic documents; they do not transfer benchmark quality
to the live system. The existing studio and `/query` defaults are unchanged.

## Next scientific step

Verification completed: 261 Python tests, including genuine MCP subprocess
pagination and the new API path. The experiment's code/protocol and summary
hashes match their saved manifest. Budget compliance is not proof of scientific
benefit. Changes are local and uncommitted on the research branch; no GitHub
push was performed.

Read SCOUT-RAG and the budget-control paper, then design a NEW development
study with documented topic-skewed/overlapping sources and multi-evidence QA.
First check oracle headroom on that development setup. Define one improved
signal for missing evidence and freeze it before a new held-out evaluation.
Keep this negative pilot as an honest baseline. Official RAGRoute/SCOUT-RAG,
end-to-end generation and realistic transport-cost comparisons remain pending.
