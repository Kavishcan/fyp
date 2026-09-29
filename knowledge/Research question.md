---
tags: [hub, type/concept]
---

# Research question

> To what extent do source-routing decisions in [[Federated RAG]] reveal the query — its content to contacted sources, and its topic to an observer of the contact pattern — and can privacy-aware routing reduce both leaks while preserving retrieval, answer quality and efficiency?

Two leaks:
1. [[Query leakage]] — a contacted hospital reads the question.
2. [[Access-pattern leakage]] — *which* hospitals are contacted reveals the topic.

Supporting (hospital-side) protection: [[Node-side de-identification]], [[Role-based access]], [[Credential gate]].

Answer (docs/47, 50, 51): [[Blind unlock]] removes both leaks under the [[Threat model]]; retrieval cost depends on the probe budget P ([[Robustness results]]).
