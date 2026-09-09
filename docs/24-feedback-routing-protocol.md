# Anchored feedback experiment: fixed protocol

## Motivation and limits

The saved B=12 failure attribution shows that uncontacted sources account for
70.20% (SciFact), 86.92% (NFCorpus), and 87.18% (SCIDOCS) of gold documents for
equal quotas. These are macro-averaged fractions of ALL gold documents, not
fractions of only the missed documents. The source-miss fractions are slightly
higher under the old joint policy. Attribution is accounting, not causal proof.

Test ONE source-identification change: use paid retrieval feedback to refine
source scores, without treating semantic similarity as proof of fact coverage.
Keep equal quotas to isolate this effect. This is an established
[pseudo-relevance-feedback idea](https://nlp.stanford.edu/IR-book/html/htmledition/pseudo-relevance-feedback-1.html)
adapted to the existing federated source profiles, not a claimed new principle.
It can reinforce an irrelevant first passage and cause query drift.

## Runtime algorithm

1. Use the original normalized query q to score cached source centroids by
   maximum positive cosine. Filter authorization and invalid profiles as before.
2. Contact the highest-scoring source and request exactly its first passage.
3. From only the unique valid returned passages, compute
   v = normalize(sum_p max(0, cosine(q, p)) * normalize(p)).
4. For choosing the NEXT previously uncontacted source only, score centroids
   using q' = normalize(q + alpha*v). Do not change the raw query sent to nodes.
5. Repeat until min(C, B, eligible sources) clients have been contacted. Failed
   contacts still consume client and candidate slots. No replacement beyond C.
6. Allocate the remainder of B uniformly over those selected sources, with
   ties in the ORIGINAL query-profile score order. No subsequent quota tuning.
7. Retrieve one ranked page per charged action. Deduplicate and rank the final
   top five using the ORIGINAL query and the shared coordinator encoder.

No gold labels, uncontacted source search, remote query-time profile refresh,
or uncharged candidate preview enters the policy. At alpha=0 this yields the
same client set, quotas, candidates and final results as the equal baseline
for stable healthy sources; unit tests enforce this contract. Empty/invalid
sources and raw-response overhead remain bounded/accounted as in docs/20.

The previous five-method constant and old study outputs are preserved.
`method=feedback` is an additional opt-in API option; the existing default
remains `joint` for `/query/evidence`, and legacy for `/query`.

## Development and freezing

- No downloads, model training or new source-profile fitting.
- Reuse cached MiniLM documents/profiles and prior development query vectors:
  SciFact train 807 retained questions, NFCorpus dev 323 retained questions.
- Verify normalized query-text overlap exclusions against the historical test
  sets. Fail if cached query IDs differ from the expected retained set.
- C=3, B=12, K=5, seeds 11/22/33; alpha candidates {0, 0.1, 0.25, 0.5}.
- Select highest macro candidate recall across the TWO development datasets,
  averaging queries and seeds within each dataset. Exact ties prefer smaller
  alpha. This is hyperparameter tuning, even though no model weights are trained.
- Save selected alpha, development-result hash, protocol and runtime/harness
  code hashes before invoking a separate evaluation command.

## Evaluation

- Frozen alpha only, compared with equal, proportional and the previous joint
  policy on all SciFact/NFCorpus/SCIDOCS historical test questions and three seeds.
- C=3, B=12, K=5, same local rankings, cached embeddings and corpus partitions.
- Candidate recall is primary; final Recall@5, nDCG@5, source recall, requested
  slots, unique contacts, text bytes and cached allocator time are secondary.
- 10,000 paired query-cluster bootstrap resamples, seeds averaged within each
  question. Descriptive intervals; no multiplicity-adjusted significance claim.
- The test questions have ALREADY been inspected in earlier studies and informed
  the diagnosis. This is exploratory transfer/regression, NOT a fresh held-out
  confirmation. A genuinely untouched QA benchmark is still required.
- No adaptive parameter changes after test inspection. Retain every outcome.
- No LLM answers or end-to-end transport latency measured. At 30 random shards,
  these qrels measure relevant documents, not all required multi-hop facts.

## Reproduction and API

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_feedback_study develop --output experiments/routing-study-feedback-dev-v1
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_feedback_study evaluate --output experiments/routing-study-feedback-test-v1 \
  --frozen experiments/routing-study-feedback-dev-v1/frozen.json
```

```json
{"question":"Which evidence supports this claim?","method":"feedback",
 "feedback_strength":0.25,"max_sources":3,"candidate_budget":12,"final_k":5}
```

The API value above is illustrative, not a development-selected recommendation.
See the results for the frozen value. Hashing remains the live demo encoder;
semantic benchmark improvements would not automatically transfer to that API.
