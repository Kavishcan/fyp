# Blind unlock: download once, unlock blindly

## Verdict

**Blind unlock hides both leaks completely and recovers most of the
retrieval quality the privacy configuration used to cost.** Every hospital
receives the same number of blinded points on every question — real or
dummy, indistinguishable — so no hospital learns the question or whether it
was relevant, and the contact pattern carries nothing. Encrypted tables are
downloaded once, so per-question traffic falls from ~100 MB to a few KB.

PMC-Patients, 986 queries, 5,000 patients in 8 k-means hospitals, bge-base
(same data, partition and seed as docs/46):

| Configuration | MRR | P@10 | nDCG@10 | Question to hospitals | Topic inference (floor 0.239) | Records disclosed / q | Device ms / q | Slowest hospital ms / q | Received / q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HyFedRAG-style (docs/46) | 0.444 | 0.109 | 0.409 | **all 8** | 0.239 | 80 | 1.6 (total) | — | 0.24 MB |
| ours: PSI + cells (docs/46) | 0.350 | 0.083 | 0.305 | 0 | 0.254 | 143 | 268 (total) | — | 103 MB |
| ours: PSI to all 8, nprobe 3 (docs/46) | 0.409 | 0.099 | 0.373 | 0 | 0.239 | 426 | 789 (total) | — | 198 MB |
| **blind unlock, P = 4** | 0.399 | 0.094 | 0.354 | **0** | **0.239** | **74** | **22** | 5 | **2.6 KB** |
| **blind unlock, P = 8** | **0.421** | 0.101 | 0.379 | **0** | **0.239** | 140 | 44 | 9 | 4.6 KB |
| **blind unlock, P = 16** | **0.431** | 0.105 | 0.392 | **0** | **0.239** | 269 | 88 | 18 | 8.7 KB |
| **blind unlock, P = 24** | **0.437** | 0.107 | 0.401 | **0** | **0.239** | 393 | 132 | 29 | 12.8 KB |

One-time download (offline, per key epoch): **83 MB for all 8 hospitals**
(largest 14.5 MB), padded envelopes, base64 on the wire; built in 1.4 s.

Reading:

- **Both leaks at zero at once**, which no earlier configuration reached
  without contacting every hospital with a full table per question.
- **Quality:** P = 8 keeps 95% of HyFedRAG's MRR (0.421 vs 0.444), P = 24
  98% (0.437). It beats PSI-to-all-8 (0.409) because the device picks the
  best clusters *across* hospitals instead of a fixed nprobe at each.
- **Disclosure:** P = 4 releases fewer records than HyFedRAG's top-10 from
  each of 8 hospitals (74 vs 80) at MRR 0.399; P = 8 is a third of
  PSI-to-all-8's disclosure (140 vs 426) at higher MRR.
- **Cost:** device 22–132 ms and hospital 5–29 ms per question (in-process,
  single core; hospitals run in parallel in deployment), a few KB per
  question, against 83 MB once per epoch.
- P = 8 is the recommended default (studio default); the P sweep is the
  privacy-free quality/disclosure trade-off, since leakage is flat in P.

## Why a new dispatch stage

docs/46 left two costs on the table, both caused by doing the download and
the unlock in the same step, per question:

- **Bandwidth and time.** Per-query labeled PSI ships every envelope a
  contacted node holds (docs/36). At PMC scale that is ~100 MB and ~270 ms
  per question at four contacts, ~200 MB and ~790 ms when every hospital is
  contacted.
- **The pattern leak is only reduced.** Cells hide the topic partially
  (0.254 vs a 0.239 floor) and cost retrieval (−0.032 MRR); contacting every
  hospital hides it fully but multiplies the first cost by the federation
  size.

## The protocol

