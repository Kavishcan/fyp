---
tags: [type/literature]
updated: 2026-10-05
---

# RAGRoute

Primary source: [Efficient Federated Search for RAG](https://arxiv.org/abs/2502.19280).

RAGRoute uses learned source relevance selection to avoid querying every repository. Training a router and applying it at inference are different phases.

The current blind design instead contacts everyone while hiding useful cluster inputs. It sacrifices source-contact savings. Since docs/53 its router (CorpusRoutingNN and training loop, MIT) is reproduced from the public code and run on PMC; its 2 GB cross-encoder is replaced by our ranking. Its coordinator sends the question text **and** its embedding to selected sources. Results: [[External baselines results]] (cheapest in hospital CPU, topic leak .562 vs .226, near-broadcast on non-topical splits).

Worksheet P01; see [[Source routing]], [[Research gap analysis]].
