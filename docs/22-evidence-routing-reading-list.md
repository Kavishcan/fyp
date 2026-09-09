# Reading plan for evidence-budget routing

These are reading prompts and implementation notes, not literature-review
paragraphs to submit as your own. Read the methods and write your own account
of what each paper does, which resources it counts, and what remains untested.

## Read first, in this order

| Order | Paper | What to extract for this project |
|---|---|---|
| 1 | [Fair and Budget-Controlled Federated Retrieval-Augmented Generation for Open-Domain QA](https://doi.org/10.1109/ICICC71012.2026.11637874) | Sections III-C, IV and VI: candidate budget before global reranking, fixed local quotas and future query-aware allocation. Distinguish B candidates, C contacted clients and final K chunks. |
| 2 | [SCOUT-RAG: Scalable and Cost-Efficient Unifying Traversal for Agentic Graph-RAG over Distributed Domains](https://arxiv.org/html/2602.08400v1) | The closest conceptual overlap: training-free relevance, incremental evidence feedback and adaptive breadth/depth under cost constraints. Explain a narrower difference before claiming novelty. |
| 3 | [Efficient Federated Search for Retrieval-Augmented Generation (RAGRoute)](https://arxiv.org/html/2502.19280v1) | Source-profile features, offline classifier training and inference-time selection. Identify which clients are contacted and whether passage quotas vary. This repo's cosine controls are NOT RAGRoute. |
| 4 | [Federated Retrieval Augmented Generation for Multi-Product Question Answering](https://aclanthology.org/2025.coling-industry.33/) | Domain routing, stochastic gating, local retrieval and cross-domain result merging. Distinguish trained domain selection from training-free inference rules. |
| 5 | [FeB4RAG: Evaluating Federated Search in the Context of Retrieval Augmented Generation](https://arxiv.org/abs/2402.11891) | Resource selection and result merging; follow its references to older federated IR methods before claiming resource allocation is new. Check what the judgments and oracle actually measure. |
| 6 | [Summarization: (1) Using MMR for Diversity-Based Reranking and (2) Evaluating Summaries](https://aclanthology.org/X98-1025/) | Relevance versus redundancy. Our residual-profile heuristic is not the MMR formula, but novelty/diversity scoring is longstanding prior art. |
| 7 | [MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop Queries](https://arxiv.org/abs/2401.15391) | Questions, supporting evidence and multi-hop labels. Plan how to partition its corpus without changing the gold support relationships. Do not confuse repeated relevant documents with required multiple facts. |

## Read next

| Paper | Purpose |
|---|---|
| [HyFedRAG](https://arxiv.org/abs/2509.06444) | Understand heterogeneous SQL/KG/text clients, local representations and caching. Heterogeneity and MCP integration alone are not this algorithm's novelty. |
| [RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation](https://arxiv.org/abs/2408.08067) | Plan separate retrieval and answer-level diagnostics. Candidate recall is not generation correctness or completeness. |

The Fair/Budget paper's full text was supplied by the user; the DOI identifies
the publication. Its future-work recommendations motivate a question, not a
proof that nobody has already addressed it. The remaining links were checked
against primary paper/author records on 2026-09-09.

## Five questions to answer in your own notes

1. Does the method choose clients, retrieval depth, or both?
2. What does it know before contacting a client? Does gathering that information
   require extra requests or reveal document contents?
3. Does the budget count clients, requests, candidates, tokens, time, or money?
4. How does it detect missing evidence, and can that signal be wrong?
5. Which experiment would distinguish our method from this one at equal cost?

## Read the negative result too

[The first implementation report](21-evidence-budget-results.md) found no gain
over the fixed controls. It is important to understand that result before
adding more heuristic terms. This implementation is a testable starting point,
not evidence that the proposed FYP contribution has already been demonstrated.
