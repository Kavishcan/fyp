---
tags: [hub, research-support]
updated: 2026-09-30
---

# FedSafeRouter Research Vault

**Project:** Privacy-Aware Source Routing for Federated RAG: Mitigating Query and Access-Pattern Leakage.

This vault is research support, not a submission-ready literature review. Imported worksheet comments are working notes; read the primary papers and write your own assessed summaries.

| Start Here | Contents |
|---|---|
| [[Project status]] | What works, what is measured, what is still open |
| [[Research question]] | The actual problem and research question |
| [[Architecture]] | Current standalone-client pipeline |
| [[Threat model]] | Trust boundaries, observers and assumptions |
| [[Claims ledger]] | Defensible wording and limits |
| [[Dataset register]] and [[Dataset strategy]] | Real data, links, client construction and tests |
| [[Literature themes]] and [[Paper register]] | All 63 worksheet papers, grouped for reading |
| [[Research gap analysis]] | One row per distinct gap |
| [[Novelty and contribution]] | Contribution versus existing building blocks |
| [[Results index]] | Results, including negative findings |
| [[Code map]] | Where the implementation lives |
| [[Next steps]] | Prioritised research and engineering work |
| [[Source reconciliation]] | Conflicts between worksheet, old docs and code |
| [[Vault maintenance]] | Source provenance and how to update these notes |

**Current conclusion:** in the tested eight-node PMC federation, all-node blind unlock hides query content from nodes and makes the contacted-source set query-independent. At P=24, hybrid retrieval retains 96.9-98.4% of the local HyFedRAG-style hybrid baseline across three splits. This is a scoped prototype result, not complete privacy or universally superior retrieval.

Supporting maps: [[Mechanisms index]], [[Attacks index]], [[Experiments index]], [[Literature map]], [[Design timeline]], [[Future work]].
