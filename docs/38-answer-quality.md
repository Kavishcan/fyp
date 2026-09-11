# E10: answer quality with local generation over PSI-dispatched evidence

## Verdict

The first answer-level result in the project. On 150 MIRAGE questions with
Qwen3.5-9B running locally through Ollama:

| Condition | Accuracy | Contacts | Medical contacts (of 3) | Passages | Generation |
|---|---:|---:|---:|---:|---:|
| closed-book (no passages) | 0.547 | 0 | 0 | 0 | 0.8 s |
| **psi** — local routing + PSI dispatch, cap 4 | **0.580** | 4 | 2.06 | 4 | 3.3 s |
| broadcast — PSI dispatch to all 8 | 0.627 | 8 | 3 | 8 | 5.8 s |

- **Query-confidential retrieval improves answers over no retrieval**
  (+3.3 points; 11 questions gained, 6 lost) with no node seeing the
  question.
- **Routing captures ~40% of the contact-everything gain at half the
  contacts and 56% of the generation time.** The shortfall is routing, not
  privacy: psi placed 2.06 of the 3 medical nodes in its 4 contacts on
  average; broadcast always has all 3.
- **The gain is where evidence is the answer.** pubmedqa +13 and bioasq +10
  points under psi (literature yes/no questions against literature
  corpora); medqa unchanged; medmcqa and mmlu-medical −3 (memorised-
  knowledge MCQ where passages distract).

| Subset | n | closed-book | psi | broadcast |
|---|---:|---:|---:|---:|
| pubmedqa | 30 | 0.200 | 0.333 | 0.367 |
| bioasq | 30 | 0.433 | 0.533 | 0.633 |
| medqa | 30 | 0.633 | 0.633 | 0.700 |
| medmcqa | 30 | 0.667 | 0.633 | 0.633 |
| mmlu-medical | 30 | 0.800 | 0.767 | 0.800 |

**Read the size honestly.** 150 questions give roughly ±8-point 95%
intervals on the overall figures, so the +3.3 is suggestive and the +8.0 is
likely real; the per-subset pattern (literature questions gain, knowledge
questions do not) is the robust finding. One model, one seed, one run.

## Setup

`eval/run_answer_quality.py`. Questions: 30 per MIRAGE subset (medqa,
medmcqa, pubmedqa, bioasq, mmlu), seed 11, from
`vendor/ragroute/data/benchmark/MIRAGE.json`. Nodes: 8 in-process sources —
medical nfcorpus, scifact, trec-covid and distractors fiqa, arguana,
scidocs, dbpedia-entity, webis-touche2020 — 1,500 documents each sampled as
in docs/36, `BAAI/bge-base-en-v1.5`, PSI cluster tables as docs/35–36.
Routing: `select_dispatch`, cap 4, `genuine_k=2`, `coarse_k=12`. Retrieval:
`nprobe=2`, one passage per contacted node after device-side rerank.
Generation: Ollama `qwen3.5:9b`, thinking off, temperature 0, the fixed
prompt in `generation/base.py` with the MCQ options appended and "reply with
the single option letter". Accuracy is exact match on the parsed letter; a
reply with no option letter is scored wrong and counted as abstained (≤1.3%).

The same PSI retrieval feeds psi and broadcast, so their difference is
routing; the difference from closed-book is retrieval. Nodes are in-process
(no MCP) so that the 150 × 8 contacts run in minutes; the protocol code is
the one measured over MCP in docs/36–37.

## What this does not establish

- Comparability with MIRAGE's published numbers: those retrieve from
  MedRAG's PubMed/textbook corpora, which are not here. Every retrieval
  condition is equally handicapped by the BEIR samples.
- Statistical separation between psi and closed-book (see intervals).
- Anything about a hosted model, a smaller local model, or more than one
  passage per node — single configuration.
- Groundedness or citation correctness: only the option letter is scored.
- Privacy of generation beyond "it ran on localhost"; no output-leakage test.

## Reproduce

```
LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3.5:9b python -m eval.run_answer_quality \
  --per-subset 30 --distractors fiqa arguana scidocs dbpedia-entity webis-touche2020 \
  --max-nodes 4 --top-per-node 1
```

Tests: `tests/test_answer_quality.py`. Test counts are not answer-quality results.
