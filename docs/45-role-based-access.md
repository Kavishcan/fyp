# Role-based access to node collections

## Verdict

**A node now serves each client only the document collections its role
allows, and it enforces this inside the PSI step — where it cannot see what
is being asked for.**

A hospital node holds named collections (`public`, `research`,
`clinical_notes`, …) and publishes, in its signed profile, a policy mapping
roles to the collections they may read. Which roles a *client* holds is
decided by the federation and stored in the node's allow-list; the client
cannot claim one. Measured with the real code paths on a node holding 150
documents per collection, with every client acting adversarially — probing
every published cluster of every collection, ignoring its own role:

| Client | Public | Research | Clinical notes |
|---|---:|---:|---:|
| authorised, no role | 1.000 | 0.000 | 0.000 |
| researcher | 1.000 | 1.000 | 0.000 |
| clinician | 1.000 | 1.000 | 1.000 |
| **researcher claiming to be a clinician** | 1.000 | 1.000 | **0.000** |
| anyone, via the unauthenticated legacy/v2 retrieve paths | 1.000 | **0.000** | **0.000** |

(fraction of each collection's documents obtained; policy: researcher →
research, clinician → research + clinical notes; public for every authorised
client)

The access matrix is exactly the policy. Lying about a role gains nothing,
because the node reads roles from its own allow-list. The old text and
vector retrieve tools — which have no credential — can no longer reach
anything but `public`.

## How it works when the node is blind

The node never sees which cluster is being asked for (the ids are blinded,
docs/36), so it cannot check "is this cluster allowed?". Instead:

- **Each collection has its own OPRF key.** Clusters never mix collections;
  each collection's envelopes are sealed under keys derived from its own
  OPRF key, with the collection name bound into the key.
- **The node evaluates only under permitted keys.** After the credential
  check (docs/43), the node looks up the client's roles in its allow-list,
  computes the permitted collections from its published policy, and returns
  one evaluation per blinded point *per permitted collection*.
- **Nothing else can open.** A researcher who probes a clinical cluster
  receives no evaluation under the clinical key, so no clinical envelope
  can ever be decrypted — whatever ids it sent.

The node still learns nothing about which cluster or which collection
matched: it learns the client's roles, which it already knew from the
allow-list.

Backwards compatible by construction: a node with plain documents has one
collection, `public`; its envelope keys are byte-identical to before, and an
open node (no allow-list) serves only `public`. A restricted collection on
an open node is readable by no one.

## Configuration

Node data file:

```json
{
  "node_id": "st_marys",
  "documents": [{"text": "…", "collection": "clinical_notes"}, "a plain string is public"],
  "access_policy": {"researcher": ["research"], "clinician": ["research", "clinical_notes"]}
}
```

or `"collections": {"public": [...], "research": [...], "clinical_notes": [...]}`.
Allow-list (`<node>.clients.json`, 0600): each client gets `"roles": [...]`
beside its key and daily budget. The OPRF keys persist per collection in
`<node>.psi.key` (0600). Client side: `Credential(client_id, key, roles)` —
the roles there only decide which clusters the client bothers to probe; the
node never trusts them.

## What this does not establish

- **Topic structure of restricted collections is public.** Their cluster
  centroids (≥5 documents each, docs/35) and the coarse routing profile are
  in the signed profile every member can read. Hiding them needs
  role-scoped profile publication — not built.
- **Roles, not attributes.** No per-patient consent, time windows, purpose
  of use or break-the-glass; a role reads a whole collection.
- **Issuance and revocation** of roles is the federation operator editing
  an allow-list; no directory integration (LDAP) or policy engine (OPA).
- Everything a clinician obtains is still de-identified text (docs/44); a
  role does not unlock raw identifiers.
- Budgets (docs/43) are per client, not per role.

## Reproduce

```
python -m eval.run_rbac
```

Tests: `tests/test_rbac.py` — the permission rule, an unevaluated
collection never opening, byte-compatibility of single-collection nodes,
role decides clinical access, a client lying about its role gains nothing,
legacy/v2 paths never return restricted documents, policy and cluster
collections are covered by the profile signature, and a real MCP node
enforcing roles from its allow-list. Test counts are not an access-control
audit.
