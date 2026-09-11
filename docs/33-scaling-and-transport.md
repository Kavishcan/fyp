# Scaling and transport cost: measured results

## Verdict

**Recall at a fixed contact cap falls steadily with source count.** With 6
contacts, v2/legacy source recall goes 0.872 → 0.707 → 0.518 from 30 to 100
to 300 sources; smart goes 0.692 → 0.429 → 0.273. Nothing in the router
compensates for a growing pool — the cap is the cap. This is the expected
shape, now measured rather than assumed.

**v2 and legacy remain identical at every scale** (same recall, contacts and
audit cost to three decimals, as in docs/31). v2 is not a better router at
any N tested.

**v2's plaintext-free wire is ~55x heavier per contact than a text request.**
A 768-d routing vector serialises to ~17 KB; a text query to ~0.3 KB. At six
contacts v2 sends ~102 KB per query, more than broadcasting the text to 100
sources (31 KB) and comparable to broadcasting it to 300 (90 KB). Removing
the plaintext from the wire has a communication cost the design notes did not
account for.

**Routing latency is O(N) in the shipped implementation**: every mode
rebuilds its candidate index per query, exactly as api/state.py does. v2 goes
0.27 → 1.11 → 2.58 ms per query from 30 to 300 sources; smart 1.6 → 6.4 →
17.4 ms. Sub-3 ms at 300 for v2 is not a bottleneck; the O(N) shape means a
persistent index would be needed well before 1,000 in the live path.

**With real MCP subprocesses, transport dominates everything.** At 30
registered nodes a query takes ~2.7–2.9 s end to end, of which routing is
under 1 ms and each of the six node contacts ~450–490 ms — the cost of the
client's deliberate spawn-a-subprocess-per-call design (interpreter start-up
plus profile construction). Registration is ~0.45 s per node.

**1,000 sources was not run.** The 300 tier took ~8–10 min per seed to embed
on this machine and the 1,000 tier was projected at over an hour; it was
stopped at the user's request. The 300 tier has two seeds, not three. No
claim is made about 1,000 sources.

## Setup

In-process scaling: `eval/run_scaling.py`. Five BEIR corpora (arguana,
nfcorpus, scifact, fiqa, scidocs), 6 / 20 / 60 virtual sources per corpus
→ 30 / 100 / 300 sources; 100 judged queries per corpus (~500 per seed);
`BAAI/bge-base-en-v1.5` normalised via `eval/embed_cache.CachedEmbedder`
(cache changes no embedding); 6-contact cap, `genuine_k=2`, `coarse_k=12`,
unit cost, sigma 0. Seeds 11/22/33 (300: 11/22). Documents per source shrink
with tier (110 → 53 → 40) because nfcorpus's ~38 qrels per query pull nearly
its whole corpus in at every tier and the small corpora cannot supply 40 docs
× 60 nodes; this is reported, not corrected. trec-covid was excluded (50
queries, ~1,300 qrels each).

Real transport: `eval/run_mcp_transport.py`. 30 node data files from
`data/mcp_nodes*` (real BEIR/MMLU slices, not qrel-aligned, so **no recall**),
each one `python -m nodes.mcp_server` process over MCP stdio, 16 real BEIR
query texts, legacy and v2, 6-contact cap. The routing embedder in this path
is the live demo's 256-d hashing placeholder, so its routing decisions are not
those of the bge-base rows above. Timings from `api/state.py` instrumentation
(`stage_latency_ms`, `bytes_transferred`), added for this study and recorded
on every query from now on.

Bytes everywhere are UTF-8 JSON application payloads — no MCP framing, no
transport overhead.

## In-process scaling (mean over seeds)

