---
tags: [type/result]
---

# Formal leakage (docs/51)

| Party | Leakage per question |
|---|---|
| any node / coalition | credential id, P, permitted-collection count, arrival time (with [[Cover traffic]]: the fixed ticks) |
| network observer | every node, P points each, sizes, times |
| device | everything (trusted) |

**Claim 1:** the joint node view is independent of the question — statistically, against unbounded, colluding, malicious nodes ([[Dummy points]]). **Claim 2:** the observer's view likewise. **Claim 3:** a client with budget B opens ≤ B envelopes (one-more gap DH, ROM; [[2HashDH key binding]]). **Not claimed:** integrity, DP, device side channels. Surfaced the [[Timing channel]] fix.
