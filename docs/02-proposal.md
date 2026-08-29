# Proposal

**Title:** A Smart, Privacy-Aware Source Router for Federated Retrieval-Augmented
Generation

## Statement

Federated RAG lets institutions contribute knowledge to a shared question-answering
system without surrendering their documents. But keeping documents local does not
make the system private. Before any retrieval happens, a router must decide which
of potentially thousands of nodes to contact, and that decision is itself an
exposed asset. The router observes the query, holds a map of which node knows
what, and its selection pattern is readable across repeated queries. Existing
protections do not reach it: confidential computing and encrypted vector search
protect documents, federated embedding learning protects retriever training, and
secure aggregation protects model updates. Two 2026 surveys name routing metadata
as an open leakage channel; the leading routing paper optimises purely for
efficiency and leaves privacy to future work.

This research builds a source router that is both smart and privacy-aware. Smart
means it selects a small set of relevant, trustworthy nodes from a large pool
without querying them all: a coarse filter over published node profiles narrows
the candidates, and a second stage reranks on relevance and accumulated trust.
Privacy-aware means it does this without learning what it should not — nodes
publish perturbed profiles rather than exact ones, queries are noised before the
router sees them, and selected nodes are padded with decoys so the true set is
hidden inside a larger anonymity set.

The central claim is that these two goals are in tension. Intelligent routing
wants rich signal. Privacy requires the opposite. And trust-based defence against
malicious nodes, which works by inspecting profiles and selection behaviour,
depends on exactly the signal that privacy removes. This tension has not been
examined: the one paper that defends routing integrity reports that encrypted
routing preserves the vulnerability it exploits, but treats routing privacy as
out of scope.

## Research questions

**RQ1.** How much does the routing stage leak, under an honest-but-curious router
attempting query inversion and an observer reconstructing node topics from
selection patterns?

**RQ2.** Can a privacy-aware router reduce that leakage at acceptable cost to
routing recall, answer quality, latency, and bandwidth?

**RQ3.** Does that protection weaken trust-based defence against malicious nodes,
and can the two be reconciled?

RQ1 is the safety net — publishable alone if the defence underperforms.
RQ3 is the headline.

## Contributions

1. A working two-stage privacy-aware source router, deployed over MCP.
2. The first measurement of routing-stage leakage in FedRAG.
3. A characterisation of where relevance, privacy, and trust hold together, and
   where they trade off.

## Scope boundaries

Deliberately **out of scope**, to keep the project inside nine months:

- Prompt and output leakage. Generation runs on a local open-weight model inside
  the trusted boundary, so these surfaces do not arise.
- Encrypted or TEE-based retrieval. Requires hardware or homomorphic ANN search;
  both are systems projects in their own right.
- Learned neural routing. The router uses clustering and a scoring function.
  "Smart" means the two-stage design plus trust weighting, not a trained model.
- Federated training of any component.

Stating these explicitly is a defence in the viva, not an admission.
