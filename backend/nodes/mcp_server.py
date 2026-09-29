"""A real, standalone MCP node server — one process per source.

Run it directly:
    python -m nodes.mcp_server --data-file data/mcp_nodes/arguana_1.json

`--data-file` points at a JSON file: {"node_id": str, "local_model": str,
"documents": [str, ...]}. Prepared by scripts/prepare_beir_nodes.py from real
BEIR corpora (see docs/06-datasets.md) — this is not toy data.

This process holds the real documents. It exposes exactly two MCP tools:

- `get_profile`: returns this node's published profile: perturbed centroids
  and optional document-derived description/topics/embedding, never raw documents. Called once
  by the coordinator when the node comes online.
- `retrieve`: given a query string, re-embeds it with this node's OWN local
  embedder (which may differ from every other node's) and returns the top-n
  passages from its local index. Only retrieve receives user queries.

Requires Python 3.10+ (the `mcp` package's floor). See README's MCP section
for why this is a separate venv/interpreter from anything on 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `import nodes.*` when run as a script

from nodes.embedding import SHARED_ROUTING_MODEL, HashingEmbedder, shared_routing_embedder  # noqa: E402
from nodes.profile import build_profile, embed_documents  # noqa: E402
from nodes.simulator import InProcessNode  # noqa: E402
from nodes.metadata import attach_metadata  # noqa: E402

# Largest top_n any open retrieve call may ask for (audit, docs/49): a
# retrieve with top_n = 100000 used to return a node's whole public corpus.
MAX_TOP_N = 20


def load_node(data_file: Path) -> tuple[InProcessNode, dict, str]:
    spec = json.loads(data_file.read_text())
    node_id = spec["node_id"]
    local_model = spec.get("local_model") or SHARED_ROUTING_MODEL
    # Node-side de-identification (privacy/deidentify.py, docs/44): runs once,
    # before anything else sees the text, so embeddings, the published
    # profile, the PSI envelopes and every retrieve result are built from the
    # same de-identified documents. `known_identifiers` is the institution's
    # own registry (names/ids); `"deidentify": false` disables it explicitly.
    from privacy.deidentify import Deidentifier  # noqa: E402

    # Role-based access (docs/45): a document is either a string ("public")
    # or {"text": ..., "collection": "clinical_notes"}; alternatively the file
    # may hold {"collections": {"public": [...], "research": [...]}}.
    # `access_policy` maps role -> readable collections and is published.
    raw_documents, collections = [], []
    if "collections" in spec:
        for name, docs in spec["collections"].items():
            raw_documents.extend(docs)
            collections.extend([name] * len(docs))
    for d in spec.get("documents", []):
        raw_documents.append(d["text"] if isinstance(d, dict) else d)
        collections.append(d.get("collection", "public") if isinstance(d, dict) else "public")
    documents = raw_documents
    access_policy = spec.get("access_policy") or {}
    if spec.get("deidentify", True):
        backend = None
        if spec.get("ner") == "presidio":
            from privacy.deidentify import presidio_backend  # noqa: E402

            backend = presidio_backend(spec.get("ner_model", "en_core_web_sm"))
        documents = Deidentifier(known_identifiers=spec.get("known_identifiers", []),
                                 id_patterns=spec.get("id_patterns", []), backend=backend).redact_all(documents)
    profile_k = spec.get("k", 4)
    if type(profile_k) is not int or profile_k < 1:
        raise ValueError("k must be a positive integer")

    # Same factory as the coordinator: ROUTING_EMBEDDER decides the space.
    routing_embedder = shared_routing_embedder()
    local_embedder = (
        routing_embedder if local_model in (SHARED_ROUTING_MODEL, routing_embedder.model_name)
        else HashingEmbedder(model_name=local_model, n_features=256)
    )

    # Profiles must stay reproducible across the fresh process used per call.
    seed = int.from_bytes(hashlib.sha256(node_id.encode()).digest()[:4], "big")
    rng = np.random.default_rng(seed)
    routing_embeddings = embed_documents(documents, routing_embedder)
    local_embeddings = (
        routing_embeddings if local_embedder is routing_embedder else embed_documents(documents, local_embedder)
    )

    # docs/45: with restricted collections, the published profile and topic
    # words describe public documents only.
    from nodes.simulator import public_view  # noqa: E402

    pub_docs, pub_emb = public_view(documents, routing_embeddings, collections)
    profile = build_profile(
        node_id,
        pub_emb,
        k=min(profile_k, len(pub_docs)),
        sigma=0.05,
        rng=rng,
        document_count=len(pub_docs),
        policy_labels=spec.get("policy_labels", []),
    )
    attach_metadata(profile, pub_docs, routing_embedder, enabled=spec.get("publish_metadata", True))
    # v2 integrity (docs/30): this node's persistent Ed25519 key lives next to
    # its data file so every fresh server process signs with the same identity.
    from nodes.signing import load_or_create_key_file, sign_profile  # noqa: E402

    node = InProcessNode(
        node_id, documents, local_embeddings, local_embedder=local_embedder, routing_embeddings=routing_embeddings
    )
    # PSI dispatch (docs/03 target): the OPRF key persists next to the data
    # file so every fresh server process serves the same table; the cluster
    # index is deterministic in `seed`, so centroids and ids match too.
    from nodes.simulator import attach_psi_index  # noqa: E402
    from privacy.psi import random_scalar  # noqa: E402

    psi_keys = _load_or_create_psi_keys(data_file.with_suffix(".psi.key"), sorted(set(collections)), random_scalar)
    attach_psi_index(node, profile, seed=seed, psi_keys=psi_keys, collections=collections,
                     access_policy=access_policy)
    # Authorisation for the PSI step (privacy/credentials.py, docs/43): an
    # allow-list next to the data file gates psi_evaluate per client with a
    # daily evaluation budget. No file = open node (prototype behaviour).
    from privacy.credentials import load_authorizer  # noqa: E402

    node.authorizer = load_authorizer(node_id, data_file.with_suffix(".clients.json"),
                                      state_path=data_file.with_suffix(".usage.sqlite"))
    # Serving policy (docs/49). A gated node (allow-list present) serves only
    # the credentialed private paths — psi/blind — unless its operator opts
    # the unauthenticated text/vector tools back in; otherwise the gate could
    # be walked around. The experimental Paillier scorer (docs/34) is off
    # unless enabled, never on a gated node, and scores public rows only:
    # with chosen plaintexts it returns every scored row's embedding exactly.
    node.open_retrieval = bool(spec.get("open_retrieval", node.authorizer is None))
    node.private_scoring = bool(spec.get("experimental_private_scoring", False)) and node.authorizer is None
    node.signing_key = load_or_create_key_file(data_file.with_suffix(".key"))
    sign_profile(profile, node.signing_key)
    return node, profile.__dict__, local_model


def _load_or_create_psi_keys(path: Path, collections: list[str], generate) -> dict[str, bytes]:
    """One OPRF key per collection, persisted (0600) so every process of this
    node agrees. Backward compatible: a file holding one bare hex key is the
    "public" collection's key."""
    keys: dict[str, bytes] = {}
    if path.exists():
        path.chmod(0o600)   # files written before the 0600 rule stayed world-readable (audit, docs/49)
        text = path.read_text().strip()
        if text.startswith("{"):
            keys = {c: bytes.fromhex(h) for c, h in json.loads(text).items()}
        else:
            keys = {"public": bytes.fromhex(text)}
    changed = False
    for c in collections:
        if c not in keys:
            keys[c] = generate()
            changed = True
    if changed or not path.exists():
        if set(keys) == {"public"}:
            path.write_text(keys["public"].hex())
        else:
            path.write_text(json.dumps({c: k.hex() for c, k in keys.items()}))
        path.chmod(0o600)
    return {c: keys[c] for c in collections}


