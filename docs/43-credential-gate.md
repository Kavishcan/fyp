# Credential gate on the PSI step

## Verdict

**"The node serves only credentialed clients" is now true of the code, and
enumeration has a measured bound with an identity attached.**

`privacy/credentials.py` puts an authorisation check in front of the OPRF
evaluation: the client signs (node id, UTC day, blinded points) with a shared
HMAC key the federation issued; the node checks the signature against its
allow-list, charges the evaluations to that client's daily budget, logs who /
when / how many / outcome, and only then touches its OPRF key. A refusal
evaluates nothing, so nothing can open — the gate refuses without leaking.

Measured with the real gate in `eval/run_psi_enumeration.py` (adaptive
enumerator, nprobe 2, three seeds):

| Clusters | Queries to dump the table, no gate | Days to dump at 20 evaluations/day, gated |
|---:|---:|---:|
| 20 | 10 | 1 |
| 150 | 75 | **8** |
| 200 | 100 | **10** |

At the docs/35 operating point (~150–200 clusters) a single credential
needs 8–10 days of its entire budget to dump one node, and every one of
those days is a line in that node's audit log under that client id. The
budget is per credential; a pool of colluding credentials divides the days,
which is why the allow-list is the federation operator's control, not the
node's alone.

Verified end to end: a gated real MCP node refuses `psi_evaluate` without a
credential (the coordinator records `PermissionError`, no citation), serves
with one, and refuses again when the day's budget is spent.

## Design

| Element | Where | Note |
|---|---|---|
| `Credential(client_id, key).sign(node_id, blinded)` | client | HMAC-SHA256 over node id, day, and the exact blinded points — cannot be replayed against another node, day, or query |
| `Authorizer.check(auth, blinded)` | node, before `PSINode.evaluate` | unknown client / stale day / bad signature / budget exhausted → `Unauthorized(reason)`, nothing evaluated, audit line written |
| Allow-list `<node>.clients.json` (0600) | node | `{client_id: {key_hex, daily_evaluation_budget}}`; absent file = open node, the prototype's prior behaviour |
| `AppState.credential` | coordinator (device) | signs every PSI contact; `None` presents nothing |
| MCP tool `psi_evaluate(blinded, auth)` | node server | returns `{"error": reason}` on refusal; the client raises `PermissionError`, psi mode logs it as a retrieval error and the budget is still charged on the client side |

What the node learns from the gate: which credential probed it, on which
day, with how many points. Not the query, not the cluster ids. Hiding *which
member* asked needs an anonymous credential (Privacy Pass-style tokens) —
the design direction, not built.

## What this does not establish

- Transport security: TLS on every hop is assumed in deployment; the
  prototype's MCP is local stdio and there is no wire to protect.
- Key issuance and revocation: the allow-list is a file the operator edits;
  no key authority is built (docs/03 target).
- Resistance to a pool of colluding credentials, or to a compromised client
  machine (outside the trust boundary by assumption).
- Any change to what an honest client is served: ~36 passages per contact
  as docs/35–36; the gate limits how many probes, not how much each probe
  returns. In-cluster private scoring remains the way to lower that.

## Reproduce

```
python -m eval.run_psi_enumeration --clusters 20 150 200 --rate-limit-per-day 20
```

Tests: `tests/test_credentials.py` (refusal before evaluation for every
tamper, budget bounds the opened set, allow-list round trip, gated real MCP
node). Test counts are not security results.
