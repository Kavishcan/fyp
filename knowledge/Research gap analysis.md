---
tags: [hub, research-support]
updated: 2026-09-30
---

# Consolidated Research Gap Analysis

A gap is a bounded comparison with prior work, not a claim that nobody has built private search. Worksheet gap rows were proposals; this table reconciles them with current evidence.

| Gap | What Exists | Specific Missing / Unsettled Element | Evidence to Read | Current Project Response | Remaining Work |
|---|---|---|---|---|---|
| G1: Query content plus cross-owner contact-set protection | Selective FedRAG routing, PSI/PIR, private search and confidential RAG | Their joint utility/cost trade-off in this multi-owner RAG setting needs a controlled comparison | RAGRoute P01; C-FedRAG P11; FRAG P12; RemoteRAG P53; Private-RAG P54; SCOUT-RAG P55; PIR-RAG P59; Tiptoe P61; [[Pointing the Way]] | Standalone all-node blind unlock; three PMC splits and contact-set attacks | Direct primary-paper capability matrix; stronger timing and realistic-network tests |
| G2: Minimal authorised source-data disclosure | DP/HE, permissions, de-identification, private retrieval | Query hiding alone does not limit how much an authorised client obtains or what profiles reveal | FedE4RAG P03; Good and Bad RAG P04; cross-institution RAG P18; Private-RAG P54; [[Labeled PSI]] | Role keys, budgets, de-identification, cluster labels | Restricted-only profile fallback; clinical privacy tests; per-document disclosure; Sybil/collusion |
| G3: Malicious-source integrity under private routing | Profile signatures, poisoning/hijacking studies, trusted execution | Private dispatch does not prove source profiles or returned evidence truthful | Routing hijacking P21; blockchain reliability P22; PoisonedRAG P50; C-FedRAG P11 | Older trust/rerank experiments and audit fixes | Blind-specific hijack/poisoning benchmark; VOPRF/integrity design; no solved claim |
| G4: Joint reproducible evaluation | Ragas, ARES, RAGChecker, retrieval and budget benchmarks | One matched protocol for quality, contact leakage, disclosure, failure and system cost | P06, P13, P23, P37, P38, P62, P63 | Separate harnesses, per-query archives and bootstrap comparisons | One current scorecard; total wire cost, cache cost and noninferiority protocol |
| G5: External validity in realistic federations | Public medical and heterogeneous benchmarks | Public simulated clients do not establish clinical deployment, workload stability or broad scale | HyFedRAG P08; medical FL/RAG P20; MIRAGE P39; FeB4RAG P13 | PMC three-way partition; BEIR/MIRAGE; fictional canaries | Domain expert review, additional models/seeds, authorised clinical data if feasible; remote scale tests |

G1 merges the old overlapping routing and end-to-end privacy rows. G2 is a distinct data-owner disclosure axis, not the same query-leakage problem.

**Working main gap:** a well-scoped, reproducible evaluation of training-free multi-owner RAG that hides query-dependent source contacts and node query inputs together, while measuring the retrieval and authorised-disclosure costs.

**Novelty caution:** first-in-world status is not established by these 63 worksheet summaries. See [[Novelty and contribution]], [[Literature themes]] and [[Source reconciliation]].
