"""Isolated, opt-in encrypted scoring endpoint. No fetch, generation or audit log."""
import json
import time
import uuid

from pydantic import BaseModel, Field, model_validator

from nodes.mcp_client import MCPNodeHandle
from router.v2 import V2Config, select_dispatch
from .topic import assign_topic_key


class PrivateScoreRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    max_sources: int = Field(default=3, ge=0, le=6, strict=True)
    genuine_k: int = Field(default=1, ge=0, le=6, strict=True)
    exposure_budget: float = Field(default=3, ge=0, le=6, allow_inf_nan=False)
    final_k: int = Field(default=5, ge=0, le=20, strict=True)

    @model_validator(mode="after")
    def validate_budget(self):
        if self.genuine_k > self.max_sources:
            raise ValueError("genuine_k exceeds contact cap")
        return self


def run_private_scoring(state, req):
    from privacy.encrypted_scoring import CoordinatorSession, score_encrypted

    started = time.perf_counter()
    q = state.routing_embedder.embed([req.question])[0]
    profiles = [p for p in state.registry.all_profiles()
                if set(p.policy_labels).issubset(state.allowed_policy_labels)]
    decision = select_dispatch(q, profiles, trust={},
        per_source_cost=state.source_exposure_costs,
        topic_key=assign_topic_key(q, profiles),
        config=V2Config(max_sources=req.max_sources, genuine_k=req.genuine_k,
                        exposure_budget=req.exposure_budget, coarse_k=15))
    # Selection is coordinator-local. Scores and rankings never go back to sources.
    model = state.routing_embedder.model_name
    session = CoordinatorSession(q, model) if decision.dispatched_source_ids else None
    ranks, errors, costs = [], {}, {}
    for sid in decision.dispatched_source_ids:
        tick = time.perf_counter()
        request_bytes = response_bytes = 0
        try:
            request = session.request()
            request_bytes = len(json.dumps(request).encode())
            node = state.nodes[sid]
            if isinstance(node, MCPNodeHandle):
                response = node.score_encrypted_query(request)
            else:
                response = score_encrypted(request, node.routing_embeddings, model)
            response_bytes = len(json.dumps(response).encode())
            ranks.extend(dict(node_id=sid, **r) for r in session.decode(response))
        except Exception as exc:
            errors[sid] = type(exc).__name__
        costs[sid] = dict(request_bytes=request_bytes, response_bytes=response_bytes,
                          milliseconds=(time.perf_counter()-tick)*1000)
    ranks.sort(key=lambda r: (-r["score"], r["node_id"], r["index"]))
    return dict(query_id=str(uuid.uuid4()), status="encrypted_scoring_only",
                ranked_documents=ranks[:req.final_k], nodes_contacted=decision.dispatched_source_ids,
                exposure_spent=decision.exposure_spent, errors=errors, transport_costs=costs,
                elapsed_ms=(time.perf_counter()-started)*1000,
                fetch_performed=False, generation_performed=False,
                end_to_end_query_privacy=False,
                residual_leakage=["source contacts", "timing", "index size", "query dimension", "public profiles"],
                trust_boundary="coordinator trusted; source scoring honest-but-curious")
