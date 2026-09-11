# Privacy cases, attack cases, enumeration, and persistent transport

## Verdict

**On the project's own 200 synthetic privacy cases, PSI dispatch exposes
none of the three fictional sensitive values to any contacted node; every
other mode exposes all three, and the repository's regex redaction removes
only the email.** Routing quality is identical across modes by construction.

| Mode | Input | Values exposed to nodes | Reached allowed client (genuine / dispatched) | Unnecessary contacts (genuine / dispatched) |
|---|---|---:|---:|---:|
| legacy | as sent | **1.000** | 0.540 / 0.600 | 1.44 / 5.35 |
| legacy | regex-redacted | 0.667 | 0.560 / 0.620 | 1.42 / 5.33 |
| legacy | original, no PII (reference) | 0.000 | **0.620** / 0.680 | 1.36 / 5.27 |
| smart | as sent | 1.000 | 0.440 / 0.615 | 1.55 / 5.34 |
| v2 | as sent | **1.000** (nearest-neighbour inversion of the vector) | 0.540 / 0.600 | 1.44 / 5.35 |
| **psi** | as sent | **0.000** (blinded; 0 repeated-blinding collisions) | 0.540 / 0.600 | 1.44 / 5.35 |

Two things beyond the headline:

- **The PII prefix itself damages routing.** The same requests without it
  reach their allowed client 0.620 of the time against 0.540 with it: the
  "My name is …, my email is …" preamble pulls the embedding away from the
  question. Redaction before embedding is therefore a routing improvement
  as well as a privacy control, and PSI does not provide it — psi mode
  routes on the augmented embedding and inherits the 0.540. The two
  controls are complementary, not alternatives.
- **Unnecessary contacts are ~5.3 of 6 in every mode.** Each case allows one
  client; the cap is six; decoys fill the rest. That is the A2 price made
  visible on this dataset, not a routing failure. The genuine-set figure
  (1.4 of 2 not allowed) is the routing error.

**The 60 attack cases succeed completely in every mode.** A source
publishing a forged profile at the mean of the attack queries is selected
for 100% of them and, because each contacted node's top passage is cited
with no cross-node evidence filter, its "TEST ATTACK" passage is cited 100%
of the time — in psi mode too. Encryption does nothing for A3; this
reproduces docs/32's finding on the project's own attack set, and adds that
the shared PII preamble makes the attack queries unusually similar to one
another, which makes the mean-profile forgery unusually effective.

**Enumeration is a rate-limited cost, not an impossibility.** A malicious but
authorised client that targets clusters deliberately opens a whole node's
table in exactly ⌈clusters / nprobe⌉ queries — 75 queries for a
150-cluster node, under a day at 100 queries/day. Without the OPRF it would
be zero queries (offline). The OPRF makes dumping a node cost one evaluated
query per two clusters and leaves an audit trail; it does not prevent it.

**Persistent MCP sessions remove the transport overhead.** Same 30 real
nodes, 16 queries, 6 contacts, one live server process per node:

| Mode | Query total (spawn-per-call → persistent) | Per contact | Response bytes |
|---|---:|---:|---:|
| legacy | 2.43 s → **10 ms** | 404 → 2 ms | 5.2 KB |
| v2 | 2.44 s → **9 ms** | 406 → 1 ms | 5.9 KB |
| psi | 4.85 s → **61 ms** | 808 → 10 ms | 1.01 MB |

PSI's real cost over MCP is ~10 ms per contact and ~170 KB per 40-document
node; the earlier seconds were interpreter start-up.

**Local generation exists and is untested for quality.**
`generation/ollama_generator.py` (`LLM_PROVIDER=ollama`) talks only to
localhost and refuses a remote host, so query and passages stay on the
device as docs/03 requires. Ollama is not installed on this machine; no
answer-quality number was produced.

## Setup

Cases: `fedrag-dataset/data/processed/privacy/` — 200 FeB4RAG requests
prefixed with a fictional name, email and reference id (`example.invalid`,
`TEST-0001` — reserved values, no real PII), each with one `allowed_client`;
60 attack cases of three declared types sharing one malicious payload.
Engines: the 13 FeB4RAG engines with local BEIR corpora, profiled from 1,500
sampled documents each with bge-base (as docs/36), seed 11. Six-contact cap,
`genuine_k=2`, `coarse_k=12`. `eval/run_privacy_cases.py`.

Exposure: text modes by string match; v2 by `attacks/a1_inversion`
nearest-neighbour recovery against a pool of the 200 augmented and 200
original requests (a lower bound on a stronger inverter); psi by
construction, with an empirical check that two blindings of the same case
share no bytes. "Reached allowed" = the allowed client is in the genuine
top-2 / in the dispatched six. Attack: attacker profile =
`nodes/simulator.forge_profile` at the mean of the 60 attack-query vectors.

Enumeration: `eval/run_psi_enumeration.py`, real OPRF/PSI code against a
synthetic table, adaptive versus random probing, three seeds.

Transport: `eval/run_mcp_transport.py --persistent`, `PersistentMCPNodeHandle`
(one server process and MCP session per node on a background event loop).

## What this does not establish

- Anything about output leakage or generation: no answers were produced.
- That psi resists a stronger inverter: there is no vector to invert; the
  claim is the DDH reduction, not an empirical attack result.
- Attack resistance of any kind. The attack cases measure the absence of a
  defence; the three declared attack types share one payload, so nothing
  distinguishes them here.
- Enumeration against a pooled adversary (many credentials) or with the
  fetch-set knob, and whether ~170 KB per contact is acceptable at real node
  sizes.
- Redaction quality: the regex heuristic caught one of three value types.

## Reproduce

```
python -m eval.run_privacy_cases
python -m eval.run_psi_enumeration
python -m eval.run_mcp_transport --node-counts 30 --modes legacy v2 psi --n-queries 16 --persistent
```

Tests: `tests/test_privacy_cases.py`, `tests/test_persistent_mcp.py`,
`tests/test_ollama_generator.py`. Test counts are not privacy results.
