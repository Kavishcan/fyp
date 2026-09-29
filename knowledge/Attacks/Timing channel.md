---
tags: [type/attack, status/fixed]
---

# Timing channel

1. **Found while writing [[Formal leakage]]:** the first blind round unlocked each node's reply before contacting the next, so gaps depended on where real probes were. Fixed: contact every node first, then unlock.
2. **When the user asks:** fixed by [[Cover traffic]] (one round per tick).
Device-internal side channels remain out of scope.
