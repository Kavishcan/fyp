# Experiments

## Baseline ladder

Run in this order. The ablation table writes itself.

| # | System | Purpose |
|---|---|---|
| 0 | Oracle routing | Upper bound using dataset labels |
| 1 | Broadcast to all | Max coverage, max exposure, max cost |
| 2 | Plain relevance router | Efficiency-only baseline (RAGRoute-style) |
| 3 | + query perturbation | Isolates the query-noise effect |
| 4 | + noisy profiles | Isolates the profile-noise effect |
| 5 | + anonymity sets | Full privacy router |
| 6 | + trust reranking | Full system |

## Attacks

| ID | Attack | Adversary | Measures |
|---|---|---|---|
| A1 | Query inversion | Honest-but-curious router | Term recovery rate from the perturbed embedding |
| A2 | Source inference | Observer of routing decisions | Accuracy of reconstructed topic -> node map |
| A3 | Routing hijack | Malicious node forging its profile | Attacker selection rate |

**Design A2 with a strong adversary.** Many observed queries, known topic
taxonomy, full access to the selection sequence. If leakage turns out to be
small, a strong adversary makes that an informative null result rather than an
under-powered one.

A3 replicates Mu and Li's setup. Use their public repository.

## Metrics

**Routing**
- Coarse recall@K (stage 1 only) — log separately, this is the ceiling
- Final recall@K, MRR, nDCG, top-1 accuracy

**Answer quality**
- EM / F1 where labels allow
- Groundedness, citation accuracy

**Privacy**
- A1 inversion success
- A2 source-inference accuracy
- Nodes contacted that were not relevant

**Robustness**
- A3 attack success rate
- Malicious-node selection rate
- Honest-node false-positive rate (down-ranked when they should not be)

**Cost**
- Nodes contacted
- Bytes transferred
- Per-stage and end-to-end latency

## The sweep

Vary the two privacy knobs and record everything above at each setting:

- `sigma` — noise magnitude on queries and profiles
- `m` — anonymity set size

## Headline figure

X-axis: privacy level. Two y-curves: leakage falling, hijack success rising.

If they cross, that is the thesis. If they do not, that is a useful null result
for deployers and RQ1 and RQ2 still stand.

## Scaling study

Node pools at 16, 100, 300, 1000. Report the funnel honestly at each scale:
coarse recall, final recall, nodes contacted, latency, bytes.

If recall collapses at 300, publish the ceiling. A measured limit is a finding.

## Known confound

FeB4RAG's 16 clients are cross-domain, which makes routing artificially easy — a
medical query obviously goes to the medical client. Address it directly by adding
a hard split: partition a single BEIR dataset into several same-domain nodes so
routing must discriminate between similar sources. Report both.
