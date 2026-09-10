# Reading pack: budgeted federated evidence retrieval

This is the complete recommended starting pack for the current implementation,
not an exhaustive survey or a claim that all papers identify the same gap.
Read the first eight closely, then the remaining groups as needed. Links identify
primary papers; preprints are not automatically peer-reviewed publications.
These are reading questions, not literature-review summaries to submit as your
own. Write your own notes after reading the methods and experiments.

## Priority 1: read these eight first

| No. | Paper and primary link | What to extract in your own notes |
|---|---|---|
| 1 | [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries (1998)](https://www.cs.cmu.edu/~jgc/publication/MMR_DiversityBased_Reranking_SIGIR_1998.pdf) | Relevance versus redundancy; the exact greedy rule. Why document diversity is established prior art, not our novelty. |
| 2 | [MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop Queries (2024)](https://arxiv.org/abs/2401.15391) | How questions and supporting evidence are constructed; null questions; why retrieving a gold document does not guarantee retrieving its supporting fact. |
| 3 | [Dense X Retrieval: What Retrieval Granularity Should We Use? (EMNLP 2024)](https://aclanthology.org/2024.emnlp-main.845/) | Effects of document/passage/proposition granularity; what is counted as a retrieval unit and as context cost. |
| 4 | [Fair and Budget-Controlled Federated Retrieval-Augmented Generation for Open-Domain QA (2026)](https://doi.org/10.1109/ICICC71012.2026.11637874) | Candidate budget before global reranking; distinction between source contacts, returned passages and final context. Full text was provided in this project chat. |
| 5 | [Efficient Federated Search for Retrieval-Augmented Generation / RAGRoute (2025)](https://arxiv.org/abs/2502.19280) | Offline classifier training, source features, source-selection decisions and reported communication accounting. Our cosine/fusion controls are not this implementation. |
| 6 | [FeB4RAG: Evaluating Federated Search in the Context of Retrieval Augmented Generation (2024)](https://arxiv.org/abs/2402.11891) | Resource selection versus result merging; benchmark judgments; differences from our 49-source MultiHop corpus. |
| 7 | [Federated Retrieval Augmented Generation for Multi-Product Question Answering (2025)](https://aclanthology.org/2025.coling-industry.33/) | How MKP-QA combines domain and passage relevance; training requirements; cross-product QA evaluation. |
| 8 | [RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation (2024)](https://arxiv.org/abs/2408.08067) | Separate retrieval and generation failure measures; fact-level checking versus parent-document recall. |

## Priority 2: positioning and stronger comparisons

| No. | Paper and primary link | What to check |
|---|---|---|
| 9 | [SCOUT-RAG: Scalable and Cost-Efficient Unifying Traversal for Agentic Graph-RAG over Distributed Domains (2026 preprint)](https://arxiv.org/abs/2602.08400) | Overlap with adaptive domain breadth and traversal depth. Explain graph versus text retrieval and actual budget differences before claiming novelty. |
| 10 | [Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods (2009)](https://doi.org/10.1145/1571941.1572114) | Rank fusion formula and constants; distinguish original unweighted RRF from our weighted source-ranking adaptation. |
| 11 | [Searching Distributed Collections With Inference Networks (1995)](https://sigir.org/wp-content/uploads/2017/06/p160.pdf) | Classical collection representations, resource selection and result merging. Source profiles and inverse collection frequency have long-standing prior art. |
| 12 | [HyFedRAG: A Federated Retrieval-Augmented Generation Framework for Heterogeneous and Privacy-Sensitive Data (2025 preprint)](https://arxiv.org/abs/2509.06444) | Heterogeneous data types and distributed pipeline; which parts differ from our source/passage selection problem. |
| 13 | [Privacy-Preserving Federated Embedding Learning for Localized Retrieval-Augmented Generation / FedE4RAG (2025 preprint)](https://arxiv.org/abs/2504.19101) | Distinguish embedding learning from source routing. Background positioning, not a direct implementation-equivalent local-diversity baseline. |
| 14 | [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models (2021)](https://arxiv.org/abs/2104.08663) | Transfer across domains and retrieval metrics; why a win on a repeatedly inspected dataset is insufficient. |

## Priority 3: retrieval, answer evaluation and adaptive RAG

| No. | Paper and primary link | What to check |
|---|---|---|
| 15 | [Dense Passage Retrieval for Open-Domain Question Answering (2020)](https://arxiv.org/abs/2004.04906) | Query/passage embedding spaces, retrieval supervision and candidate evaluation. |
| 16 | [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (2020)](https://arxiv.org/abs/2005.11401) | Foundational retrieval/generation distinction; why better retrieval must be validated downstream. |
| 17 | [Lost in the Middle: How Language Models Use Long Contexts (2023 preprint; later published)](https://arxiv.org/abs/2307.03172) | Context order and length as confounders when comparing generated answers. |
| 18 | [Ragas: Automated Evaluation of Retrieval Augmented Generation (2023 preprint; EACL 2024 demo)](https://arxiv.org/abs/2309.15217) | Faithfulness and answer relevance; judge assumptions and costs. Not a replacement for labeled evidence recall. |
| 19 | [ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems (2023 preprint; later published)](https://arxiv.org/abs/2311.09476) | Automated evaluation calibration and human-labeled checks. Avoid treating an LLM judge as unquestionable ground truth. |
| 20 | [Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity (2024)](https://arxiv.org/abs/2403.14403) | Query-dependent retrieval strategies; distinguish learned complexity routing from our frozen source fusion. |
| 21 | [Corrective Retrieval Augmented Generation (2024 preprint)](https://arxiv.org/abs/2401.15884) | Reliability checks and corrective retrieval; how any extra retrieval would fit a strict budget. |

## A small note template for every paper

1. What exact decision does it make: source, passage, depth, reranking or generation?
2. What information is available before contacting a source?
3. What is trained, fitted or tuned, and on which split?
4. What resource is constrained: contacts, local work, candidates, tokens or latency?
5. Which experiment is most relevant to our implementation?
6. What limitation is explicitly reported, and what limitation is only my inference?
7. Which page/section supports my comparison?

Do not force 20 papers to state one gap. A defensible gap requires careful
comparison against the closest methods, not a numerical citation threshold.
MCP/A2A protocol documentation belongs in implementation references, not a claim
that connecting tools creates algorithmic novelty. The current non-privacy
experiment does not require expanding the privacy reading list again.

Primary records checked on 2026-09-10 or in the preceding project verification.
The Fair/Budget paper was read from the supplied full text; its DOI is retained.
Use each primary record's full author list when constructing final Harvard
citations; this reading checklist intentionally identifies papers by title.
