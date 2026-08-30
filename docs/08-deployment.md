# Deployment

The target deployment for this system is a regional hospital network sharing
clinical reference material without pooling it.

## Scenario

Six to twelve hospitals in a region. Each holds local clinical guidance: treatment
protocols, formulary decisions, care pathways, departmental guidelines, anonymised
case summaries. This material is institutionally owned and cannot be centralised,
for reasons that are legal, contractual and political rather than technical.

A clinician at hospital A asks a question. The answer may exist in hospital D's
protocols. Today that knowledge is unreachable. This system makes it reachable
without moving the documents.

## Why routing privacy matters here specifically

In a generic federated setting, "an observer learns which node holds which topic"
sounds mild. In healthcare it is concrete harm:

- A query routed to the paediatric oncology silo reveals a patient's condition
  class even if nobody reads the query text.
- Selection patterns reveal which hospital treats rare condition X. In a small
  population that is potentially re-identifying, and it is commercially useful to
  competitors regardless.
- Over months, routing logs expose one institution's case mix to anyone watching.

None of this requires reading a single query. Protecting document content is not
sufficient.

## The audit-cost constraint

This is the constraint that distinguishes healthcare from a generic deployment,
and it feeds directly into the research.

In a hospital network, **every node contact is an audit event**. Access is logged
under data-sharing agreements. Contacting twenty hospitals when three hold
relevant material is not merely bandwidth. It is seventeen logged accesses to
institutions with no legitimate interest in that query, and under some agreements
that is itself a violation.

The decoy cost function therefore has three terms, not two:

```
cost(m) = latency(m) + bandwidth(m) + audit_cost(m)
```

Two design questions follow, both measurable:

1. Should decoys be drawn only from nodes already inside the same data-sharing
   agreement? This constrains the anonymity set and probably weakens it.
2. Does a smaller, agreement-bounded anonymity set still defeat A2, or does the
   constraint make the defence useless?

No existing FedRAG work costs decoys this way.

## What a node is

One hospital runs one node. Concretely:

- A container with a local document folder mounted read-only
- A PII removal pass over documents before embedding
- A local embedding index that never leaves the container
- A k-means profile, noised, published to the coordinator
- An MCP server exposing a single `retrieve` tool

Onboarding is: run the container, point it at a folder, register with the
coordinator. No model training, no data upload, no schema migration.

## What the coordinator is

One container running the router plus a local open-weight LLM. It holds:

- The profile registry (noised centroids only, never documents)
- The two-stage router
- Trust state per node
- The generation step, inside the trust boundary

The coordinator never receives raw documents and never sees an unperturbed query.

## API surface

```
POST /query          { question, max_nodes? }  -> { answer, citations, nodes_contacted }
POST /nodes/register { node_id, profile, mcp_endpoint }
GET  /nodes          -> registry status and trust scores
GET  /audit/:query_id -> which nodes were contacted and why
```

The audit endpoint is not optional in this domain. An institution must be able to
ask why it received a query, and the honest answer is sometimes "you were a
decoy". Whether that answer can be given without undoing the privacy is an open
design question and is discussed in the thesis.

## Latency budget

Clinical reference lookup is not real-time, but it competes with a web search.
Target end to end under 5 seconds:

| Stage | Budget |
|---|---|
| Embed and perturb | 50 ms |
| Coarse filter | 20 ms |
| Rerank and decoy selection | 30 ms |
| Node fan-out, slowest node | 1500 ms |
| Merge and rerank | 200 ms |
| Generation | 3000 ms |

Fan-out dominates and scales with the slowest contacted node, not the average.
This is another reason anonymity set size is a real cost and not a free parameter.

## Out of scope for v1

Stated explicitly so the boundary is defensible:

- Real patient records. The system is evaluated on public benchmarks and
  synthetic data only.
- Authentication beyond mTLS between coordinator and nodes.
- Multi-tenancy, high availability, failover.
- Clinical validation of answer quality.
- Regulatory approval.

## Regulatory position

Clinical decision support that influences patient care is a regulated medical
device under EU MDR, UK MHRA and US FDA regimes. This system is **research
infrastructure demonstrating a routing architecture**, not a clinical tool. It is
evaluated on public exam benchmarks and synthetic data, never on patient records,
and would require regulatory review before any clinical deployment.

If real hospital data were ever involved, GDPR Article 9 applies (special
category data), which is a substantially heavier regime than anything in scope
here.

State this position in the thesis rather than waiting to be asked.

## Engineering standards from day one

These cost almost nothing during research and prevent a rewrite in month 8:

- Configuration in files, not constants
- Structured logging, not print statements
- Type hints throughout
- Unit tests on the router, integration test on a two-node setup
- `docker compose up` working by month 2
- Pinned dependencies

## Applicability to other domains

Healthcare is the evaluated domain. The architecture is not medical.

Nothing in the router, the node interface, or the privacy mechanism assumes
clinical content. A node is any institution holding documents it cannot pool. The
routing-leak argument transfers wherever the *identity* of the consulted source
carries information independent of what was asked.

| Domain | What the selection pattern reveals | Regime |
|---|---|---|
| Healthcare (evaluated) | A hospital's case mix; a patient's condition class | GDPR Art. 9, MDR/MHRA/FDA |
| Legal | Which firm handles which client matter | Privilege, conflict-of-interest rules |
| Financial services | Which institution is exposed to which sector or counterparty | Market-sensitive information, competition law |
| Government | Which department holds which case or investigation | Freedom of information, national security exemptions |

**Legal is arguably the sharpest case.** Under privilege and conflict rules, the
fact that a firm was consulted on a matter is itself confidential, independent of
the content of the consultation. That is the thesis argument restated in a
profession's own vocabulary: protecting the documents is not sufficient when the
routing decision is the disclosure.

The audit-cost constraint transfers too, in altered form. In healthcare a decoy
contact is a logged access under a data-sharing agreement. In law it is a
potential conflict-check trigger. In finance it is an information barrier
crossing. In each case decoys cost something beyond bandwidth, and the specific
cost model would need re-deriving per domain.

**This section is an argument, not a result.** No cross-domain evaluation is
performed. Extending the audit-cost model and the anonymity-set design to legal
and financial consortia is identified as future work, not claimed as demonstrated.
Stating that boundary explicitly is the point: the architecture generalises, the
evidence does not.

## Two operating modes, one codebase

**Research mode** sweeps noise sigma and anonymity set size m across the full
grid and writes results for analysis.

**Deployment mode** ships a single validated operating point, chosen from the
research curve.

This is the connection between the two halves of the project: the research is
what justifies the default. Without the sweep, the deployed configuration would
be an arbitrary guess.

## Cross-domain applicability

The architecture is domain-agnostic. The routing-leak argument transfers directly:

| Domain | What the selection pattern reveals |
|---|---|
| Healthcare | A hospital's case mix; a patient's condition class |
| Law | Which firm handles which client's matter, which under privilege and conflict rules is confidential independent of content |
| Finance | Which institution is exposed to which sector or counterparty |

Legal networks are arguably the sharpest case, because the fact of consultation is
itself protected.

Healthcare remains the evaluated domain. Generality is argued in the conclusion in
roughly one page and is not claimed as an evaluated result. A thesis asserting
three domains it cannot evaluate reads as unfocused; a thesis evaluating one and
reasoning carefully about the others does not.