```text
Offline, once per key epoch (same bytes for every client of a role)
  node:   for each cluster c, out_c = k_coll · H(c)
          tag_c = BLAKE2b(out_c, "lookup-tag")      key_c = BLAKE2b(out_c, "label-key")
          envelope_c = XChaCha20-Poly1305(key_c, padded compact payload)
          publish {tag_c: envelope_c}   (public collection to anyone,
                                         restricted ones only to permitted roles)
  device: download and cache every node's table

Online, per question
  device: score every published cluster of every node locally; take the best P
          for EVERY node: P points = r·H(c) for its chosen clusters, r'·G dummies for the rest, shuffled
          send to every node in a fixed (sorted) order, with the credential
  node:   return k_coll · point for each point and each permitted collection;
          charge P evaluations to the credential's budget
  device: for real points only: out = r⁻¹ · reply → tag → cache lookup → open with key
          rerank the unlocked passages → top-n → local / trusted LLM
```

**Why a node cannot tell a dummy from a real probe.** A real point is
r·H(c) with r uniform modulo the group order ℓ; H(c) generates the
prime-order group, so r·H(c) is uniform on it. A dummy is r'·G with r'
uniform — the same distribution. The node's view of a question is P uniform
group elements, whatever the question and whichever clusters (if any) were
real. This is the argument that already hides the cluster ids in docs/36,
applied to whether a point exists at all.

**Leakage.** Per question, a node learns (credential id, P, time of
arrival); an observer learns (every registered node, P points each, time).
Both are independent of the question. P and the node set are public
parameters. The device alone knows which clusters were real.

**Implementation.** `privacy/psi.py`: `label_tag`, `dummy_point`, compact
float16 payloads padded to one length (`encode_passages`), deterministic
sealing so every process of a node serves a byte-identical table,
`PSINode.blind_table`, `epoch`, `rotate_keys`. `privacy/blind_unlock.py`:
`plan_probes` (global top-P, per-node padding), `TableCache`, `unlock` (tag
lookup, no trial decryption). Node tool `psi_table`; `psi_evaluate` now
reports the key epoch so the device refreshes a table only when a node
rotated its keys — for that node, whatever the question. API:
`routing_mode="blind"`, `blind_probes` (default 4, studio 8).

## Relation to prior work

Every ingredient is known; the combination and the setting are not, as far
as a web search in September 2026 found:

- Labeled PSI over an OPRF — Chen, Laine, Rindal.
- Offline download, online query — standard in PIR with hints (SimplePIR,
  online–offline PIR, Tiptoe).
- Fake queries made indistinguishable by encryption — Wally (Apple, 2024),
  which needs a crowd of clients and an anonymity network and gives a DP
  guarantee against one server. Here a single device pads every node itself,
  and the property is exact indistinguishability of each node's view.
- Private dense retrieval against one provider — "Pointing the Way, Hiding
  the Destination" (arXiv 2608.25735), which bounds disclosure with k-out-of-K
  OT; its multi-owner, source-routing analogue is what this doc adds.

## What this does not establish

- **Records still reach the device**: the P unlocked clusters, de-identified
  (docs/44). Envelopes of other clusters sit on the device encrypted under
  keys the node never releases; rotating keys makes every old copy
  permanently unopenable.
- **Device storage scales with the federation.** Suitable for tens to
  hundreds of institutional nodes; a node too large to cache needs per-query
  PSI with cells (docs/40) or PIR.
- **Budgets are charged for dummies.** A credential spends P evaluations at
  every node per question; the enumeration bound per node (docs/43) is
  unchanged per point, and daily budgets must be sized in points × questions.
  The docs/43 budget is still held in memory by the node process — the audit
  finding that a spawn-per-call MCP node resets it stands until fixed.
- Semi-honest nodes. A malicious node can serve a client a different table,
  but receives no reply channel from which to learn what opened; argued, not
  proven. Timing side channels (device and node) are not measured.
- Topic inference sits at the floor by construction (the observer's view is
  constant); the naive-Bayes observer confirms it, it does not prove it.
