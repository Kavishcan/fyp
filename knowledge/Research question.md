---
tags: [hub, research-support]
updated: 2026-09-30
---

# Research Question

How much do query content and query-dependent source contacts reveal in federated RAG, and can a training-free client-side design reduce both channels while retaining useful retrieval and answer quality?

1. **Query content:** text and embeddings can expose sensitive questions to sources.
2. **Source contacts:** the identity of contacted sources can reveal the topic even when content is encrypted.
3. **Supporting data protection:** authorised retrieval still requires de-identification, collection permissions and disclosure budgets.

The current intervention is [[Blind unlock]]: local cluster selection, equal padded requests to every enrolled node, cached encrypted tables, and local ranking and generation. This changes the original selective-router plan; it does not contact only three relevant hospitals.

Evaluate [[Query leakage]], [[Access-pattern leakage]], [[Session attack]], [[Robustness results]], [[Answer quality results]] and system cost together. See [[Research gap analysis]] for unresolved issues.