| Sources | Mode | Recall | Contacts | Audit | A2 prec. | Routing ms | p95 ms | Req. bytes/query |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 30 | broadcast | 1.000 | 30.0 | 27.5 | 0.013 | 0.00 | 0.00 | 9,271 |
| 30 | oracle | 1.000 | 2.5 | 0.0 | 1.000 | 0.00 | 0.00 | 419 |
| 30 | legacy | 0.872 [0.868, 0.876] | 6.0 | 4.39 | 0.335 | 0.45 | 0.81 | 1,854 |
| 30 | v2 | 0.872 [0.868, 0.876] | 6.0 | 4.39 | 0.353 | 0.27 | 0.45 | **102,025** |
| 30 | smart | 0.692 [0.664, 0.713] | 6.0 | 5.29 | 0.131 | 1.59 | 2.23 | 1,854 |
| 100 | broadcast | 1.000 | 100.0 | 96.0 | 0.018 | 0.00 | 0.00 | 30,844 |
| 100 | oracle | 1.000 | 2.8 | 0.0 | 1.000 | 0.00 | 0.00 | 443 |
| 100 | legacy | 0.707 [0.703, 0.713] | 6.0 | 4.60 | 0.197 | 1.17 | 2.12 | 1,851 |
| 100 | v2 | 0.707 [0.703, 0.713] | 6.0 | 4.60 | 0.224 | 1.11 | 2.24 | **102,026** |
| 100 | smart | 0.429 [0.398, 0.463] | 6.0 | 5.55 | 0.115 | 6.38 | 11.05 | 1,851 |
| 300 | broadcast | 1.000 | 300.0 | 294.1 | 0.007 | 0.01 | 0.01 | 90,399 |
| 300 | oracle | 1.000 | 2.9 | 0.0 | 1.000 | 0.00 | 0.00 | 440 |
| 300 | legacy | 0.518 [0.505, 0.530] | 6.0 | 5.12 | 0.099 | 2.45 | 2.94 | 1,808 |
| 300 | v2 | 0.518 [0.505, 0.530] | 6.0 | 5.12 | 0.137 | 2.58 | 3.36 | **102,026** |
| 300 | smart | 0.273 [0.268, 0.279] | 6.0 | 5.72 | 0.041 | 17.43 | 21.82 | 1,808 |

Seeds share documents and queries; ranges show partition sensitivity, not
confidence intervals. A2 precision falls with N for every mode including
broadcast, because topics repeat less often across ~500 queries as the
partition gets finer — it is not evidence that any mode becomes more private
at scale (the docs/31 warning applies: low A2 precision alone is not privacy,
and smart's low values track its poor recall).

Absolute recall here is not comparable to docs/31 (0.711 at 24 sources):
five corpora instead of three make cross-domain routing easier at the
smallest tier, and documents per source differ.

## Real MCP transport, 30 nodes (mean over 16 queries)

| Mode | Register/node | Query total | p95 | Embed | Routing | Per contact | p95 | Req. bytes | Resp. bytes | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy | 461 ms | 2,916 ms | 3,905 | 0.12 ms | 0.74 ms | 486 ms | 543 | 3,654 | 5,248 | 0 |
| v2 | 451 ms | 2,702 ms | 2,748 | 0.07 ms | 0.48 ms | 450 ms | 485 | 7,831 | 5,905 | 0 |

Six contacts per query, sequential. Over 99.9% of query time is the six
subprocess round trips; routing is negligible. v2's request here is only ~2x
legacy's because the demo embedder is 256-d and arguana query texts are long
paragraphs; with the 768-d model the in-process figure above (55x) applies.

This is 30 genuinely separate OS processes with real MCP protocol traffic on
one laptop. It is not a network deployment: no network latency, no
concurrency, and no node ran on another machine.

## What this does not establish

- Anything at 1,000 sources. Not run.
- That the recall decline is a property of the router rather than of a fixed
  cap: oracle stays at 1.000 with ~2.9 contacts, so the relevant sources are
  present and findable; the routers' ranking simply misses them more often as
  the pool grows. Whether a larger cap or a persistent index changes the slope
  was not tested.
- Any answer-quality result.
- Transport cost with a persistent MCP session, which would remove most of
  the ~450 ms per contact. That is an implementation choice, not a measured
  limit of MCP.
- Network bytes: framing and compression were not measured.

## Reproduce

```
python -m eval.run_scaling --nodes-per-corpus 6 20 60 --seeds 11 22 33
python -m eval.run_mcp_transport --node-counts 30 --modes legacy v2 --n-queries 16
```

Tests: `tests/test_scaling_and_transport.py`. Test counts are not scaling or
privacy results.
