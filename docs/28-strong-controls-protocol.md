# Stronger controls and answer evaluation protocol

This follow-up keeps the hybrid weight fixed at .25. It tests whether the gain
survives stronger same-information fusion controls, not a claim that hybrid
retrieval is a new idea. Previous FiQA results have been seen: this repeat is a
stronger-baseline audit, not a fresh untouched test.

## Controls and selection

Use the exact saved source assignments, 16/21 centroids, sketches, MiniLM
embeddings and judgments from the completed rich-profile study. Verify input
hashes, corpus/document/query ordering and completed manifests before use.
Never rebuild more favorable profiles or tune on FiQA judgments.

- Weighted RRF: score (1-w)/(k+semantic_rank) + w/(k+lexical_rank),
  k in {10,60,100}, w in {0,.25,.5,.75,1}.
- Min-max score fusion: scale each query's source-score vector to [0,1],
  then combine with w in {0,.25,.5,.75,1}. Constant vectors map to zero.
- Endpoints reproduce semantic or lexical-with-semantic-tie-break selection.
  Intermediate rank ties use source ID, as in the previous RRF control.
- All controls use the same eligible sources and whole-query semantic fallback.
- Select each control independently on the existing SciFact/NFCorpus development
  queries, maximizing macro candidate recall across dataset/layout groups.
  Tie break: smaller weight, then smaller k. Record the full grid.
- Freeze chosen settings and code before the FiQA audit. Compare semantic16,
  semantic21, lexical, unweighted RRF, fixed hybrid and both tuned controls.
- C=3, B=12, final K=5, equal quotas, common dense local retrieval/cosine merger.
  Report mean recall and query-cluster bootstrap intervals (10,000 resamples).
  Intervals are descriptive, unadjusted for multiple comparisons.

RRF is established prior art: [Cormack, Clarke and Buettcher (2009)](
https://doi.org/10.1145/1571941.1572114). These are experimental source-level
adaptations. They are NOT an official [RAGRoute](https://arxiv.org/html/2502.19280v1)
reproduction. The vendored RAGRoute code requires external model checkpoints
and its configured embedding/source setup; the current adapter is a stub.

## Answer-quality preparation

Use the local processed MultiHop-RAG corpus (609 documents, 49 source-based
clients, 2,556 questions), not FiQA qrels as invented answer strings. Audit actual
counts and missing labels. This dataset has been used in this project previously;
describe the run as an exploratory transfer pilot, not a pristine held-out study.

Chunk source documents using the cached MiniLM tokenizer: at most 180 tokens,
30-token overlap, including the title. Embed all chunks with the same cached
MiniLM model. Build up to 16/21 centroids per source (seed 11); sketches use the
source document text. This smaller source corpus often yields fewer centroids
and may expose nearly document-level profiles; it is not comparable byte-for-byte
with the FiQA 30-source settings. Record counts and costs.

Run all seven frozen routing methods at C=3/B=12/K=5. Score document-level
candidate/final evidence recall by mapping chunks back to original document IDs,
and all-required-document coverage. Report absent/empty evidence separately;
do not call gold document coverage factual sufficiency or answer correctness.
Small sources may exhaust before their quotas; do not silently refund requests
or fabricate passages. No tuning on these questions or their answers.

Prepare a deterministic 24-question answer pilot by SHA256(query_id), without
filtering on retrieval success, plus a no-retrieval control. Same question IDs
for every method. Cap retrieved text at five passages and 256 MiniLM tokens per
passage (1,280 total); record actual counts. This is a common token cap, not equal
realized tokens, and is not the generator tokenizer. Include no gold answers in
model prompts. Save answer references separately and hash both inputs.

Generation requires an explicitly selected available model and authorization
before external API calls. No generator is downloaded automatically; no dataset
over 500 MB is downloaded. Without a generator, mark generation pending and
report retrieval evidence only. Never substitute an oracle or copied reference
for generated output. Offline scoring accepts genuine externally generated
predictions with an explicit model/run manifest and strict full ID coverage;
report normalized exact match and token F1, not semantic correctness or
faithfulness. Unit-test predictions are not scientific results.

## Commands

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_strong_controls develop --output experiments/routing-study-controls-dev-v1
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.run_strong_controls transfer --output experiments/routing-study-controls-transfer-v1 \
  --frozen experiments/routing-study-controls-dev-v1/frozen.json
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m eval.prepare_answer_study --dataset /Users/jimmy/DEV/FYP/fedrag-dataset/data/processed/multihop \
  --output experiments/routing-study-answer-pilot-v1 \
  --frozen experiments/routing-study-controls-dev-v1/frozen.json
```
