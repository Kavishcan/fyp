"""How a device talks to one node, whatever the node is (docs/52).

A node is reached through four calls — profile, blind table, OPRF
evaluation, restricted centroids — and nothing else: the device never sends
a node the question, a vector or a cluster id. `MCPTransport` wraps a real
MCP node process; `LocalTransport` wraps an in-process node (tests and the
simulated federation) and applies the same gate the MCP server applies.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from baselines.base import SourceProfile


def profile_from_dict(data: dict) -> SourceProfile:
    """A node's published profile as it arrives over the wire."""
    return SourceProfile(
        source_id=data["source_id"],
        centroids=np.asarray(data["centroids"], dtype=np.float64),
        trust_mean=data.get("trust_mean", 0.5),
        trust_observations=data.get("trust_observations", 0),
        document_count_bucket=data.get("document_count_bucket", "unknown"),
        policy_labels=data.get("policy_labels", []),
        expected_latency_ms=data.get("expected_latency_ms", 0.0),
        profile_version=data.get("profile_version", 1),
        profile_signature=bytes.fromhex(data.get("profile_signature", "")),
        public_key=bytes.fromhex(data.get("public_key", "")),
        description=data.get("description", ""),
        topics=data.get("topics", []),
        description_embedding=(np.asarray(data["description_embedding"], dtype=np.float64)
                               if data.get("description_embedding") is not None else None),
        metadata_method=data.get("metadata_method", ""),
        metadata_embedding_model=data.get("metadata_embedding_model", ""),
        cluster_centroids=(np.asarray(data["cluster_centroids"], dtype=np.float64)
                           if data.get("cluster_centroids") is not None else None),
        cluster_collections=data.get("cluster_collections"),
        access_policy=data.get("access_policy"),
    )


class NodeTransport(Protocol):
    node_id: str

    def profile(self) -> SourceProfile: ...

    def table(self, auth: dict | None) -> dict: ...

    def evaluate(self, points: list[bytes], auth: dict | None) -> tuple[list[dict[str, bytes]], str | None]: ...

    def restricted(self, auth: dict | None) -> dict: ...


class MCPTransport:
    """A real MCP node (spawn-per-call or persistent handle)."""

    def __init__(self, handle) -> None:
        self.handle = handle
        self.node_id = handle.node_id

    def profile(self) -> SourceProfile:
        return profile_from_dict(self.handle.get_profile())

    def table(self, auth: dict | None) -> dict:
        return self.handle.psi_table(auth)

    def evaluate(self, points, auth):
        return self.handle.psi_evaluate_epoch(points, auth)

    def restricted(self, auth: dict | None) -> dict:
        return self.handle.get_restricted_centroids(auth)


class LocalTransport:
    """An in-process node, gated exactly as nodes/mcp_server gates a real one:
    roles come from the node's own allow-list, never from the request."""

    def __init__(self, node, profile: SourceProfile | None = None) -> None:
        self.node = node
        self.node_id = node.source_id
        self._profile = profile

    def profile(self) -> SourceProfile:
        if self._profile is None:
            raise ValueError(f"in-process node {self.node_id!r} needs its profile passed in")
        return self._profile

    def _roles(self, auth: dict | None, points: list[bytes]) -> tuple[tuple[str, ...], bool]:
        from privacy.credentials import Unauthorized

        if self.node.authorizer is None:
            return (), False
        try:
            return self.node.authorizer.roles_of(self.node.authorizer.check(auth, points)), True
        except Unauthorized as exc:
            raise PermissionError(f"node {self.node_id!r} refused: {exc.reason}") from exc

    def table(self, auth: dict | None) -> dict:
        from privacy.credentials import permitted_collections

        roles, authorised = self._roles(auth, []) if auth is not None else ((), False)
        return self.node.psi.blind_table(permitted_collections(self.node.access_policy, roles,
                                                               self.node.psi.collections, authorised=authorised))

    def evaluate(self, points, auth):
        from privacy.credentials import permitted_collections

        roles, _ = self._roles(auth, points)
        allowed = permitted_collections(self.node.access_policy, roles, self.node.psi.collections,
                                        authorised=self.node.authorizer is not None)
        return self.node.psi.evaluate_for(points, allowed), self.node.psi.epoch

    def restricted(self, auth: dict | None) -> dict:
        from privacy.credentials import permitted_collections

        if self.node.authorizer is None:
            return {"clusters": [], "signature": None}
        roles, _ = self._roles(auth, [])
        allowed = permitted_collections(self.node.access_policy, roles, self.node.psi.collections, authorised=True)
        payload = {"node_id": self.node_id, "client_id": (auth or {}).get("client_id"), "day": (auth or {}).get("day"),
                   "clusters": self.node.restricted_centroids([c for c in allowed if c != "public"])}
        signature = None
        if getattr(self.node, "signing_key", None) is not None:
            from nodes.signing import sign_payload

            signature = sign_payload(self.node.signing_key, payload)
        return {**payload, "signature": signature}
