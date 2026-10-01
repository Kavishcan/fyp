---
tags: [hub, research-support]
updated: 2026-09-30
---

# Dataset Strategy: What Goes Where and What We Test

Think of a client as one library. The router needs useful evidence without letting the libraries read the user's question or revealing which library mattered.

| Job | Data | How It Is Used | What We Test |
|---|---|---|---|
| Build eight main client libraries | PMC-Patients, 5,000 public summaries | Divide the same documents three ways: by topic, uneven topic mix, randomly | Does retrieval still work when evidence is distributed differently? |
| Make questions with known useful documents | PMC relevance labels, 986 queries | Keep question/relevance labels separate from local profiles | MRR, recall and comparison with matched local baselines |
| Build medical and non-medical libraries for answers | Six BEIR corpora | Three medical sources and three distractors in the latest MIRAGE run | Do retrieved passages improve answers? |
| Ask medical questions | 150 MIRAGE questions | 30 questions per subset; same questions for each condition | Accuracy and paired uncertainty estimates |
| Check if contacts reveal a topic | PMC / FeB4RAG labels | Train a contact-set attacker; use held-out examples | Topic/source prediction versus the majority-class floor |
| Check repeated questions | PMC summary snippets | Five related snippets per eligible patient | Does leakage increase from one to five questions? |
| Check identifier filtering | Fictional canaries and public text | Insert known test identifiers, run de-identification | Missed identifiers, unrelated text changes and retrieval impact |
| Check source attacks | Synthetic malicious fixtures | Compare poisoned/misleading profiles and evidence | Attack selection/citation; must rerun in blind mode before transferring claims |
| Check cost | Same sources and workloads | Measure setup and each round separately | Evaluations, opened passages, cache bytes, latency and full transport bytes |

**No model training is required for the current blind router.** It uses existing embeddings and local similarity. Profile construction is offline preprocessing, not learning a router.

**Fair comparison:** use the same corpus, query set, embeddings, ranking rule, final context limit and generation model where applicable. Report both probe/evaluation cost and final evidence budget. Candidate-budget matching alone does not equalise all work.

**Avoid data leakage:** do not tune on the reported test questions; report seeds and partition construction; keep relevance labels out of published profiles. K-means partitioning in the routing embedding can favour the method, which is why the other splits matter.

**Still needed:** common evaluation command, explicit train/validation/test roles for attack models, clinical expert review, real network costs, broader session splits. See [[Next steps]].

## Implementation / Experiment Sources

- [backend/eval/run_hyfedrag_compare.py](../backend/eval/run_hyfedrag_compare.py)
- [backend/eval/run_answer_quality.py](../backend/eval/run_answer_quality.py)
- [backend/eval/run_session_attack.py](../backend/eval/run_session_attack.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
