# Rich-profile routing: development and transfer protocol

## Hypothesis

Small centroid sets blur exact lexical distinctions. Test a compact lexical
presence sketch alongside semantic centroids, rather than continuing to add
feedback penalties to a weak profile. This is hybrid retrieval/source-profile
engineering built from established ingredients, not a claim of worldwide
algorithmic novelty. A gain over cosine alone does not establish superiority
over all federated retrieval research.

## Representation and rule (fixed before development)

- Each source publishes its 16 normalized-space centroids and an 8,192-byte
  bitset. Tokenize casefolded text into word tokens of length >=2, remove the
  existing metadata stoplist and purely decimal tokens, hash each distinct
  unigram to 16 bits using the first two bytes of SHA256 and set that bit.
- Same preprocessing for queries. Hash collisions are possible. Presence means
  "some document in this source contains a matching bucket", not co-occurrence
  in one document and not evidence verification. Hashing is not privacy.
- Across eligible published profiles, let df(h) be the number containing a
  query bucket. Ignore buckets absent everywhere or present everywhere. Weight
  the others by log((N+1)/(df(h)+1))^2 and compute each source's weighted fraction
  of matching buckets, l_i in [0,1].
- Semantic score s_i is maximum nonnegative query-centroid cosine. Hybrid score
  is (1-alpha)*s_i + alpha*l_i. At alpha=1 use semantic order to break lexical
  ties. Missing, invalid or incompatible sketches at ANY eligible source cause
  the whole query to fall back to semantic routing. No source is penalized for
  missing metadata. With no discriminative query buckets, also fall back.
- Select top three, equal quotas, B=12 candidate requests, final K=5 original-
  query cosine ranking. No query-time profile requests or free candidate probes.

## Controls

1. semantic16: 16-centroid cosine top-3, equal quotas.
2. semantic21: 21-centroid cosine top-3, equal quotas; approximate byte-matched
   dense-only profile control.
3. lexical: lexical routing with semantic tie breaking/fallback, equal quotas.
4. rrf: unweighted reciprocal rank fusion of lexical and semantic source
   rankings, constant 60, equal quotas; a standard same-information control.
5. hybrid: development-selected alpha from {0, .25, .5, .75, 1}.

For 384-dimensional float32 centroids, semantic16 is 24,576 canonical binary
bytes; hybrid is 32,768; semantic21 is 32,256 (512 bytes less). Report actual
centroid counts for small clients, canonical bytes, and serialized JSON bytes.
Base64/JSON transport is NOT the same as canonical binary size. Offline profile
publication cost must be stated separately from query contacts/candidates.

All new centroid sets use the same sklearn MiniBatchKMeans construction for
both sizes (seeded, n_init=3, max_iter=100, reassignment_ratio=0). Do not compare
new profile results to old saved centroids as if representation were unchanged.
Offline centroid fitting is unsupervised profile construction; "training-free"
here means no learned router/LLM weights, not that clustering does no fitting.

## Partitions and development

- SciFact and NFCorpus development queries from the verified existing cache
  (807/323), excluding normalized text overlap with historical tests.
- For EACH dataset use both the previous random assignment algorithm and a
  topic-skewed assignment: MiniBatchKMeans with 30 clusters over normalized
  document embeddings. Seeds 11,22,33 for both kinds. Topic partitioning is a
  benchmark construction using corpus text only, not query judgments.
- Topic clusters are simulated institutions, not naturally federated data.
  Retain random partitions as a control, do not drop the difficult setting.
- Select alpha maximizing macro candidate recall, equal weight per dataset
  and partition kind; ties prefer smaller alpha. Freeze code, protocol, inputs
  and selected alpha before transfer evaluation. This is development tuning.
- Evaluate all controls, not only the proposed mixture. Do not force a positive
  mixture if a single signal wins, or call equality a novel algorithm.

## Transfer evaluation

After freezing, load and encode the locally cached FiQA test corpus/questions
using the same cached MiniLM model/snapshot and max length 256. FiQA judgments
are NOT used to choose this method or alpha. FiQA has been used elsewhere in
the project, so describe this as a separate transfer dataset for this study,
not a guarantee that nobody has ever inspected its questions.

FiQA is finance rather than the biomedical development domains. Evaluate all
five controls on both random/topic layouts and three seeds, C=3/B=12/K=5.
Use query-cluster paired bootstrap (10,000 resamples, seeds averaged within
query); report candidate recall, final Recall@5, nDCG@5, source recall, contact/
candidate counts, profile bytes, text bytes and cached allocation time.
Intervals are descriptive and not multiplicity-corrected. No retuning after
transfer results. No LLM answer or multi-hop completeness claims.

No new dataset downloads. Use only cached model files; fail rather than fetch
missing assets. Real MCP tests validate sketch publication and retrieval, not
benchmark quality or network latency. Live hashing and offline MiniLM quality
must remain distinguished. Existing defaults and historical results remain.

## API and commands

The rich strategy is opt-in on `/query/evidence`:

```json
{"question":"Find evidence about BRCA1 mutations", "method":"equal",
 "profile_strategy":"hybrid", "lexical_weight":0.5,
 "max_sources":3, "candidate_budget":12, "final_k":5}
```

The example weight is illustrative, not the development-selected value.

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_rich_profile_study develop --output experiments/routing-study-rich-dev-v2
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_rich_profile_study transfer --output experiments/routing-study-rich-transfer-v1 \
  --frozen experiments/routing-study-rich-dev-v2/frozen.json
```
