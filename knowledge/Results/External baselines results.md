---
tags: [type/result]
updated: 2026-10-05
---

# External baselines results

RAGRoute and Flower FedRAG reproduced from their public code on the PMC setup (593 test queries after RAGRoute's 30/10/60 router split), plus HyFedRAG-style and [[Blind unlock]]. Cost is per question.

| System | Hospitals reading the question | Topic inference (k-means, floor .226) | Hospital CPU total, 8 nodes | Traffic up+down | Modelled latency |
|---|---|---|---|---|---|
| Flower FedRAG (MiniLM) | all | .128 | 49 ms | 258 KB | 50 ms |
| HyFedRAG-style (bge) | all | .128 | 287 ms | 275 KB | 79 ms |
| RAGRoute | ~2 | **.562** | ~0.1 ms | 349 KB | 88 ms |
| Blind P=8 hybrid | **0** | .128 | 68 ms | **9 KB** | 123 ms |

**Scaling 8 / 16 / 32 hospitals (k-means):**
- bge broadcast hospital CPU: 287 / 542 / 1,112 ms per question.
- Blind P=8: 68 / 137 / 274 ms, and 9 / 18 / 37 KB per question.
- Blind P=8 hybrid MRR stays at 0.515 / 0.522 / 0.520.

**Quality, paired bootstrap:**
- Blind P=8 hybrid vs RAGRoute hybrid: +0.04 to +0.06 on k-means (p < .001); −0.05 on Dirichlet and −0.09 on random.
- On Dirichlet and random, RAGRoute's router learns little (validation AUC .852 / .583) and contacts 5.5 / 7.4 of 8 hospitals.
- Blind P=24 ties or beats RAGRoute on every split.

**Do not claim:** cheapest (RAGRoute hospitals only search; its coordinator sends text and embedding), or fastest (blind's device unlock adds latency). Defensible: "privacy at comparable cost". Also: blind releases more records (139) than broadcast (80); see [[Release results]].

See [[RAGRoute]], [[Flower FedRAG]], [[HyFedRAG comparison results]], [[Paired bootstrap]].

## Implementation / Experiment Sources

- [docs/53-external-baselines-cost.md](../../docs/53-external-baselines-cost.md)
- [backend/baselines/external_fedrag.py](../../backend/baselines/external_fedrag.py)
- [backend/eval/run_external_baselines.py](../../backend/eval/run_external_baselines.py)
- [docs/results/external_baselines_kmeans_c8_20261001-162602.csv](../../docs/results/external_baselines_kmeans_c8_20261001-162602.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
