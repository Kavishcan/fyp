---
tags: [type/mechanism]
updated: 2026-09-30
---

# Cover traffic

The scheduler uses one monotonic timed run and sends a padded round on each scheduled tick. Real work can replace a cover round; planning is local and local answer generation finishes after the schedule.

The CLI now uses one schedule rather than repeatedly restarting one-tick runs. Direct tick calls do not pace themselves. Slow nodes can miss deadlines; finite schedule participation is visible. No universal timing-anonymity guarantee has been demonstrated.

Every cover tick consumes per-node evaluation budget. See [[Timing channel]], [[Client and cover results]].

## Implementation / Experiment Sources

- [backend/client/cover.py](../../backend/client/cover.py)
- [backend/client/__main__.py](../../backend/client/__main__.py)
- [docs/52-standalone-client-and-cover-traffic.md](../../docs/52-standalone-client-and-cover-traffic.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
