# Standalone client and constant-rate cover traffic

## Verdict

Two standing caveats of blind unlock (docs/47, 51) are removed by code:

| Caveat before | Now |
|---|---|
| "The API process sees the question" — in the studio the coordinator plays the device | **`client.Device`**: the whole query path as a library the user runs. It talks to each node directly through a transport; no server is in the path, and no component other than the device object ever holds the question. Verified over real MCP node processes with every text/vector tool patched to fail. |
| "Nodes and observers see *when* the user asks" | **`client.CoverTrafficScheduler`**: exactly one round per fixed tick — the queued question if there is one, otherwise a cover round of P dummy points to every node. Questions are embedded and planned when submitted, so at the tick a real and a cover round are sent the same way. On the wire they are identical: same nodes, same order, same point count, same request bytes (tested), and the same budget charge. |

Together with docs/51, the per-question leakage to nodes and observers
becomes: **an authorised credential is active at a fixed rate** — not what
it asks, not which node matters, not when it asks. The credential id is
still visible to nodes (anonymous tokens are future work, docs/47).

## Design

```text
client.Device (the user's machine)
  connect(transport)  → verify the signed profile, check the routing space,
                         download the blind table, fetch the day's restricted
                         centroids (verified; fail closed)
  plan(question)      → embed, score every node's clusters, global top-P,
                         blind real ids, draw dummies        [no network]
  send(plan)          → privacy/blind_unlock.blind_round: every node, sorted,
                         then unlock; tables refreshed by epoch only
  finish(...)         → hybrid rank, top-k evidence, local generation
  cover()             → blind_round(cover_plan): P dummies to every node

client.CoverTrafficScheduler(device, interval_s)
  submit(question)    → plan now (local), queue it
  tick()              → refresh daily fetches; send ONE round: queued plan or cover
  run(N)              → pace N ticks with one monotonic clock, then finish local answers

client.transport      → MCPTransport (real node process) | LocalTransport (in-process,
                        gated exactly like the MCP server)
python -m client      → command-line asker (optionally inside a cover schedule)
```

`blind_round` is the single implementation of a round: the API coordinator
(`AppState._blind_retrieve`) now calls it too, so the studio and the
standalone client run the same protocol code.

Two timing details the design closes: planning (embedding, scoring, blinding)
never touches the network (tested by patching every transport call to fail
during `plan`), and the daily restricted-centroid fetch happens at connect
time and on the scheduler's tick, never when a question is typed.

## Costs

- **Budget.** Every tick charges P evaluations at every node whether or not
  a question was asked (tested: a real and a cover round each charge P).
  A daily budget must cover ticks/day × P. With P = 8 and a 60 s tick, a
  node sees 11,520 evaluations per credential per day.
- **Latency.** A question waits up to one tick before it is sent.
- **Rate.** Timing is hidden only for questions asked no faster than the
  tick rate; a burst queues and is sent one per tick.
- Hospital load is per tick, not per question.
- The finite CLI example picks one random tick for its question, with cover
  rounds before and after it. It demonstrates equal-size rounds and pacing;
  a finite demo is not a substitute for an always-on scheduler.

## What this does not establish

- The credential identity is still visible to every node (who is active).
- Device-local side channels (CPU, cache) and a compromised device are out
  of scope.
- Network-level timing jitter was not measured; the schedule is enforced by
  the device's clock.
- A manual sequence of `tick()` calls does not itself enforce pacing; use
  `run()` or an always-on scheduler for the timing claim. `run()` completes
  local generation after its scheduled rounds so generation cannot delay a
  later network contact. A slow node or clock drift can still miss a tick.
- The studio still uses the API coordinator as the device for the demo; the
  standalone client is the deployment path.

## Reproduce

```
cd backend
python -m client --nodes ../data/mcp_nodes/nfcorpus_1.json ../data/mcp_nodes/arguana_1.json \
    --question "does vitamin D supplementation reduce cancer risk" --probes 3 --cover-ticks 3 --interval 0.5
```

Output on real MCP nodes: every node received "3 points, 231 B" in each of
three rounds (one real, two cover); the device alone logged which was real.

Tests: `tests/test_client.py` — every node receives the same points; planning
touches no network; a cover round equals a real round on the wire and in the
budget; one round per tick; roles hold through the client (a clinician
unlocks clinical notes, a researcher never does); unsigned restricted
centroids are refused; a device over real MCP nodes with no server. Test
counts are not privacy results.
