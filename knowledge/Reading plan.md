---
tags: [hub, research-support]
updated: 2026-09-30
---

# Reading Plan

## Read First: Closest Architecture and Threat Models
- P01 RAGRoute: routing benefits and information exposed to sources.
- P11 C-FedRAG: confidential computing trust boundary and evidence flow.
- P12 FRAG, P53 RemoteRAG, P54 Private-RAG, P55 SCOUT-RAG, P59 PIR-RAG: private retrieval scope and leakage assumptions.
- P61 Tiptoe and [[Pointing the Way]]: private-search architecture, setup cost and disclosure control.
- P08 HyFedRAG and P03 FedE4RAG: distinguish heterogeneous retrieval from federated embedding training.
- P21 routing hijacking and P50 PoisonedRAG: integrity threats and attacks.
- P62 budget-controlled FedRAG: fair candidate comparisons versus contact/evaluation/disclosure budgets.

## Then: Benchmark and Evaluation
P13 FeB4RAG; P29 BEIR; P39 MIRAGE; P06 Ragas; P37 ARES; P38 RAGChecker; P63 RealRoute.

## Then: Theory and Breadth
[[Kiss et al 2017]], [[Chen-Laine-Rindal 2018]], [[Privacy Pass and anonymous tokens]], P48 secure aggregation, P49 DP-SGD, P10 mapping study, P56 security/privacy survey.

For each paper record: adversary, trusted component, plaintext/embedding flow, visible metadata, protected input, authorised outputs, setup/online cost, dataset and tested failure. Do not infer absence of a feature from its abstract alone.

Find all citations and original worksheet links in [[Paper register]].
