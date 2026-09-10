# Start here: implementation status and next steps

Updated 2026-09-10. Read this file instead of replaying the full chat. Read
[the 21-paper pack](32-focused-reading-pack.md) only when literature is needed.

## Project and scope

- Repository: `/Users/jimmy/DEV/FYP/fyp`.
- Branch: `research/evidence-budget-routing`.
- Current experiment: fixed-budget source routing plus document-aware local
  passage retrieval. Not a proven novel, universally superior or private system.
- Keep the hybrid source router frozen at lexical weight .25, C=3 contacts,
  B=12 candidate requests, equal quotas and final cosine top-5.
- No model training, new downloads, paid API calls or generated-answer evaluation
  were performed in this step. Existing runtime defaults remain unchanged.

## What was implemented

`backend/nodes/document_retrieval.py` provides four local retrieval policies:

| Policy | Behavior |
|---|---|
| cosine | Preserve existing relevance order. Default. |
| parent_cap1 | Promote the highest-ranked chunk per document, then backfill repeated-document chunks. |
| parent_cap2 | Promote up to two chunks per document, then backfill. |
| mmr | Greedy relevance/redundancy reranking, cosine similarity, weight .7. |

All rerank the first 64 local candidates and preserve the remaining tail.
Parent caps are soft, not hard deletion: small collections still return their
remaining chunks. One deterministic order supports stable offset pagination.
Internal source computation is extra work, not an extra remote query.

Integration exists in `nodes/simulator.py` and `nodes/mcp_server.py`. A source
spec can opt in using:

```json
{
  "node_id": "example",
  "documents": ["First chunk of A", "Second chunk of A", "First chunk of B"],
  "parent_document_ids": ["document-a", "document-a", "document-b"],
  "local_retrieval": {"method": "parent_cap1", "pool_size": 64}
}
```

Documents here are indexed chunks. Parent IDs must come from ingestion, not
be inferred from query relevance. Missing/misaligned parent IDs are rejected
for parent-cap modes. Existing specs without these settings retain cosine.
MCP response shape and source-profile scoring remain unchanged. Runtime uses
hashing embeddings; benchmark quality uses cached MiniLM, not the live encoder.

## Measured result

Ran all four policies against all seven frozen routers on the exact saved
MultiHop corpus: 49 sources, 609 documents, 9,675 chunks, 2,556 questions.
Document metrics use 2,255 evidence-labeled questions; 301 null questions are
run but excluded from those denominators. Every policy keeps the same sources
as its cosine counterpart. Cosine reproduces previous per-query final IDs and
recall. Across 71,568 decisions, there were zero budget violations.

Hybrid router, same C/B/K:

| Local policy | Candidate document recall | Final document recall | All required documents in final context |
|---|---:|---:|---:|
| Cosine | 62.54% | 50.89% | 21.24% |
| One-chunk promotion | 72.56% | 59.21% | 31.09% |
| Two-chunk promotion | 65.40% | 53.33% | 24.66% |
| MMR, weight .7 | 63.00% | 54.30% | 24.70% |

For parent_cap1, final recall rises 8.32 percentage points, exploratory paired
95% interval [7.59, 9.05]. There are 460 query wins, 1,795 ties and no losses
on this parent-document metric. MMR has 342 wins and 151 losses on final recall.
Mean distinct documents in five hybrid chunks rises from 3.50 to 4.94 under
parent_cap1. Mean chunk query cosine falls from .5854 to .5673.

Fair comparison after applying parent_cap1 to everyone:

| Router | Candidate document recall | Final document recall |
|---|---:|---:|
| Semantic16 | 64.58% | 56.62% |
| Semantic21 | 69.50% | 57.49% |
| Lexical / development-selected weighted RRF | 62.99% | 51.33% |
| Unweighted RRF | 73.30% | 58.67% |
| Hybrid | 72.56% | 59.21% |
| Development-selected min-max | 73.71% | 59.07% |

