---
tags: [hub, research-support]
updated: 2026-10-05
---

# Research Question

How much do query content and query-dependent source contacts reveal in federated RAG, and can a training-free client-side design reduce both channels, and control how much source content is released, while retaining useful **retrieval** quality? (Answer generation is out of scope since 2026-10-02.)

1. **Query content:** text and embeddings can expose sensitive questions to sources.
2. **Source contacts:** the identity of contacted sources can reveal the topic even when content is encrypted.
3. **Source-content exposure:** authorised retrieval still releases records; measured and controlled by de-identification, permissions, budgets and cluster granularity × P ([[Source-content exposure]]).

The current intervention is [[Blind unlock]]: local cluster selection, equal padded requests to every enrolled node, cached encrypted tables, and local ranking and generation. This changes the original selective-router plan; it does not contact only three relevant hospitals.

Evaluate [[Query leakage]], [[Access-pattern leakage]], [[Session attack]], [[Robustness results]], [[External baselines results]], [[Release results]] and system cost together. See [[Research gap analysis]] for unresolved issues.