def _load_or_create_psi_key(path: Path, generate) -> bytes:
    if path.exists():
        return bytes.fromhex(path.read_text().strip())
    key = generate()
    path.write_text(key.hex())
    path.chmod(0o600)  # secret OPRF key: owner-only, same as the signing key
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", required=True, type=Path)
    args = parser.parse_args()

    node, profile_dict, local_model = load_node(args.data_file)
    server = MCPServer(name=f"fedsaferouter-node-{node.source_id}")

    @server.tool()
    def get_profile() -> str:
        """Return centroids and optional document-derived description/topics."""
        serialisable = dict(profile_dict)
        serialisable["centroids"] = np.asarray(serialisable["centroids"]).tolist()
        serialisable["profile_signature"] = serialisable["profile_signature"].hex()
        serialisable["public_key"] = serialisable["public_key"].hex()
        if serialisable.get("cluster_centroids") is not None:
            serialisable["cluster_centroids"] = np.asarray(serialisable["cluster_centroids"]).tolist()
        if serialisable["description_embedding"] is not None:
            serialisable["description_embedding"] = np.asarray(serialisable["description_embedding"]).tolist()
        serialisable["local_model"] = local_model
        return json.dumps(serialisable)

    @server.tool()
    def retrieve(query: str, top_n: int = 5) -> str:
        """Retrieve the top-n locally-held passages for `query` (raw text; legacy/smart modes)."""
        if not node.open_retrieval:
            return json.dumps({"error": "open_retrieval_disabled"})
        passages = node.retrieve_from_text(query, top_n=max(1, min(int(top_n), MAX_TOP_N)))
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    @server.tool()
    def score_encrypted_query(request: dict) -> str:
        """Experimental full-index encrypted scoring; no document fetch."""
        from privacy.encrypted_scoring import score_encrypted

        if not node.private_scoring:
            return json.dumps({"error": "private_scoring_disabled"})
        public = np.array([c == "public" for c in node.collections])
        return json.dumps(score_encrypted(request, node.routing_embeddings[public], SHARED_ROUTING_MODEL))

    @server.tool()
    def retrieve_vector(vector: list[float], top_n: int = 5) -> str:
        """v2 dispatch: retrieve by a shared-routing-space vector, never raw text.

        This node never sees the query string in this mode. It is hardening,
        not secrecy — the vector can still be inverted toward the query.
        """
        if not node.open_retrieval:
            return json.dumps({"error": "open_retrieval_disabled"})
        passages = node.retrieve_vector(np.asarray(vector, dtype=np.float64), top_n=max(1, min(int(top_n), MAX_TOP_N)))
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    @server.tool()
    def psi_evaluate(blinded: list[str], auth: dict | None = None) -> str:
        """PSI dispatch step 1: OPRF-evaluate blinded points (hex). The node
        learns nothing about the query — the points are uniform in the group.
        With an allow-list configured, `auth` (client_id, day, mac) is checked
        and the evaluations charged BEFORE anything touches the OPRF key; a
        refusal returns {"error": reason} and evaluates nothing."""
        from privacy.credentials import Unauthorized, permitted_collections  # noqa: E402

        points = [bytes.fromhex(b) for b in blinded]
        roles: tuple[str, ...] = ()
        if node.authorizer is not None:
            try:
                client_id = node.authorizer.check(auth, points)
            except Unauthorized as exc:
                return json.dumps({"error": exc.reason})
            roles = node.authorizer.roles_of(client_id)
        # Roles come from THIS node's allow-list, never from the request.
        allowed = permitted_collections(node.access_policy, roles, node.psi.collections,
                                        authorised=node.authorizer is not None)
        evaluated = node.psi.evaluate_for(points, allowed)
        return json.dumps({"collections": allowed, "epoch": node.psi.epoch,
                           "evaluations": [{c: e.hex() for c, e in per.items()} for per in evaluated]})

    @server.tool()
    def psi_table(auth: dict | None = None) -> str:
        """Blind unlock, offline step (docs/47): this node's whole encrypted
        cluster table, keyed by OPRF-derived tags, envelopes padded to one
        length. Public collection for anyone; restricted collections only
        for a credential whose roles may read them (their size is not shown
        to anyone else). Same bytes for every caller of the same role, and
        charges no evaluations. Base64 on the wire."""
        import base64

        from privacy.credentials import Unauthorized, permitted_collections  # noqa: E402

        roles: tuple[str, ...] = ()
        if node.authorizer is not None and auth is not None:
            try:
                roles = node.authorizer.roles_of(node.authorizer.check(auth, []))
            except Unauthorized as exc:
                return json.dumps({"error": exc.reason})
        allowed = permitted_collections(node.access_policy, roles, node.psi.collections,
                                        authorised=node.authorizer is not None and auth is not None)
        table = node.psi.blind_table(allowed)
        return json.dumps({"node_id": table["node_id"], "epoch": table["epoch"], "version": table["version"],
                           "entries": {t.hex(): base64.b64encode(e).decode("ascii")
                                       for t, e in table["entries"].items()}})

    @server.tool()
    def get_restricted_centroids(auth: dict | None = None) -> str:
        """Role-scoped profile (docs/45): centroids of restricted clusters the
        caller's roles may read, signed with this node's profile key. Open
        node or unauthorised caller: none. Charges no evaluations."""
        from privacy.credentials import Unauthorized, permitted_collections  # noqa: E402
        from nodes.signing import sign_payload  # noqa: E402

        if node.authorizer is None:
            return json.dumps({"clusters": [], "signature": None})
        try:
            client_id = node.authorizer.check(auth, [])
        except Unauthorized as exc:
            return json.dumps({"error": exc.reason})
        allowed = permitted_collections(node.access_policy, node.authorizer.roles_of(client_id),
                                        node.psi.collections, authorised=True)
        payload = {"node_id": node.source_id, "client_id": client_id, "day": auth.get("day"),
                   "clusters": node.restricted_centroids([c for c in allowed if c != "public"])}
        return json.dumps({**payload, "signature": sign_payload(node.signing_key, payload)})

    @server.tool()
    def psi_envelopes(fetch_set: list[int] | None = None) -> str:
        """PSI dispatch step 2: encrypted envelopes for an anonymity set of
        cluster ids (None = all). The node learns the set, never the match;
        only envelopes the client holds the OPRF output for will open."""
        envelopes = node.psi.envelopes_for(fetch_set)
        return json.dumps({token: env.hex() for token, env in envelopes.items()})

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
