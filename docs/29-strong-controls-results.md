# Stronger baseline audit and answer-study readiness

## Verdict

The fixed hybrid router remains competitive after development-tuning stronger
same-information controls, but is **not uniformly superior**. On FiQA topic
partitions it improves final recall over tuned min-max fusion by 0.356 percentage
points. On MultiHop-RAG its final evidence recall is only 0.096 points higher
than min-max, while its candidate evidence recall is lower. Do not change the
primary metric after seeing this trade-off or call it a universal win.

Actual LLM answer quality remains **pending**. No cached local generation model
or configured OpenAI/Gemini API key was available. No external generation calls,
model downloads, invented predictions or copied-reference answers were used.
The completed MultiHop measurements below concern retrieved evidence, not answers.

## Implementation

- `backend/baselines/profile_fusion.py`: development-tunable weighted RRF and
  min-max source-score fusion, with the same published source information.
- `backend/eval/run_strong_controls.py`: development/frozen-transfer evaluation,
  verifying and reusing earlier partitions, profiles, embeddings and inputs.
- `backend/eval/prepare_answer_study.py`: real-source MultiHop chunk retrieval
  and answer-request preparation, keeping references separate from prompts.
- `backend/eval/answer_quality.py`: offline EM/token-F1 scoring of supplied
  predictions. Rejects missing/extra/duplicate IDs and changed requests; failed
  generations count as zero rather than being silently dropped.

Runtime routing, API defaults, the studio and the earlier frozen algorithms
were not changed. These controls are evaluation adapters, not new API strategies.
See the [pre-run protocol](28-strong-controls-protocol.md).

## Development selection

Used the existing 807 SciFact and 323 NFCorpus development queries, never FiQA
or MultiHop judgments. The hybrid remained fixed at lexical weight .25.

| Control | Development grid | Selected setting | Macro candidate recall |
|---|---|---|---:|
| Weighted RRF | 5 weights x 3 rank constants | weight 1, constant 10 | 33.927% |
| Min-max fusion | 5 weights | weight .5 | 35.308% |
| Previously frozen hybrid | Previously selected from 5 weights | weight .25 | 35.724% |

Each dataset/layout group receives equal weight. Ties favor smaller weights,
then smaller rank constants. At weight 1, RRF reduces to the lexical control,
including its semantic fallback/ties; the constant then has no effect. This
endpoint is a development result, not intentional weakening of RRF. Its grid
had more configurations than the hybrid grid.

Development: 135,600 decisions. FiQA audit: 27,216 decisions. Both completed with
zero violations of C=3 source contacts and B=12 candidate requests, final K=5.
Five unchanged controls reproduced their earlier aggregate retrieval metrics
to absolute tolerance 1e-12. Counts include methods/seeds, not unique questions.
FiQA has been inspected previously: this is a stronger-baseline audit, not a
newly untouched test set.

## FiQA results

648 questions, 30 simulated sources, three seeds per layout. Percentages:

| Layout | Method | Candidate recall | Final Recall@5 |
|---|---|---:|---:|
| Random | Semantic16 | 9.710 | 8.573 |
| Random | Semantic21, approximately byte-matched | 9.882 | 8.330 |
| Random | Unweighted RRF | 10.101 | 8.873 |
| Random | Tuned RRF / lexical | 11.080 | 9.817 |
| Random | Tuned min-max | 10.956 | 9.693 |
| Random | Hybrid, fixed .25 | 11.067 | 9.804 |
| Topic | Semantic16 | 34.972 | 31.499 |
| Topic | Semantic21, approximately byte-matched | 35.354 | 31.796 |
| Topic | Unweighted RRF | 28.405 | 26.395 |
| Topic | Tuned RRF / lexical | 35.091 | 31.592 |
| Topic | Tuned min-max | 35.390 | 31.943 |
| Topic | Hybrid, fixed .25 | 35.798 | 32.299 |

Hybrid minus tuned control, percentage points with 95% paired query-cluster
bootstrap intervals; seeds averaged within query, 10,000 resamples. These are
descriptive intervals without multiple-comparison adjustment.

| Layout | Comparator | Candidate difference [interval] | Final difference [interval] |
|---|---|---|---|
| Random | Tuned RRF | -0.013 [-0.180, +0.154] | -0.013 [-0.180, +0.154] |
| Random | Tuned min-max | +0.111 [0.000, +0.257] | +0.111 [0.000, +0.257] |
| Topic | Tuned RRF | +0.707 [+0.244, +1.247] | +0.707 [+0.213, +1.268] |
| Topic | Tuned min-max | +0.407 [+0.116, +0.823] | +0.356 [+0.043, +0.780] |

Random-layout intervals include or touch zero. Topic gains are small, and the
previous byte-matched semantic21 candidate comparison remains inconclusive.
Storage trade-offs remain those in [the earlier study](27-rich-profile-results.md).
These simulator results are not network latency or answer accuracy.

## MultiHop-RAG retrieval pilot

Local processed corpus: 609 news documents, 49 source-based clients, 2,556
questions. Chunking produced 9,675 chunks from 180 MiniLM-token windows with
30-token overlap. The same cached MiniLM encoded queries/chunks. Source
assignments were preserved; no synthetic repartitioning or test tuning.

