# Proposal

**Title:** A Smart, Privacy-Aware Source Router for Federated Retrieval-Augmented
Generation in Healthcare Networks

This document follows the structure of Chapter 1 of the dissertation, so sections
map directly onto the required subsections.

## 1.3 Problem definition

Federated RAG lets institutions contribute knowledge to a shared question-answering
system without surrendering their documents. Keeping documents local does not make
the system private. Before retrieval happens, a router decides which of potentially
thousands of nodes to contact. That decision is an exposed asset: the router
observes the query, holds a map of which node knows what, and its selection pattern
is readable across repeated queries.

In a hospital network this is concrete harm. A query routed to the paediatric
oncology silo reveals a patient's condition class without anyone reading the query.
Selection patterns over months expose one hospital's case mix to competitors.

## 1.6 Research gap

See `01-research-gap.md`. In brief: existing protections cover documents,
embeddings and model updates. The only mechanism operating at the routing stage is
ranking-preserving homomorphic encryption, which hides the query from the router
but leaves the selected node IDs unchanged.

## 1.7 Contribution to the body of knowledge

### 1.7.1 Problem domain contribution

A federated retrieval system for hospital consortia that protects the routing
decision as well as the documents. Nodes publish perturbed profiles rather than
exact ones, queries are perturbed before the router sees them, and selected nodes
are padded with decoys so the true set is hidden inside a larger anonymity set.

The system introduces an **audit-cost model** for decoy selection. In a regulated
network every node contact is a logged access under a data-sharing agreement, so
contacting seventeen irrelevant hospitals is a compliance cost and not merely
bandwidth. No existing federated RAG work prices decoys this way.

### 1.7.2 Research domain contribution

Three items, stated at the level of claim a reviewer can check.

1. **First measurement of routing-stage leakage in FedRAG.** Two 2026 surveys name
   routing decisions as a leakage channel; neither quantifies it. This work
   formulates and implements a source-inference attack (A2) that reconstructs a
   topic-to-node map from selection patterns alone, and reports the first numbers.

2. **A tunable privacy mechanism at the source-selection stage.** The primitives
   (distance-preserving perturbation, k-anonymity, decoy selection) are
   pre-existing and this is stated plainly. What is new is their composition into
   a selection mechanism and two design results that do not transfer trivially:
   max-over-centroid coarse scoring, which prevents recall loss across many
   centroids per node; and topic-stable decoy sampling, without which an observer
   intersects decoy sets across repeated queries and recovers the real nodes.

3. **The privacy-security interference result.** Trust-based defence against
   malicious nodes inspects returned evidence for query relevance. A decoy is a
   node returning evidence poorly matched to the query. The two are behaviourally
   identical, so anonymity-set privacy and evidence-feedback trust defence corrode
   each other. This interaction has not been posed, because the only existing
   routing privacy mechanism is ranking-preserving and therefore cannot produce it.

## 1.8 Research challenges

### 1.8.1 Research domain challenges

**RC1: Calibrating perturbation without destroying routing.** Distance-preserving
noise may degrade routing recall before it meaningfully reduces inversion success.
Coarse-stage recall is a hard ceiling: if the correct node is not in the candidate
set, no reranking recovers it. Establishing whether a usable operating region
exists is a precondition for the rest of the work, not an outcome of it.

**RC2: Constructing an adversary strong enough for a null result to mean
something.** If A2 is under-powered, a small measured leakage is uninformative. The
observer must be given many queries, a known topic taxonomy and the full selection
sequence, so that low leakage is evidence of safety rather than of a weak attack.

**RC3: Resolving the decoy-hijacker collision without leaking the resolution.**
Exempting decoy-selected nodes from trust updates fixes the interference, but the
exemption is itself observable and discloses which nodes were decoys, undoing the
privacy it was meant to protect. Whether a resolution exists that is both effective
and non-disclosing is an open design question.

### 1.8.2 Problem domain challenges

