# FedSafeRouter studio

This Next.js frontend is a demonstration surface for the FastAPI backend.

## Run

```sh
npm install
npm run dev
```

The API base defaults to http://localhost:8000; set NEXT_PUBLIC_API_BASE_URL
when using another backend address. See the root README for backend startup.

## Current routing mode

The chat panel omits routing_mode, so the backend uses legacy mode. Its diagram,
fixed genuine/decoy controls and node trust display are legacy-oriented.

lib/api.ts includes smart request/response types, but the studio does not yet
offer a smart-mode selector or explain SmartDecision traces. Use the
[smart API guide](../docs/13-smart-router-implementation.md) to run that algorithm
now. Do not present the current visual diagram as the new algorithm.

A future UI change should distinguish mode, budget, maximum contacts, adaptive
selected count and stop reason, and should not label the consistency score as
verified source honesty.

## Scope

This is not a secured multi-user deployment. It can display query text,
passages, source identities and audits. Use public/synthetic data.
The research contribution is the routing method and evaluation, not the studio.

Keep lib/api.ts synchronized with backend/api/schemas.py. Check types with:

```sh
./node_modules/.bin/tsc --noEmit --incremental false
```