- One dataset (PMC-Patients), one partition (k-means, 8 hospitals), in-process
  crypto; hospital compute is timed but hospitals would run in parallel on
  their own hardware.

## Addendum: chunked, compressed tables

The first table layout padded every envelope to the node's largest
cluster; measured on the PMC federation, **66% of the 86 MB download was
padding** (text 22%, float16 embeddings 12%). Tables are now built as:
each cluster's payload is zlib-compressed and cut into fixed 16 KB chunks;
chunk i is sealed under the cluster's key with i as associated data and
listed under its own tag H3(out, cluster, i). Tags are pseudorandom, so
which chunks belong together — and each cluster's size — stays hidden,
with padding only in each cluster's last chunk. Embeddings are stored as
int8 with a per-vector scale. The device looks up chunks 0, 1, 2, … until
one is missing, verifies and joins them, and decompresses.

| Layout | Download, 8 PMC hospitals | Largest hospital | MRR P=8 | MRR P=8 hybrid | MRR P=24 hybrid |
|---|---:|---:|---:|---:|---:|
| padded to largest cluster, float16 | 86 MB | 14.5 MB | 0.421 | 0.509 | 0.535 |
| chunked + compressed, float16 | 20.7 MB | — | — | — | — |
| **chunked + compressed, int8 (default)** | **15.0 MB** | **2.8 MB** | **0.423** | **0.508** | **0.536** |

Retrieval is unchanged (int8 moves MRR by ≤0.002); the download is 5.7×
smaller, ~3 KB per record. Timings in that run were taken with two other
experiments on the same machine and are not comparable to the table above.
Compression before encryption is acceptable here because no attacker
controls any plaintext in a node's table and fixed chunks hide per-cluster
lengths; the total chunk count reveals only the collection's total
compressed size, which does not depend on any question. Tests:
`tests/test_blind_unlock.py` (multi-chunk clusters open, equal envelope
lengths, a tampered chunk makes its cluster unopenable, int8 keeps the
ranking, the chunked table is several times smaller).

## Future work (decided: not part of this project)

Blind unlock is the project's solution as built and measured. The following
were designed or discussed and are deliberately left as future work:

| Area | Future work | What it would address |
|---|---|---|
| Scale | blind unlock inside groups of nodes, cells between groups; PIR for envelope fetch | federations of hundreds to thousands of nodes |
| Disclosure | two-level unlock (sub-cluster round) or k-out-of-K oblivious transfer | records released per probe (~10 → ~2–3) |
| Key lifecycle | scheduled rotation with secure deletion of old secrets; threshold OPRF keys (split across servers); hardware-held keys (HSM/TEE) | a leaked old secret opening cached copies |
| Device hygiene | purge old tables on epoch change; keep opened records and derived keys in memory only | copies and plaintext left on the device |
| Credentials | short-lived credentials, a revoke command, usage alerts from the audit log; anonymous role tokens | stolen credentials; nodes learning who asked |
| Malicious nodes | verifiable OPRF (DLEQ proofs of the published key) | key substitution by a node |
| Lighter modes | relay-based fetch (Oblivious HTTP style) for weak devices, stating its weaker guarantee | devices that cannot hold the tables |

What cannot be solved by any design: records a user legitimately opened
cannot be un-revealed; minimising and auditing them is the only lever.


```
python -m eval.run_hyfedrag_compare --queries 1000 --skip-stock-deid \
    --only ours_blind_P4 ours_blind_P8 ours_blind_P16 ours_blind_P24
```

Tests: `tests/test_blind_unlock.py` — every node receives exactly P points
for any question; dummies pass the node's point check and look uniform at the
byte level; unlock opens exactly the chosen clusters by lookup; tables padded,
deterministic and role-scoped; rotated keys lock out cached tables; the budget
counts dummies; blind mode never calls a text or vector tool (simulated and
real MCP). Test counts are not privacy results.
