---
tags: [hub, type/concept]
---

# Threat model

| Party | Sees | Trusted? |
|---|---|---|
| [[Device]] (user's machine, [[Standalone client]]) | everything | **yes** — the trust boundary |
| Hospital node ([[MCP node]]) | credential id, P uniform points per round, tick times | honest-but-curious about the question; may lie about content |
| Network observer | every node contacted, P points each, sizes, times | no |
| Colluding hospitals | the union of the above | no — learns nothing more ([[Formal leakage]]) |
| Malicious client | what a credential may unlock | bounded by [[Credential gate]] and [[Role-based access]] |

Leakage per question with [[Cover traffic]]: *an authorised credential is active at a fixed rate*. Not what, not which hospital, not when.

Out of scope: a compromised device; de-identification failures inside opened records ([[Node-side de-identification]]); which credential is active ([[Anonymous role tokens]] — future work).

See [[Trust boundary]], [[Honest-but-curious]], [[Formal leakage]].
