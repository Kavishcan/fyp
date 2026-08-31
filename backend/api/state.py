"""In-memory application state for the API layer.

Single-process, in-memory, no persistence — this is a research demo backing a
frontend, not a deployment target. Real deployment would need the MCP
transport (src/nodes/server.py) talking to actually-separate node processes,
not documents held in this process's memory.
"""
from __future__ import annotations

import uuid

import numpy as np

from baselines.cosine_router import CosineRouter, aggregate_scores
from eval.instrument import Instrumentation, QueryLog
from nodes.simulator import InProcessNode, build_simulated_source
from router.exposure import ExposureFactors
from router.pipeline import PrivacyAwarePipeline, RerankFeatures, RerankWeights
from router.registry import SourceRegistry
from router.trust import BoundedTrustUpdate

from .embedder import HashingEmbedder
from .topic import assign_topic_key


class AppState:
    def __init__(self, instrumentation_path: str = "experiments/runs/api_queries.jsonl") -> None:
        self.registry = SourceRegistry()
        self.nodes: dict[str, InProcessNode] = {}
        self.embedder = HashingEmbedder(n_features=256)
        self.trust_update = BoundedTrustUpdate(alpha=0.3, decoy_aware=False)
        self.instrumentation = Instrumentation(instrumentation_path)
        self._rng = np.random.default_rng()

    def register_node(self, node_id: str, documents: list[str], *, policy_labels, k: int, sigma: float):
        node, profile = build_simulated_source(
            node_id, documents, self.embedder, k=k, sigma=sigma, rng=self._rng, policy_labels=policy_labels
        )
        # Re-publishing an existing node bumps profile_version so the
        # registry's stale-version rejection (router/registry.py) doesn't fire.
        existing = self.registry.get(node_id)
        if existing is not None:
            profile.profile_version = existing.profile_version + 1
        self.nodes[node_id] = node
        self.registry.publish(profile)
        return profile

    def node_status(self) -> list[dict]:
        statuses = []
        for profile in self.registry.all_profiles():
            trust = self.trust_update.get(profile.source_id, default=profile.trust_mean)
            statuses.append(
                {
                    "node_id": profile.source_id,
                    "trust": trust,
                    "trust_observations": profile.trust_observations,
                    "document_count_bucket": profile.document_count_bucket,
                    "profile_version": profile.profile_version,
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

        query_embedding = self.embedder.embed([question])[0]
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
            for passage in node.retrieve(query_embedding, top_n=1):
                citations.append({"node_id": node_id, "document": passage.document, "score": passage.score})

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

        return {
            "query_id": query_id,
            "answer": None,
            "citations": citations,
            "nodes_contacted": result.dispatched_source_ids,
            "generation_status": "not_implemented",
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
