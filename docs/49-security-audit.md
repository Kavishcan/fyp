# Security audit of the node and device code

## Verdict

An audit of the implementation against its own claims (docs/43–45) found
three holes that let a party with **no credential** bypass the protections,
each confirmed by running the attack against a real MCP node. All three are
fixed and each attack is now a regression test (`tests/test_audit_fixes.py`).

| # | Hole | Attack that worked | Before | After |
|---|---|---|---|---|
| 1 | Experimental Paillier scorer (docs/34) exposed on every node, unauthenticated, over **all** rows | chosen plaintexts x_j = B^j pack many coordinates into one encrypted score | **3 requests recovered 100% of document embeddings, restricted clinical notes included** | off unless the node enables it; never on a gated node; public rows only |
| 2 | Credential gate covered only PSI; text/vector `retrieve` stayed open, `top_n` unbounded | `retrieve("anything", top_n=100000)` | **all 60/60 public documents in one call, no credential** | a gated node refuses open retrieval unless its operator opts in; `top_n` capped at 20 |
| 3 | Daily evaluation budget and audit log held in process memory | 6 requests against a budget of 2 on a spawn-per-call node | **6/6 served** (every call a fresh process); a restart reset the budget; the audit log was never written | SQLite next to the node (0600), one IMMEDIATE transaction per request: **2/6 served**, spent budget survives restart, audit on disk |

**Correction to docs/43.** Its enumeration bound ("8–10 days of one
credential's budget") was measured with an in-process authorizer and was not
true of a real spawn-per-call MCP node, whose budget reset on every call.
It is true now.

## Smaller findings fixed

- OPRF key files written before the 0600 rule stayed world-readable; the
  node now tightens them on every load.
- Restricted-centroid replies were verified only if the node attached a
  signature; a signed node that omits one is now refused (fail closed).
- Re-registering a node reset its trust to the 0.5 prior (trust laundering).
  Re-registering under the same signing key now keeps earned trust.
  Found while fixing it: re-registering any **signed** node always failed,
  because the coordinator bumped the profile version after the node had
  signed it; a same-key re-registration is now a refresh.

De-identification gaps (NIC, passports, date formats, ages over 89,
addresses, relatives' names, surname-first registry names) are fixed —
docs/44 addendum.

## Found, not fixed (stated limitations)

| Finding | Severity | Why not now |
|---|---|---|
| Anonymity cells are rebuilt from the registry per query; one join moved 8 of 16 nodes to new cells, and intersecting before/after cells shrank a node's anonymity set to 1 | high for cells | blind unlock (docs/47) replaces cells as the recommended configuration; cells need epoch-fixed, join-stable construction |
| Cell grouping uses node-declared policy labels | medium | as above |
| The same HMAC client key is installed at every node, so a node can sign requests to other nodes as that client | high | per-node keys or Ed25519 client signatures; anonymous tokens are the stated direction |
| A signed request can be replayed within its UTC day (burns budget) | low | needs a nonce store |
| `psi_envelopes` (per-query PSI) serves restricted envelopes to anyone, revealing their count and sizes | medium | blind unlock's `psi_table` already serves restricted collections only to permitted roles |
| Node registration is not authenticated (Sybil nodes) | medium | needs operator-signed node certificates |
| Retrieved passages enter the LLM prompt without delimiters (prompt injection) | medium, unmeasured | not measured |

## Reproduce

```
pytest tests/test_audit_fixes.py
```

Each test replays one attack; test counts are not security results.
