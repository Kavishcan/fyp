# Deployment boundaries and API

This repository is local research infrastructure, not a secured hospital
deployment or a clinical tool. Use public/synthetic data. Any real clinical
deployment would need separate governance, security and regulatory assessment.

## Current process layout

- A Next.js studio calls the FastAPI coordinator.
- The coordinator holds profiles, source handles, raw questions, retrieved
  passages, separate legacy/smart trust state and routing logs.
- In-process sources keep documents inside that coordinator.
- MCP sources are separate local stdio subprocesses started afresh per call.
- Optional external generation sends questions/passages to the configured provider.

SmartRouter is an algorithm module inside the coordinator. It does not create
cryptographic separation or hide the question from its host.

## API surface

| Endpoint | Current purpose |
|---|---|
| GET /health | Health and registered-source count |
| POST /nodes/register | Submit documents to create a simulated source |
| GET /nodes | Source status; displayed trust is currently legacy trust |
| DELETE /nodes/{node_id} | Remove a registered source |
| GET /nodes/available | List locally prepared additional MCP node specifications |
| POST /nodes/activate | Register a prepared MCP node |
| POST /query | Execute legacy or opt-in smart routing |
| GET /audit/{query_id} | Retrieve selection trace; includes smart routing_details |

POST /nodes/register does not onboard a remote institution from a profile-only
request. mcp_endpoint is reserved, not a working remote enrollment mechanism.
The actual schema is backend/api/schemas.py.

## Smart request

```json
{
  "question": "COVID treatment research",
  "routing_mode": "smart",
  "max_nodes": 5,
  "exposure_budget": 2,
  "minimum_gain": 0.05,
  "minimum_trust": 0,
  "aggregation": "mean"
}
```

max_nodes is a hard cap, not a target. Budget defaults to max_nodes if omitted;
unit costs count recipients. genuine_k is legacy-only. Nonzero query sigma is
rejected in smart mode. Zero budget dispatches nothing.

The response includes costs, selection scores, stopping reason and retrieval
failures. Empty evidence skips generation. Use the
[implementation guide](13-smart-router-implementation.md) for startup commands.

## What authorization currently means

A source with no policy labels is public under the demo convention. For smart
mode, all its labels must be included in the coordinator's allowed_policy_labels.
The query payload cannot grant itself those permissions or advertise source costs.

This is a selection hook, not per-user access control. Registration endpoints,
profile identity, signatures, multi-tenancy and mTLS are not secured production
features. An untrusted party must not be allowed to administer this demo.

## Privacy limitations

Raw queries reach selected nodes; returned passages reach the coordinator and
possibly a generator provider. Regex redaction is not complete de-identification.
Centroids can carry information about source contents. Public audit logs would
expose the source identities and decisions being studied.

A strict contact budget limits recipients under an explicit accounting rule.
It does not establish query secrecy, anonymity, DP or protection of generated
outputs. Do not call contact costs measured legal/compliance costs without a
separately justified model.

## Before a real deployment

Implement authenticated source/user identities, signed profile verification,
persistent trust and replay controls, node-side access enforcement, protected
logs, secret management, measured timeouts/retries, and clear trust boundaries.
Evaluate generation disclosure and document handling with appropriate domain
experts. These are future requirements, not properties currently delivered.

## Performance

Selection timing is logged. The live API retrieves sequentially, so latency can
accumulate across sources; it is not simply the latency of the slowest node.
Network byte counts and all-stage timings still need measurement. No clinical
latency target is claimed as achieved.