There are 2,255 evidence-labeled questions and 301 null questions. The latter
were run but excluded from evidence-recall denominators, not scored as perfect
recall. Seventeen questions require more than three gold sources, making complete
coverage infeasible under C=3; they remain in the denominator.

Each method made 3 contacts and 12 requests per question, returning 12 chunks.
17,892 decisions, zero violations. Document recall maps chunks to original IDs;
repeated chunks from one document do not earn extra gold-document credit. A chunk
from a gold document need not contain the supporting fact. Final contexts may
contain repeated parent documents.

| Method | Candidate document recall | Final document recall | All gold documents in candidates | All gold documents in final context |
|---|---:|---:|---:|---:|
| Semantic16 | 56.234% | 48.814% | 24.656% | 18.448% |
| Semantic21 | 59.401% | 49.353% | 27.140% | 18.758% |
| Lexical / tuned RRF | 53.326% | 44.372% | 23.282% | 15.920% |
| Unweighted RRF | 62.875% | 50.248% | 30.909% | 20.089% |
| Tuned min-max | 63.271% | 50.795% | 31.619% | 20.931% |
| Hybrid, fixed .25 | 62.539% | 50.891% | 31.619% | 21.242% |

Hybrid improves final document recall by 2.077 points over semantic16 but only
0.096 over min-max. Min-max wins candidate recall by 0.732 points; unweighted
RRF also exceeds hybrid candidate recall. Hybrid/min-max tie on all-candidate-
document coverage. These pilot comparisons are descriptive, not statistically
established superiority. Questions share articles and this is a previously used
project dataset, not a pristine held-out set.

Eight sources have fewer than 16 centroids. Sources contain 1-101 documents
and 8-1,781 chunks, so some profiles describe tiny collections nearly directly.
Mean canonical profile bytes/source: hybrid 31,169 versus semantic21 29,215.
This is not exactly byte-matched, 49 physical servers or a large institutional
corpus. No privacy/trust defense was evaluated.

## Answer evaluation: prepared, not measured

Selected 24 questions by SHA256(query ID), without filtering on retrieval
success. Prepared eight settings each: seven retrieval methods plus no retrieval,
totaling 192 requests. Gold answers are in a separate references file, not prompts.
All methods use the same question IDs/template.

RAG requests have at most five passages and a common 1,280 MiniLM-token cap.
Actual maximum: 904 tokens; mean across RAG requests: 871.42. These are not
generator-token counts or equally filled contexts. Use one fixed generator,
deterministic settings where supported and a common output cap. Preserve model
identity, errors and usage. Strict EM/F1 can penalize semantically correct full
sentences from the generic prompt; a separate semantic/faithfulness audit is
still needed for broader answer-quality claims.

Key artifacts in `experiments/routing-study-answer-pilot-v1/`:

- `answer-requests.jsonl`: query ID, method, prompt, chunk IDs and context counts.
- `answer-references.jsonl`: reference answers; never send this to the generator.
- `generation-status.json`: explicitly pending, zero calls made.
- `retrieval.jsonl`, `retrieval-summary.json`: actual evidence measurements.
- `manifest.json`, `frozen.json`, embeddings, chunks, profiles and code snapshot.

For a completed generator run, store one prediction per prepared query/method:

```json
{"query_id":"<prepared ID>", "method":"hybrid", "answer":"<actual model output>"}
```

Record failed calls with an `error` field and retain them in evaluation. A
generation manifest must identify `model`, `provider`, `temperature`,
`max_output_tokens`, and `requests_sha256` from the prepared manifest. These
fields support provenance checks, not proof that submitted answers are genuine;
retain original responses/run logs. Unit-test fixtures are not research outputs.

```sh
PYTHONPATH=backend .venv/bin/python -m eval.answer_quality \
  --study experiments/routing-study-answer-pilot-v1 \
  --predictions /absolute/path/to/actual-predictions.jsonl \
  --generation-manifest /absolute/path/to/generation-manifest.json \
  --output experiments/routing-study-answer-pilot-v1/answer-scores.json
```

Answer EM/F1 results will exist only after an actual authorized generation run.
Keys should be configured locally, not pasted into chat.

## Reproducibility and remaining work

Completed artifacts, ignored by Git and to be preserved separately:

- `experiments/routing-study-controls-dev-v1/`: grid results/frozen settings.
- `experiments/routing-study-controls-transfer-v1/`: FiQA summaries, intervals
  and raw decisions.
- `experiments/routing-study-answer-pilot-v1/`: evidence evaluation and ungenerated
  answer inputs.

All three completed manifests have matching frozen code hashes. Answer-study
input/artifact hashes were checked. Total: 180,708 query/configuration/seed
decisions, zero violations. Verification: 328 Python tests and `git diff --check`
passed. No frontend contract or production defaults changed.

The official RAGRoute adapter remains a stub. Local upstream `ragroute/router.py`
expects MedRAG/FeB4RAG/Wikipedia checkpoints and matching embedding/source assets
outside the checkout. No `.pt`/`.pth` routing checkpoint was found in the vendored
tree. A fusion control does not reproduce [RAGRoute](https://arxiv.org/html/2502.19280v1).

Next prerequisites: an available fixed generator; official routing-baseline
assets/reproduction; a genuinely new evaluation split; budget/profile-size curves.
Current evidence supports a competitive hybrid source-profile method with
measured trade-offs, not universal novelty or completed end-to-end superiority.
