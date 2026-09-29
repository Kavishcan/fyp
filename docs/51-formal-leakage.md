# What each party learns: leakage definitions and proof sketches

Support material for the thesis's security section — definitions and
arguments to be restated in the student's own words, not submission prose.
It states exactly what blind unlock (docs/47) reveals, to whom, under which
assumptions, and contrasts it with the earlier dispatch policies whose
leakage was measured (docs/39–40, 50).

## Setting and notation

- G: the prime-order subgroup of edwards25519, order ℓ ≈ 2²⁵²; G a fixed
  generator. H₁: {0,1}* → G (libsodium `from_uniform` on SHA-512, cofactor
  cleared), modelled as a random oracle. H₂, H₃: keyed BLAKE2b, modelled as
  random oracles.
- Nodes N₁…N_n. Node i holds one OPRF key k_{i,c} ∈ ℤ_ℓ per collection c,
  and clusters with ids j. Envelope key and lookup tag:
  K_{ij} = H₂(i, c, j, k_{i,c}·H₁(j)),  t_{ij} = H₃(i, c, j, k_{i,c}·H₁(j))
  (the 2HashDH form of Jarecki–Kiayias–Krawczyk: the input j is bound into
  the outer hash — `privacy/psi.label_key`, `label_tag`).
- Public parameters Π: the node set, the probe count P, each node's
  published profile and cluster centroids, each role's permitted collections.
- A question q, held by the device D. The plan S(q): the P clusters with the
  highest centroid similarity across all nodes (`plan_probes`).

**Offline phase** (per key epoch, independent of any question): node i
publishes T_i = {(t_{ij}, AEAD(K_{ij}, pad(payload_{ij})))} for the
collections the caller's role may read; D caches it.

**Online phase** for q: for every node i, in sorted order, D sends
X_i = (x_{i,1}, …, x_{i,P}) where x = r·H₁(j) with fresh r ←$ ℤ_ℓ if slot
holds a real cluster j ∈ S(q) at node i, and x = r·G otherwise; slots are
shuffled. Node i returns k_{i,c}·x for each point and each permitted c.
D sends to every node before it unlocks anything (docs/51 fix, see below),
then unblinds real replies, looks up t, opens with K.

## Leakage functions

| Party | Leakage per question L(q) |
|---|---|
| Any node i (and any coalition of nodes) | (credential id, P, the role's permitted-collection count, arrival time) |
| Network observer | (every node in Π, P points each, message sizes, send times) |
| Device | everything (trusted — it is the user's) |

None of these is a function of q. Compare the measured policies:

| Policy | Observer leakage L(q) | Consequence (measured) |
|---|---|---|
| cosine router | top-k nodes of q | topic 0.318 per question, 0.543 over a 5-question session (docs/50) |
| topic-stable decoys | top-1 of q ∪ a set keyed by q's topic key | the cover set is a topic fingerprint: 0.469 → 0.570 (docs/39, 50) |
| random decoys | top-1 of q ∪ fresh random nodes | intersection over a session names the genuine node: 0.189 → 0.492 |
| fixed cells | the cell of top-1 of q | about log₂(#cells) bits per question; 0.256 → 0.283 over a session |
| **blind unlock** | **constant** | **floor at every session length** (0.238 topic, 0.125 source) |

## Claim 1 — the question is hidden from every node, even colluding and malicious ones

*For any two questions q₀, q₁ and any public parameters Π, the joint view
of all nodes during the online phase is distributed identically for q₀ and
q₁, up to statistical distance ≤ n·P·ε, with ε = Pr[r = 0] + Pr[H₁(j) = 0]
+ the scalar sampler's bias (all below 2⁻²⁵⁰).*

Sketch. G has prime order, so every non-identity element generates it. For
a real slot, H₁(j) ≠ 0 except with probability ≤ ε, and r uniform on ℤ_ℓ
makes r·H₁(j) uniform on G. For a dummy slot, r·G is uniform on G. Every
point uses a fresh independent r, so X₁,…,X_n are n·P independent uniform
elements whatever S(q) is — including how many real points each node
received (zero or all P). The credential MAC is a function of the points and
(node, day) only. The send order is fixed (sorted ids), and all points are
prepared before the first send, with the same total number of real points
(P) for every question. A node's reply cannot change what D sends it next
for this question: D sends nothing further, and a table re-download is
triggered by a changed epoch for that node, which does not depend on q.
Therefore a simulator given only L(q) (sample P uniform points per node)
produces the identical transcript.

This holds against **computationally unbounded** nodes, **any coalition**,
and nodes that **deviate arbitrarily** (malicious): hiding the question is
information-theoretic here, not an assumption. It does not cover: timing
inside the device beyond the send schedule; the link between a credential
and its questions over time (the node learns who asks and when — anonymous
tokens are the stated direction); a compromised device.

**Implementation fix found while writing this.** The first version of
`AppState._blind_retrieve` unlocked each node's reply before contacting the
next node, so the gap before request i+1 grew with the number of real
probes at node i — a timing channel outside the argument above. It now
contacts every node, then unlocks (`tests/test_blind_unlock.py::
test_every_node_is_contacted_before_anything_is_unlocked`).

## Claim 2 — an observer learns nothing about the question

The observer's view is the transcript of Claim 1 plus sizes and times. Sizes
are fixed by P and the role (the reply carries one point per permitted
collection). Times: fixed order, all points prepared up front, no
question-dependent processing between sends. So the observer's view is
simulatable from L(q), with the same statistical bound. Contrast cells,
whose observer leakage is the cell of the top-1 node — a function of q.

## Claim 3 — node data against a curious or malicious client

A client obtains OPRF outputs only through node evaluations, charged to its
persisted daily budget B (docs/43, docs/49). Under the one-more gap
Diffie–Hellman assumption in the random-oracle model — the standard
assumption for 2HashDH — a client making B evaluations can compute at most B
values k·H₁(j) it did not already have, hence open at most B envelopes; every
other envelope is an AEAD ciphertext under a key that is pseudorandom to it.
Separate keys per collection mean a role that is never evaluated under a
collection's key learns none of its envelopes, whatever ids it probes
(docs/45). The offline table reveals each permitted collection's cluster
count, and padding makes every envelope of a table the same length.

Deterministic sealing (nonce = H(key, plaintext)) is safe here because each
key seals one plaintext per epoch; rotating keys (`PSINode.rotate_keys`)
makes every cached envelope of the old epoch permanently unopenable.

What this does **not** give: a bound on what the B opened clusters reveal
(they are released, de-identified, by design — docs/44), or protection
against colluding clients pooling budgets.

## Claim 4 — what is not claimed

- **Integrity.** A malicious node can serve a false table or false replies.
  The device then opens nothing or opens planted content; the question stays
  hidden (Claim 1), but answers can be poisoned. Trust ranking and the
  cross-node rerank mitigate (docs/40, 42); a verifiable OPRF (a DLEQ proof
  that replies use the published key) is the standard fix for key
  substitution and is not built.
- **Differential privacy.** Nothing here is DP; the published centroids'
  minimum cluster size (docs/35) is a heuristic.
- **Side channels** at the device (CPU timing, cache) and traffic-analysis
  across questions (how often a credential asks) are outside the model.

## Assumptions, in one place

1. The device is trusted and has a good random number generator.
2. H₁, H₂, H₃ are random oracles; one-more gap DH holds in G (Claim 3 only).
3. XChaCha20-Poly1305 is IND-CPA and INT-CTXT (Claim 3 only).
4. Claims 1–2 need only uniform scalars; they hold against unbounded,
   colluding, malicious nodes and observers, for what is sent per question.
