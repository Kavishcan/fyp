# Architecture

Three trust zones. The router sits in the middle with an adversary on each side.

## Zones

**Trusted zone (user side).** Query embedding and perturbation happen here.
Generation also happens here, on a local open-weight model with a fixed prompt.
Keeping generation inside this boundary is what removes prompt and output leakage
from scope.

**Router zone (honest but curious).** Holds the profile registry and makes the
selection. This is the adversary in A1 and A2. It never holds documents.

**Node zone (some malicious).** Each node holds its own documents and local
index. At least one forges its published profile — the A3 adversary.

## Online path

```
query
  -> embed (user side)
  -> perturb embedding (user side)
  -> ROUTER
       coarse filter    1000 -> 50 candidates
       trust rerank     50 -> k relevant
       anonymity set    k + decoys = m
  -> fan out to m nodes
  -> each node retrieves locally, returns top-n passages
  -> merge and rerank
  -> trust update (feeds back into rerank)
  -> local LLM, fixed prompt
  -> answer
```

The perturbed embedding travels the whole path. Nodes never see the clean query
either.

## Offline path (once per node)

```
document storage
  -> PII removal
  -> local embed and index      [never leaves the node]
  -> k-means, 16 to 64 centroids
  -> add Gaussian noise
  -> publish via MCP            [only this leaves]
```

PII removal runs **before** embedding. If it runs after, the embeddings encode
the PII and the published centroids inherit it.

## Attack surfaces

| ID | Attack | Adversary | Where |
|---|---|---|---|
| A1 | Query inversion | Honest-but-curious router | Router holds the perturbed embedding |
| A2 | Source inference | Observer of selection patterns | The fan-out, across many queries |
| A3 | Routing hijack | Malicious node | Profile publication, surfaces at rerank |

A2 is the core novel result. It makes "routing decisions as metadata" concrete
rather than rhetorical.

## MCP as node interface

Each node is an MCP server exposing a `retrieve` tool. The router is the client.
This gives real transport, real serialisation, and honest byte counts instead of
hand-waved communication costs.

**Split the scale claim.** Real MCP servers at 8 to 16 nodes prove the
architecture works over an actual protocol; measure real bytes and latency there.
In-process simulation with mocked transport covers 100, 300, and 1000 nodes for
scaling analysis. State this split explicitly in the thesis. Claiming 1000 live
MCP nodes when 16 are running is the kind of thing that unravels in a viva.

## Instrumentation

A logger taps every arrow: nodes contacted, bytes, per-stage latency, which
passages survived into the final answer, and the full routing decision.

Build this in month 2. Without it, month 6 means rerunning everything.
