# Research gap

> **Revision note.** An earlier version of this document claimed no privacy
> mechanism operates at the routing stage. That was wrong. Mu and Li ship a
> working CKKS homomorphic-encryption router. The corrected claim is narrower and
> stronger: the one mechanism that exists is ranking-preserving, so it protects
> query content while leaving the selection pattern fully exposed.

## Statement

Federated RAG can protect documents and query content while still exposing the
identity and sequence of contacted sources. In the literature reviewed for this
project, no study was found that jointly measures this selection-pattern leakage,
reduces it under an explicit exposure/cost constraint, and evaluates the effect on
trust-based routing-hijack defence. This claim must be rechecked before proposal
submission and paper submission; it is not a universal claim that no work exists.

## What each existing mechanism protects

| Work | Protects | Leaves exposed |
|---|---|---|
| C-FedRAG | Documents, via trusted execution | Routing |
| FRAG | Query and data vectors, via homomorphic encryption | Routing |
| FedE4RAG | Retriever training | Inference-time routing |
| pFedRAG | Personalised retrieval, model updates | Routing |
| Secure Aggregation | Model updates | Everything at inference |
| DP-SGD | Training-data memorisation | Live queries |
| RemoteRAG | Query to a single cloud service | Selection among many sources |
| **HERouter (Mu and Li)** | **Query content at the router** | **The selection pattern** |

## Closest technical evidence

Mu and Li's Table 17 reports hijack rate under plaintext and encrypted routing:

| Setting | HR@1 | HR@2 | HR@3 |
|---|---|---|---|
| Plaintext | 33.2 | 81.7 | 93.7 |
| Encrypted | 33.2 | 81.7 | 93.7 |

Identical at every cutoff. CKKS encrypts the computation and returns exactly the
same ranking. The router cannot read the query, but the selected node IDs are
unchanged, so anyone observing which nodes are contacted learns exactly what they
would have learned without encryption.

The result motivates an empirical reproduction: if encryption returns the same
ranking, an observer of contacted IDs receives the same routing trace. The thesis
must reproduce this behaviour under the selected benchmark instead of relying on
the published table alone.

## Who has named the channel

- A FedRAG scoping review (2026) states that routing introduces a new trust point
  and a new leakage channel in the form of routing decisions as metadata. Listed
  as an open problem, not solved.
- A security and privacy survey for RAG (2026) lists routing metadata among the
  assets crossing edge-to-cloud trust boundaries.
- RAGRoute optimises routing purely for efficiency and notes only that privacy
  schemes "can benefit from" it, with no mechanism, threat model or experiment.
- Mu and Li's 2026 routing-hijacking preprint attacks routing **integrity** and
  defends it with TASR. It is exceptionally relevant and has runnable code, but it
  is treated as emerging preprint evidence unless peer-reviewed status is
  independently verified. Routing privacy is not its main contribution.

## Evidence weighting

| Work | Status in this project | Evidence weight |
|---|---|---|
| RAGRoute | Closest peer-reviewed source-routing method and primary runnable baseline | Core / strong |
| RAGRouter | Peer-reviewed routing methodology, but routes among RAG-enabled LLMs rather than knowledge sources | Adjacent / strong |
| Routing Hijacking + TASR | Closest security attack and defence with public implementation | Core security / emerging |
| Security and privacy surveys | Motivate metadata, coupled threats and multi-objective evaluation | Supporting |

## The three unanswered questions

| | Question | Status |
|---|---|---|
| 1 | How much does routing leak? | Not quantified in the reviewed source-routing studies |
| 2 | Can it be reduced at acceptable cost? | No directly comparable exposure-constrained mechanism was found |
| 3 | Does protecting it weaken trust-based defence? | No joint privacy/TASR evaluation was found |

## The sharpened form of question 3

Reading TASR's signal definitions turns this from a hunch into a falsifiable
prediction.

TASR's dominant signal is retrieval relevance: the mean cosine similarity between
the query embedding and each returned document. Their own ablation shows this
signal alone matches full TASR on HR@1 in every scenario.

A decoy is, by definition, a node routed for a query it cannot serve, returning
evidence poorly matched to that query.

**Decoys and hijackers are behaviourally identical under this signal.**

Two consequences follow from their published update rule, both testable:

| Direction | Mechanism |
|---|---|
| Defence corrupts privacy | Decoy trust decays at gamma = 0.9 per selection. The router stops choosing them. The anonymity set collapses over a query stream, so privacy degrades silently rather than failing visibly. |
| Privacy corrupts defence | TASR decays trust below the **median** score among selected nodes. With 15 decoys in a set of 20, the median is a decoy score. A real hijacker returning marginally relevant evidence now clears a bar it would have failed at K = 3. |

Neither is speculation. Both fall out of Appendix G and Section 3.3 of their
paper.

## Why the gap holds

**Supported** — surveys identify metadata, partial observability, trust and
privacy-utility evaluation as open concerns.
**Unoccupied in the reviewed set** — the closest source-routing and routing-
security studies do not jointly evaluate selection-pattern privacy and TASR.
**Narrow** — one stage, not five.
**Falsifiable** — the decoy-hijacker collision is a specific prediction, and a
null result is still useful to deployers.

## Standing caution

The papers defining this gap are recent and the reference implementations are
public. "Add noise and measure leakage" is not enough by itself. The contribution
must include a strong attacker, a measurable exposure model, a reproducible
baseline, a constrained privacy mechanism, and the privacy-trust interference
experiments. Re-verify the literature before the proposal and paper deadlines.
