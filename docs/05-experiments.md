# Experiments

## Baseline ladder

| # | System | Purpose |
|---|---|---|
| 0 | Oracle routing | Upper bound using dataset labels |
| 1 | Broadcast to all | Max coverage, max exposure, max cost |
| 2 | Official RAGRoute | Primary peer-reviewed source-routing baseline |
| **2.5** | **HE routing (CKKS)** | **Peer-reviewed privacy baseline. Reuse Mu and Li's HERouter.** |
| 3 | + query perturbation | Isolates the query-noise effect |
| 4 | + noisy profiles | Isolates the profile-noise effect |
| 5 | + anonymity sets | Full privacy router |
| 6 | + decoy-aware trust | Full system |

Rung 2 uses the official RAGRoute implementation through the common source-router
adapter where practical. The local cosine router remains a transparent additional
control rather than being presented as RAGRoute. RAGRouter is not a direct
federated-source baseline because it selects among RAG-enabled language models.

## Baseline comparability rule

A router can be benchmarked without open source code if an executable, package,
checkpoint or API lets the project register the same sources, run the same queries
and obtain ranked source IDs. If only published aggregate numbers are available,
cite them as literature comparison and do not place them in the direct experimental
table.

Rung 2.5 is essential because it is the closest published privacy baseline.
Mu and Li's Table 17 predicts that A2 receives the same observable selection set
under plaintext and ranking-preserving encrypted routing. The project must
reproduce that condition; it must not report the predicted equality as its own
result before running the experiment.

## Attacks

| ID | Attack | Adversary | Measures |
|---|---|---|---|
| A1 | Query inversion | Honest-but-curious router | Term recovery from the perturbed embedding |
| A2 | Source inference | Observer of selection decisions | Accuracy of the reconstructed topic-to-node map |
| A3 | Routing hijack | Malicious node forging its profile | Attacker selection rate |

**A2 is the primary new measurement in this project.** Build it with a strong adversary: many observed
queries, a known topic taxonomy, the full selection sequence. An under-powered A2
makes a low leakage figure uninterpretable.

A3 replicates Mu and Li's setup from their public repository.

## Metrics

**Routing.** Coarse recall@K logged separately from final recall@K (coarse recall
is the ceiling and diagnoses which stage broke). MRR, nDCG, top-1 accuracy.

**Answer quality.** EM and F1 where labels allow; groundedness; citation accuracy.

**Privacy.** A1 inversion success; A2 map-reconstruction accuracy; irrelevant nodes
contacted; sensitive-token fraction sent; repeated-route linkability. Report route
privacy separately from the additional query exposure caused by decoys.

**Robustness.** A3 hijack rate; malicious selection rate; honest-node false-positive
rate.

**Cost.** Nodes contacted; bytes transferred; per-stage and end-to-end latency;
**audit cost** measured as logged accesses to nodes with no relevant content.

## The sweep

Two knobs, swept jointly:

- `sigma` — perturbation magnitude on queries and profiles
- `m` — anonymity set size

The sweep is subject to a maximum fan-out and audit/exposure budget. A larger
anonymity set is not automatically more private because it discloses a
query-derived representation to more sources.

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

Real MCP servers at 8 to 16 nodes; logical or in-process clients above that. State
the split explicitly.

## Reproduction records

For every external baseline record repository commit, environment, dataset version,
source-profile construction, query split, embedding model, top-k, seed, hardware,
commands and any adapter changes. Save raw routing outputs before computing metrics.

## Known confound

FeB4RAG's 16 clients are cross-domain, which makes routing artificially easy. A
medical query routes to the medical client trivially. Address it with the
same-domain hard split from a single BEIR dataset and report both conditions.
