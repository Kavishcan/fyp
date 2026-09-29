---
tags: [type/mechanism]
---

# Cover traffic (constant rate, docs/52)

`CoverTrafficScheduler` sends exactly one round per tick: the queued question if any, else a cover round of P dummies to every node. Planning happens at submit time; daily fetches on the tick; a timed run finishes local answers after the network schedule. Real and cover rounds are identical on the wire and in the budget. Hides *when* the user asks. Cost: ticks/day × P evaluations per node; a question waits up to one tick; bursts queue. See [[Timing channel]], [[Session linkage]].
