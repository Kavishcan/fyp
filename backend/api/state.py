"""In-memory application state for the API layer.

Single-process, in-memory, no persistence — this is a research demo backing a
frontend, not a deployment target. Nodes come in two flavours, side by side in
the same registry/pipeline:

- Simulated (register_node): documents held in this process's memory.
- MCP-backed (register_mcp_node / load_mcp_nodes_from_dir): genuinely separate
  OS processes (nodes/mcp_server.py) holding real documents, reached over the
  actual MCP protocol via nodes/mcp_client.py. The coordinator never sees
  their documents — it fetches a profile once and retrieves passages by query,
  same as a real deployment would.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np

from baselines.base import SourceProfile
from baselines.cosine_router import CosineRouter, aggregate_scores
from eval.instrument import Instrumentation, QueryLog
from generation import get_generator
from nodes.mcp_client import MCPNodeHandle
from nodes.simulator import InProcessNode, build_simulated_source
from router.exposure import ExposureFactors
from router.pipeline import PrivacyAwarePipeline, RerankFeatures, RerankWeights
from router.registry import SourceRegistry
from router.trust import BoundedTrustUpdate

from .embedder import SHARED_ROUTING_MODEL, HashingEmbedder
from .topic import assign_topic_key


def _profile_from_dict(data: dict) -> SourceProfile:
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
    )


class AppState:
    def __init__(self, instrumentation_path: str = "experiments/runs/api_queries.jsonl") -> None:
        self.registry = SourceRegistry()
        self.nodes: dict[str, InProcessNode | MCPNodeHandle] = {}
        self.node_local_models: dict[str, str] = {}
        # ONE shared embedder for every profile and every routing-time query —
        # this is what keeps max-over-centroid scoring valid regardless of how
        # many distinct local_model names nodes register with (see
        # backend/nodes/simulator.py module docstring).
        self.routing_embedder = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256)
        self.trust_update = BoundedTrustUpdate(alpha=0.3, decoy_aware=False)
        self.instrumentation = Instrumentation(instrumentation_path)
        self._rng = np.random.default_rng()
        # Demo-only, external-API generation — see backend/generation/base.py
        # docstring for why this is NOT the research pipeline's design.
        self.generator = get_generator()

    def register_node(
        self,
        node_id: str,
        documents: list[str],
        *,
        policy_labels,
        k: int,
        sigma: float,
        local_model: str | None = None,
    ):
        """`local_model` names this node's own embedding model for local
        retrieval (any string — see HashingEmbedder docstring for why a
        distinct name is enough to simulate a genuinely different, mutually
        incomparable space). Omit it to use the shared routing embedder for
        this node too, i.e. no heterogeneity.
        """
        local_embedder = (
            HashingEmbedder(model_name=local_model, n_features=256) if local_model else self.routing_embedder
        )
        node, profile = build_simulated_source(
            node_id,
            documents,
            self.routing_embedder,
            local_embedder,
            k=k,
            sigma=sigma,
            rng=self._rng,
            policy_labels=policy_labels,
        )
        self._publish(node_id, node, profile, local_model or SHARED_ROUTING_MODEL)
        return profile

    async def register_mcp_node_async(self, data_file: Path) -> SourceProfile:
        """Registers a node backed by a real, separate MCP server process.

        Fetches the profile via the `get_profile` MCP tool — the coordinator
        never reads `data_file` itself and never sees the node's documents,
        only what the node chooses to publish. Async because this is called
        from FastAPI's lifespan startup, which already runs on an event loop
        — `asyncio.run()` (used by MCPNodeHandle's sync wrappers) cannot
        nest inside one, so this calls the `_async` methods directly instead.
        """
        node_id = Path(data_file).stem
        handle = MCPNodeHandle(node_id=node_id, data_file=Path(data_file))
        profile_data = await handle.get_profile_async()
        profile = _profile_from_dict(profile_data)
        local_model = profile_data.get("local_model") or SHARED_ROUTING_MODEL
        self._publish(profile.source_id, handle, profile, local_model)
        return profile

    async def load_mcp_nodes_from_dir(self, directory: str | Path) -> list[str]:
        """Registers every `*.json` node spec in `directory`. Missing
        directory or individual bad files are skipped, not fatal — this runs
        at startup and a demo with zero MCP nodes should still boot.
        """
        directory = Path(directory)
        loaded = []
        if not directory.is_dir():
            return loaded
        for data_file in sorted(directory.glob("*.json")):
            try:
                profile = await self.register_mcp_node_async(data_file)
                loaded.append(profile.source_id)
            except Exception as exc:  # noqa: BLE001 - startup must not crash the app
                print(f"[startup] skipping MCP node {data_file}: {exc}")
        return loaded

    def list_available_mcp_nodes(self, directory: str | Path) -> list[dict]:
        """Node specs in `directory` not yet registered — cheap (reads the
        JSON file directly, no subprocess spawned) so the frontend can list
        "servers you could turn on" without paying the MCP round-trip cost
        until the user actually activates one.
        """
        directory = Path(directory)
        available = []
        if not directory.is_dir():
            return available
        for data_file in sorted(directory.glob("*.json")):
            node_id = data_file.stem
            if node_id in self.nodes:
                continue
            try:
                spec = json.loads(data_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            available.append(
                {
                    "node_id": node_id,
                    "local_model": spec.get("local_model") or SHARED_ROUTING_MODEL,
                    "document_count": len(spec.get("documents", [])),
                }
            )
        return available

    def _publish(self, node_id: str, node, profile: SourceProfile, local_model: str) -> None:
        # Re-publishing an existing node bumps profile_version so the
        # registry's stale-version rejection (router/registry.py) doesn't fire.
        existing = self.registry.get(node_id)
        if existing is not None:
            profile.profile_version = existing.profile_version + 1
        self.nodes[node_id] = node
        self.node_local_models[node_id] = local_model
        self.registry.publish(profile)

    def node_status(self) -> list[dict]:
        statuses = []
        for profile in self.registry.all_profiles():
            trust = self.trust_update.get(profile.source_id, default=profile.trust_mean)
            node = self.nodes.get(profile.source_id)
            statuses.append(
                {
                    "node_id": profile.source_id,
                    "trust": trust,
                    "trust_observations": profile.trust_observations,
                    "document_count_bucket": profile.document_count_bucket,
                    "profile_version": profile.profile_version,
                    "local_model": self.node_local_models.get(profile.source_id, SHARED_ROUTING_MODEL),
                    "transport": "mcp" if isinstance(node, MCPNodeHandle) else "simulated",
                }
            )
        return statuses

    def run_query(self, question: str, *, max_nodes: int, genuine_k: int, sigma: float) -> dict:
        profiles = self.registry.all_profiles()
        query_id = str(uuid.uuid4())
        if not profiles:
            self.instrumentation.record(QueryLog(query_id=query_id, topic_key="no-sources"))
            return {
                "query_id": query_id,
                "answer": None,
                "citations": [],
                "nodes_contacted": [],
                "generation_status": "no_sources_registered",
            }

        query_embedding = self.routing_embedder.embed([question])[0]
        topic_key = assign_topic_key(query_embedding, profiles)

        baseline = CosineRouter(aggregation="max")
        baseline.register_sources(profiles)
        pipeline = PrivacyAwarePipeline(baseline, RerankWeights())

        def feature_provider(candidate_ids):
            zero_exposure = ExposureFactors(0.0, 0.0, 0.0, 0.0)  # not yet measured, see docs/04
            features = {}
            for cid in candidate_ids:
                profile = self.registry.get(cid)
                centroids = np.asarray(profile.centroids, dtype=np.float64)
                relevance = aggregate_scores(
                    self._centroid_scores(centroids, query_embedding), "max"
                )
                features[cid] = RerankFeatures(
                    relevance=relevance,
                    trust=self.trust_update.get(cid, default=profile.trust_mean),
                    authorized=True,
                    exposure_factors=zero_exposure,
                    communication_cost=0.0,
                    expected_latency=0.0,
                    hijack_risk=0.0,
                )
            return features

        result = pipeline.route(
            query_embedding,
            coarse_k=min(max_nodes * 3, len(profiles)) or 1,
            top_k=genuine_k,
            m=min(max_nodes, len(profiles)),
            topic_key=topic_key,
            feature_provider=feature_provider,
            sigma=sigma,
            rng=self._rng,
        )

        citations = []
        for node_id in result.dispatched_source_ids:
            node = self.nodes.get(node_id)
            if node is None:
                continue
            if isinstance(node, MCPNodeHandle):
                # Genuine MCP round trip to a separate process — always
                # re-embeds the raw question in that node's own local space,
                # inside that process, which the coordinator never sees.
                raw_passages = node.retrieve_from_text(question, top_n=1)
                passages = [(p["document"], p["score"]) for p in raw_passages]
            elif node.local_embedder is self.routing_embedder:
                # Same model object as routing — query_embedding is already
                # the correct vector for this node's space, so reuse it
                # instead of re-embedding identical text for no reason.
                passages = [(p.document, p.score) for p in node.retrieve(query_embedding, top_n=1)]
            else:
                # Genuinely different model: must re-embed the raw question
                # in THIS node's own space. See
                # nodes/simulator.py::InProcessNode.retrieve_from_text.
                passages = [(p.document, p.score) for p in node.retrieve_from_text(question, top_n=1)]
            for document, score in passages:
                citations.append({"node_id": node_id, "document": document, "score": score})

        signals = {node_id: self._evidence_relevance(node_id, citations) for node_id in result.dispatched_source_ids}
        self.trust_update.update(signals, decoy_ids=frozenset(result.decoy_source_ids))

        self.instrumentation.record(
            QueryLog(
                query_id=query_id,
                topic_key=topic_key,
                coarse_candidate_ids=result.coarse_candidate_ids,
                genuine_source_ids=result.genuine_source_ids,
                dispatched_source_ids=result.dispatched_source_ids,
            )
        )

        answer = None
        generation_status = "not_implemented"
        if self.generator is not None:
            try:
                answer = self.generator.generate(question, [c["document"] for c in citations])
                generation_status = self.generator.name
            except Exception as exc:  # surfaced to the caller, not swallowed
                generation_status = f"error:{type(exc).__name__}"

        return {
            "query_id": query_id,
            "answer": answer,
            "citations": citations,
            "nodes_contacted": result.dispatched_source_ids,
            "generation_status": generation_status,
        }

    def audit(self, query_id: str) -> dict | None:
        for record in self.instrumentation.read_all():
            if record["query_id"] == query_id:
                genuine = set(record.get("genuine_source_ids", []))
                dispatched = record.get("dispatched_source_ids", [])
                record["decoy_source_ids"] = [s for s in dispatched if s not in genuine]
                return record
        return None

    @staticmethod
    def _centroid_scores(centroids: np.ndarray, query_embedding: np.ndarray) -> np.ndarray:
        q = np.asarray(query_embedding, dtype=np.float64)
        q_norm = np.linalg.norm(q) or 1.0
        norms = np.linalg.norm(centroids, axis=1)
        norms = np.where(norms == 0, 1.0, norms)
        return (centroids @ q) / (norms * q_norm)

    @staticmethod
    def _evidence_relevance(node_id: str, citations: list[dict]) -> float:
        scores = [c["score"] for c in citations if c["node_id"] == node_id]
        return max(scores) if scores else 0.0
