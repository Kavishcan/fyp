# Experiments

## Baseline ladder

| # | System | Purpose |
|---|---|---|
| 0 | Oracle routing | Upper bound using dataset labels |
| 1 | Broadcast to all | Max coverage, max exposure, max cost |
| 2 | Plain relevance router | Efficiency-only baseline (RAGRoute-style) |
| **2.5** | **HE routing (CKKS)** | **Peer-reviewed privacy baseline. Reuse Mu and Li's HERouter.** |
| 3 | + query perturbation | Isolates the query-noise effect |
| 4 | + noisy profiles | Isolates the profile-noise effect |
| 5 | + anonymity sets | Full privacy router |
| 6 | + decoy-aware trust | Full system |

Rung 2.5 is essential and costs nothing to add. Showing that A2 succeeds against
encrypted routing exactly as well as against plaintext is the cleanest result in
the thesis, and their own Table 17 predicts it: encrypted and plaintext routing
produce identical rankings, so the observable selection set is unchanged.

## Attacks

| ID | Attack | Adversary | Measures |
|---|---|---|---|
| A1 | Query inversion | Honest-but-curious router | Term recovery from the perturbed embedding |
| A2 | Source inference | Observer of selection decisions | Accuracy of the reconstructed topic-to-node map |
| A3 | Routing hijack | Malicious node forging its profile | Attacker selection rate |

**A2 is the novel contribution.** Build it with a strong adversary: many observed
queries, a known topic taxonomy, the full selection sequence. An under-powered A2
makes a low leakage figure uninterpretable.

A3 replicates Mu and Li's setup from their public repository.

## Metrics

**Routing.** Coarse recall@K logged separately from final recall@K (coarse recall
is the ceiling and diagnoses which stage broke). MRR, nDCG, top-1 accuracy.

**Answer quality.** EM and F1 where labels allow; groundedness; citation accuracy.

**Privacy.** A1 inversion success; A2 map-reconstruction accuracy; irrelevant nodes
contacted.

**Robustness.** A3 hijack rate; malicious selection rate; honest-node false-positive
rate.

**Cost.** Nodes contacted; bytes transferred; per-stage and end-to-end latency;
**audit cost** measured as logged accesses to nodes with no relevant content.

## The sweep

Two knobs, swept jointly:

- `sigma` — perturbation magnitude on queries and profiles
- `m` — anonymity set size

Record every metric above at each setting.

## Headline figure

X-axis: privacy level. Two curves: A2 leakage falling, A3 hijack success rising.

If they cross, that is the thesis. If they do not, it is a useful null result and
RQ01 and RQ02 stand unaffected.

## Interference experiments (RQ03)

These are the specific tests of the decoy-hijacker collision. Both derive from
TASR's published update rule.

**E1 — Decoy trust decay.** Run a 500-query stream with anonymity sets active and
TASR unmodified. Track trust scores of honest nodes used as decoys. Prediction:
trust decays at gamma = 0.9 per selection, the router stops choosing them, and the
effective anonymity set shrinks over time even though `m` is held constant.
Measure: effective set size over the stream, and A2 accuracy at the start versus
the end.

**E2 — Median threshold shift.** TASR decays trust for nodes scoring below the
median among selected nodes. Vary `m` from 3 to 30 with a fixed hijacker and
measure A3 hijack success. Prediction: hijack success rises with `m` because the
median is drawn from decoy scores, lowering the bar the attacker must clear.

**E3 — Decoy-aware trust.** Exempt decoy-selected nodes from trust updates and
repeat E1 and E2. Measure recovery of both privacy and robustness.

**E4 — Exemption leakage.** E3's fix is observable: a node that is never penalised
was a decoy. Construct an observer that exploits the exemption pattern and measure
whether A2 accuracy recovers. This is the honest limitation and belongs in the
thesis whether or not it is solved.

## Scaling study

Node pools at 16, 100, 300, 1000. Report the funnel at each scale: coarse recall,
final recall, nodes contacted, latency, bytes, audit cost.

If recall collapses at 300, publish the ceiling. A measured limit is a finding.

Real MCP servers at 8 to 16 nodes; in-process simulation above that. State the
split explicitly.

## Known confound

FeB4RAG's 16 clients are cross-domain, which makes routing artificially easy. A
medical query routes to the medical client trivially. Address it with the
same-domain hard split from a single BEIR dataset and report both conditions.