**RC4: Evaluating a privacy property rather than an output.** Answer quality is
measurable with established metrics. Leakage is not. The evaluation must
demonstrate that reduced leakage follows from the mechanism rather than from
degraded routing, which requires isolating each protection in an ablation.

**RC5: Simulated federation.** No public dataset contains real institutional silos.
Nodes are constructed by partitioning public corpora, which are more homogeneous
than real institutions. The construction must be stated plainly and its effect on
routing difficulty measured, not assumed away.

## 1.9 Research questions

**RQ01:** What information does the routing stage leak in current federated RAG
systems, to an honest-but-curious router and to an observer of selection patterns?

**RQ02:** How can a privacy-aware source router be designed to reduce that leakage
while selecting relevant nodes from a large pool?

**RQ03:** How does such a router affect routing quality, communication and audit
cost, and the effectiveness of existing trust-based defences against malicious
nodes?

RQ01 is the safety net: a measurement result publishable on its own. RQ03 carries
the interference finding.

## 1.10 Research aim

To design, implement and evaluate a privacy-aware source router for federated RAG
that selects a small set of relevant nodes from a large pool without disclosing
query intent or the topic-to-node map, and to determine the cost of that protection
in routing quality, communication, audit exposure and robustness to malicious
nodes.

## 1.11 Research objectives

| Phase | Objectives | RQ |
|---|---|---|
| Problem identification | RO1 Survey federated RAG routing and its threat models. RO2 Analyse which assets existing mechanisms protect and which they leave exposed. RO3 Formalise the routing-stage threat model. RO4 Produce project schedule and Gantt. | RQ01 |
| Literature review | RO5 Review RAG and federated RAG foundations. RO6 Review privacy mechanisms for retrieval and routing. RO7 Review attacks on selection mechanisms. RO8 Review evaluation methodology for routing, privacy and robustness. | RQ01 |
| Design | RO9 Design the two-stage router architecture. RO10 Design node-side profiling with perturbation and PII removal. RO11 Design anonymity-set selection with topic-stable decoys. RO12 Design the audit-cost model and the decoy-aware trust layer. | RQ02 |
| Implementation | RO13 Implement node containers exposing MCP retrieve. RO14 Implement the coordinator and two-stage router. RO15 Implement instrumentation for all cost and leakage measurements. RO16 Implement attacks A1, A2 and integrate A3. | RQ02 |
| Testing and evaluation | RO17 Establish baselines including plaintext, broadcast and HE routing. RO18 Measure leakage against the unprotected router. RO19 Sweep noise and anonymity set size, producing the privacy-utility-cost surface. RO20 Measure interference with the trust defence. RO21 Validate on a second dataset and at increasing node counts. | RQ03 |
| Evaluation and dissemination | RO22 Conduct expert evaluation. RO23 Submit a research paper. RO24 Release the reference implementation. | RQ03 |

Map RO numbers to the module learning outcomes before the PPRS submission; the
template requires an LO column alongside the RQ column.

## 1.12 Project scope

**In scope.** The routing stage: node profiling, query perturbation, candidate
selection, anonymity-set construction, trust-weighted reranking, and the
measurement of leakage and cost around all of it. Healthcare as the evaluated
deployment domain.

**Out of scope, by design.**

- Prompt and output leakage. Generation runs on a local open-weight model inside
  the trust boundary, so these surfaces do not arise.
- Encrypted or TEE-based retrieval. Requires hardware or homomorphic ANN search.
- Learned neural routing. The router uses clustering and a scoring function.
- Real patient data. Public benchmarks and synthetic data only.
- Clinical validation and regulatory approval.
- Authentication beyond mTLS, multi-tenancy, high availability.

These exclusions are carried into the requirements specification as Won't Have
items and excluded from testing by design.

## Cross-domain applicability

The architecture is domain-agnostic. The same problem exists in legal networks,
where privilege rules make the fact of consultation confidential independent of
content, and in financial consortia, where selection patterns reveal sectoral
exposure. Healthcare is the evaluated domain; generality is argued in the
conclusion and not claimed as an evaluated result.
