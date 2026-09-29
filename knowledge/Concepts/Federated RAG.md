---
tags: [type/concept]
---

# Federated RAG

Retrieval-augmented generation over data held by several independent owners (hospitals) that do not pool their data.

Two families:
- **Training-time** federation — clients jointly train retrievers/generators (FedAvg); main leak = gradients. The framing of the [[RAG security survey]].
- **Query-time** federation — *this project*: nothing is trained; each question is routed to silos at answer time. Main leaks = [[Query leakage]] and [[Access-pattern leakage]].

Why [[Blind unlock]] is still federated although ranking runs on the [[Device]]: each hospital keeps cryptographic control — per-box, per-role, rate-limited, audited, revocable ([[Key epochs and rotation]]). Whoever ranks must see the question, so ranking moves to the device.

Related: [[Source routing]], [[HyFedRAG]], [[RAGRoute]].
