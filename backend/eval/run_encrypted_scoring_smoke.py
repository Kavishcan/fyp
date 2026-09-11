"""Small synthetic correctness/cost measurement, not an attack benchmark."""
import argparse
import json
from pathlib import Path
import tempfile
import time

import numpy as np

from nodes.embedding import HashingEmbedder, SHARED_ROUTING_MODEL
from nodes.mcp_client import MCPNodeHandle
from nodes.profile import embed_documents
from privacy.encrypted_scoring import CoordinatorSession, KEY_BITS, SCALE, quantize


def run(output):
    if output.exists():
        raise ValueError("refusing to overwrite a result")
    documents = ["tumour chemo protocol", "tax filing invoice", "cardiac response"]
    queries = ["tumour chemo", "tax invoice", "cardiac response"]
    embedder = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256)
    vectors = embed_documents(documents, embedder)
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "node.json"
        path.write_text(json.dumps(dict(node_id="smoke",documents=documents)))
        node = MCPNodeHandle("smoke",path)
        for question in queries:
            start = time.perf_counter()
            q = embedder.embed([question])[0]
            session = CoordinatorSession(q, SHARED_ROUTING_MODEL)
            request = session.request()
            encrypted_at = time.perf_counter()
            response = node.score_encrypted_query(request)
            received_at = time.perf_counter()
            decoded = session.decode(response)
            scores = np.array([r["score"] for r in decoded])
            fixed = quantize(vectors) @ quantize(q) / SCALE**2
            float_scores = vectors @ q / np.where(np.linalg.norm(vectors,axis=1)==0,1,np.linalg.norm(vectors,axis=1)) / (np.linalg.norm(q) or 1.)
            rows.append(dict(query_number=len(rows)+1, fixed_point_error=float(np.max(np.abs(scores-fixed))),
                float_cosine_error=float(np.max(np.abs(scores-float_scores))),
                top1_matches_cosine=bool(np.argmax(scores)==np.argmax(float_scores)),
                keygen_embed_encrypt_ms=(encrypted_at-start)*1000,
                mcp_roundtrip_ms=(received_at-encrypted_at)*1000,
                total_ms=(time.perf_counter()-start)*1000,
                request_bytes=len(json.dumps(request).encode()),response_bytes=len(json.dumps(response).encode())))
    report = dict(setting="synthetic 3 documents, 3 queries, 1 real MCP process per call",
                  key_bits=KEY_BITS, dimensions=256, scale=SCALE, rows=rows,
                  security_proof=False, attack_evaluation_performed=False,
                  fetch_performed=False, generation_performed=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)
