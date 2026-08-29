# Research gap

## Statement

Federated RAG protects documents but not the routing decision. Nobody has
measured what that decision leaks, and nobody has tested whether protecting it
breaks the defences that already exist.

## Why the gap is real

Existing FedRAG work protects one asset at a time.

| Work | Protects | Does not touch |
|---|---|---|
| C-FedRAG | Document confidentiality via trusted execution | Routing |
| FRAG | Query and data vectors via homomorphic encryption | Routing |
| FedE4RAG | Retriever training via federated embedding learning | Inference-time routing |
| pFedRAG | Personalised retrieval, model updates | Routing |
| Secure Aggregation | Individual model updates | Everything at inference |
| DP-SGD | Training data memorisation | Live queries |
| RemoteRAG | Query to a single cloud service | Selection among many sources |

The routing stage sits outside all of it. The router observes the query, holds a
map of which node knows what, and its selection pattern is observable across
repeated queries.

## Who has noticed

- A FedRAG scoping review (2026) states that routing introduces a new trust point
  and a new leakage channel in the form of routing decisions as metadata. Listed
  as an open problem, not solved.
- A security and privacy survey for RAG (2026) lists routing metadata among the
  things that cross trust boundaries in hybrid deployments. Again a listed risk.
- RAGRoute optimises routing purely for efficiency and notes only that privacy
  schemes "can benefit from" it — no mechanism, no threat model, no experiment.
- Mu and Li attack routing **integrity** and defend it with trust signals, but
  scope routing **privacy** out. They report that encrypted routing preserves the
  ranking their attack exploits.

That last finding is the pointer. Encryption does not fix routing, which is the
argument for treating routing as needing its own protection.

## The three unanswered questions

| | Question | Status |
|---|---|---|
| 1 | How much does routing leak? | Named as a risk, never measured |
| 2 | Can it be reduced at acceptable cost? | No mechanism proposed |
| 3 | Does protecting it weaken trust-based defence? | Not asked by anyone |

Question 3 is the one nobody has framed. Questions 1 and 2 make it answerable.

## The central tension

Intelligent routing wants rich signal: accurate profiles, clean queries, tight
selection. Privacy requires the opposite. Trust-based defence against malicious
nodes works by inspecting profiles and selection behaviour, which is exactly the
signal privacy removes.

A null result here is still useful. If privacy does not degrade the trust
defence, that is a reassurance deployers need.

## Caution

Two of the papers that define this gap appeared within six months of writing.
Re-verify before submitting the proposal and before submitting the paper.
