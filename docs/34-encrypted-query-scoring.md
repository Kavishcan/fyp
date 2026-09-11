# Encrypted query scoring: first query-privacy milestone

## Scope

The project remains query-privacy-aware Federated RAG on main. This milestone
adds Paillier encrypted similarity scoring, not a new routing algorithm and
not a complete private retrieval or generation system. Existing query modes
and the evidence-budget branch are unchanged.

Trusted coordinator: receives the user's query, embeds it, routes locally and
holds an ephemeral decryption key. Honest-but-curious sources: hold documents,
receive only a public key and dense ciphertext vector, and return encrypted
scores for every local row. The coordinator decrypts and ranks locally.
It does NOT send selected document IDs back, fetch passages or call an LLM.
Those operations are deliberately absent, not silently replaced by plaintext.

## Implementation

- `backend/privacy/encrypted_scoring.py`: python-paillier 1.5.0, 2048-bit key,
  fixed-point normalized vectors (scale 1,000,000), encrypted integer dot product.
- `backend/nodes/mcp_server.py`: `score_encrypted_query` tool over actual stdio MCP.
- `backend/nodes/mcp_client.py`: encrypted-only client call; no fallback.
- `backend/api/private_scoring.py`: contact-capped coordinator using the existing
  v2 source/decoy selector, with neutral trust and no trust updates.
- `POST /query/private-score`: explicit experiment, disabled unless the server
  has `ENABLE_PRIVATE_SCORING=1`; the regular `/query` is NOT protected by it.

All query coordinates, including zeros, are independently encrypted. The fixed
integer representation avoids query-dependent floating-point exponents or
sparse coordinate lists. Each recipient receives freshly randomized ciphertexts
under one per-query keypair. Responses are rerandomized before serialization.
Private key factors, query text, ciphertexts and decrypted rankings are not
written to this endpoint's application audit log. This does not police reverse
proxy logging, process memory, crash dumps or operating-system access.

The full-index score response is query-independent in row count/order. No local
encrypted top-k protocol is claimed. At most 128 rows per node and 1,024 vector
dimensions are accepted. Oversized indexes fail; they are never truncated or
retried with plaintext. Every attempted source remains charged to the budget.
JSON byte counts exclude MCP envelopes, initialization and operating-system I/O.

## Threat-model boundaries

| Asset or risk | Status |
|---|---|
| Raw query/vector in source scoring request | Replaced by Paillier ciphertexts |
| Query confidentiality from coordinator | Out of scope: coordinator trusted |
| Source-contact identities and patterns | Still visible; existing decoys are not a formal guarantee |
| Query linkability | Ephemeral public key links contacts within a query; fresh keys per query |
| Timing, dimensions, encoder ID, index size | Still visible |
| Retrieved document access pattern | No fetch performed; PIR/oblivious fetch remains missing |
| Document privacy from coordinator | Full score vectors revealed; not a document-private protocol |
| Malicious sources / chosen responses | Not protected: no verifiable computation or malicious-security proof |
| End-to-end query confidentiality | Not established |

Do not enable this unauthenticated demo API on a public network. The environment
flag is an experiment switch, not access control. The existing policy-label
filter is also not production authorization. Authentication, resource quotas,
key lifecycle review and independent protocol/security review are required.
The Python library itself documents that it has not been independently audited.
Using a standard primitive does not make this composition production secure.

## Use

Install the optional dependency into the existing environment:

```sh
.venv/bin/python -m pip install -r backend/requirements-private.txt
ENABLE_PRIVATE_SCORING=1 .venv/bin/uvicorn api.app:app --app-dir backend --host 127.0.0.1 --port 8000
```

Against registered, compatible, small nodes:

```json
{"question":"tumour chemo protocol","max_sources":3,"genuine_k":1,"exposure_budget":3,"final_k":5}
```

Send this to `/query/private-score`. The response is ranked local document
indices and scores, not an answer. The indices are only experiment output;
no stable document-version/fetch contract has been implemented. Nodes must use
the same shared encoder; this mode does not retain heterogeneous local encoders.
All-document scoring is computationally expensive; no scaling claim is made.

## Verification and next steps

Measured smoke result (`experiments/encrypted-scoring-smoke-v1.json`): three
synthetic queries, three documents, 256-dimensional hashing encoder, one real
MCP node per query. All three top-1 results matched plaintext cosine. The exact
fixed-point score error was zero; maximum float-cosine error was 6.19e-7.
Each request was 263,784 JSON bytes and each response 3,252 bytes. End-to-end
time was 18.60-19.50 seconds per query, including key generation and encryption;
the MCP round trip itself was 1.07-1.35 seconds. This is a slow correctness
prototype, not a deployable latency result or realistic retrieval-quality study.
There is no measured encrypted-payload attack-success rate: do not report zero
leakage merely because a plaintext inversion attacker cannot consume ciphertext.

Tests compare encrypted scores to the exact fixed-point plaintext computation,
exercise randomized dense serialization, reject malformed requests, enforce
caps/policy filtering, and verify no plaintext fallback, fetch or generation.
A real MCP fixture tests 256 dimensions. These are correctness checks, not
measurements of attack success or a cryptographic proof.

```sh
env PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
env PYTHONPATH=backend .venv/bin/python -m eval.run_encrypted_scoring_smoke --output experiments/encrypted-scoring-smoke-v1.json
```

Next: establish the observer model and measure residual contact-pattern attacks;
choose and review a private fetch protocol; then connect generation within the
trusted boundary and evaluate answer quality, leakage and full transport costs.
Do not send selected IDs openly and call the result end-to-end private.
Profile-hijacking defence and the prior v2 failures remain unresolved.

References: https://python-paillier.readthedocs.io/en/stable/ and its security
caveats; PRAG https://aclanthology.org/2024.privatenlp-1.2.pdf for existing private
retrieval. Paillier scoring is existing technology, not claimed research novelty.
