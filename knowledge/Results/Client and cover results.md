---
tags: [type/result]
---

# Client and cover results (docs/52)

Real MCP nodes, `python -m client`: every node received "3 points, 231 B" in each of three rounds (one real, two cover); only the device knew which was real. Tests: planning touches no network; real = cover on the wire and in the budget; one round per tick; roles hold; unsigned restricted centroids refused. See [[Standalone client]], [[Cover traffic]].
