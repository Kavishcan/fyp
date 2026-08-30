# Research gap

> **Revision note.** An earlier version of this document claimed no privacy
> mechanism operates at the routing stage. That was wrong. Mu and Li ship a
> working CKKS homomorphic-encryption router. The corrected claim is narrower and
> stronger: the one mechanism that exists is ranking-preserving, so it protects
> query content while leaving the selection pattern fully exposed.

## Statement

Federated RAG protects documents and, in one case, query confidentiality at the
router. It does not protect the routing decision itself. Nobody has measured what
that decision leaks, and nobody has tested whether protecting it breaks the
defences that already exist.

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

## The decisive evidence

Mu and Li's Table 17 reports hijack rate under plaintext and encrypted routing:

| Setting | HR@1 | HR@2 | HR@3 |
|---|---|---|---|
| Plaintext | 33.2 | 81.7 | 93.7 |
| Encrypted | 33.2 | 81.7 | 93.7 |

Identical at every cutoff. CKKS encrypts the computation and returns exactly the
same ranking. The router cannot read the query, but the selected node IDs are
unchanged, so anyone observing which nodes are contacted learns exactly what they
would have learned without encryption.

This single table is the strongest motivation available for this project. Cite it
in the introduction and in the gap statement.

## Who has named the channel

- A FedRAG scoping review (2026) states that routing introduces a new trust point
  and a new leakage channel in the form of routing decisions as metadata. Listed
  as an open problem, not solved.
- A security and privacy survey for RAG (2026) lists routing metadata among the
  assets crossing edge-to-cloud trust boundaries.
- RAGRoute optimises routing purely for efficiency and notes only that privacy
  schemes "can benefit from" it, with no mechanism, threat model or experiment.
- Mu and Li (EMNLP 2026 Main) attack routing **integrity** and defend it with
  TASR. Routing **privacy** is explicitly out of their scope. A keyword search of
  their released codebase for leak, privacy, inversion, anonymity, decoy,
  differential and epsilon returns zero matches.

## The three unanswered questions

| | Question | Status |
|---|---|---|
| 1 | How much does routing leak? | Named as a risk, never measured |
| 2 | Can it be reduced at acceptable cost? | Only a ranking-preserving mechanism exists, which offers no trade-off to characterise |
| 3 | Does protecting it weaken trust-based defence? | Not asked by anyone |

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

**Validated** — two independent surveys call it open, so it was not invented here.
**Unoccupied** — the closest paper explicitly scopes privacy out and ships no
privacy metric.
**Narrow** — one stage, not five.
**Falsifiable** — the decoy-hijacker collision is a specific prediction, and a
null result is still useful to deployers.

## Standing caution

The papers defining this gap are months old and the reference implementation is
public at a top venue. "Add noise to this and measure leakage" is a reasonable
next step for anyone already holding that repository. Re-verify before the
proposal deadline and again before paper submission, and set an arXiv alert for
federated RAG routing.
