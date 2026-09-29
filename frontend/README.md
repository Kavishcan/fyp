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

The chat panel selects blind unlock with eight probes and hybrid reranking by
default. It also lets you switch to legacy, smart, v2 or PSI for comparison.
The backend API itself still defaults to legacy when routing_mode is omitted.

The studio sends the question to the API coordinator, which plays the device
for the demo. It does not provide the standalone client's query boundary or
fixed-rate cover traffic; use `python -m client` from the backend for those.
The architecture view and audit trace are explanatory, not security proofs.

## Scope

This is not a secured multi-user deployment. It can display query text,
passages, source identities and audits. Use public/synthetic data.
The research contribution is the routing method and evaluation, not the studio.

Keep lib/api.ts synchronized with backend/api/schemas.py. Check types with:

```sh
./node_modules/.bin/tsc --noEmit --incremental false
```