This is a SHARED LOCAL RETRIEVAL improvement. Hybrid does not win candidate
recall. Its final advantage over min-max is just .14 points, not a demonstrated
router-specific breakthrough. Parent-document metrics favor removing duplicates;
zero document-recall losses do not prove no useful supporting chunks were lost.
Questions share articles, the dataset was previously inspected, and intervals
are descriptive and not multiple-comparison adjusted. No new held-out claim.

Measured mean local reranking time per uncached source/policy computation:
cosine .020 ms, parent_cap1 .246 ms, parent_cap2 .240 ms, MMR .299 ms. This excludes
dense scoring/sorting, embedding, IO and generation. Simulator caching is reused
across methods; these are NOT end-to-end or real-MCP latency measurements.

Verification: 341 Python tests passed, including a real MCP subprocess test.
Code/artifact hashes match the completed manifest; `git diff --check` passed.
No automatic promotion to the default, commit or push was performed.

## Where the evidence lives

- Frozen protocol: [30-local-retrieval-protocol.md](30-local-retrieval-protocol.md).
- Runner: `backend/eval/run_local_retrieval_study.py`.
- Tests: `backend/tests/test_document_retrieval.py`.
- Results: `experiments/routing-study-local-retrieval-v1/`:
  `manifest.json`, `summary.csv`, `comparisons.json`, `local-costs.json`,
  `decisions.jsonl` and `snapshot/`.
- Earlier baseline/answer preparation: [29-strong-controls-results.md](29-strong-controls-results.md).
- Experiment directories are Git-ignored; preserve them separately when sharing.

## Next tasks, in order

1. **Measure actual supporting-fact coverage.** The local raw file
   `/Users/jimmy/DEV/FYP/fedrag-dataset/data/raw/multihop/MultiHopRAG.json`
   contains `evidence_list` entries with `fact`, `url` and `title`. Map these
   to processed parent documents, then determine whether selected chunks contain
   the supporting fact. Audit unmatched/paraphrased facts manually; exact-string
   matching alone is not a definitive semantic metric. Labels must stay in the
   evaluator, never in retrieval, routing or inference-time stopping rules.

2. **Run a small real answer experiment.** Choose/configure one generator locally.
   The old 192 requests in `routing-study-answer-pilot-v1` use the OLD retrieval
   policies. Do not reuse them as document-aware results. Prepare paired cosine/
   parent_cap1 prompts for the same questions and token cap, with a no-retrieval
   control; never include gold references. Use the existing strict answer scorer
   plus a manually checked faithfulness/sample-error audit. Generation is pending
   because no cached generator or API key was available. Do not paste keys in chat.

3. **Validate outside the inspected dataset.** Freeze the local policy and select
   a new evaluation set, preferably with document-disjoint development/test
   corpora. A new split of the already inspected questions is not untouched data.
   Respect the user's 500 MB download limit. Keep all baselines under the same
   local retrieval/reranking conditions, and report null/absent-evidence cases.

4. **Run resource curves before more heuristics.** Compare source caps 1/3/5 and
   candidate budgets 6/12/24 with fixed final context constraints; include local
   candidate-pool cost and profile bytes. Report which document/fact coverage
   improvements survive at each budget. Count every attempted remote request.

5. **Only then revisit adaptive quotas or source selection.** Use the updated
   failure breakdown to justify a change. Earlier feedback/adaptive allocation
   studies failed; do not silently revive them or tune repeatedly on MultiHop.
   Official RAGRoute reproduction is still pending its model/source assets.

## Short prompt for the next coding session

> Work in `/Users/jimmy/DEV/FYP/fyp` on the existing research branch. Read
> `docs/31-next-steps-handoff.md` first and inspect Git status. Start with task 1:
> supporting-fact coverage evaluation using raw MultiHop evidence facts. Keep
> routing and retrieval frozen, preserve prior artifacts, and never expose gold
> labels to inference code. Verify fact-to-document/chunk mappings and report
> unmatched cases rather than inventing matches. Add tests and one concise new
> results/next-steps document. Do not replay the full chat, retune on inspected
> test data, download large datasets, call paid APIs or claim universal novelty.
