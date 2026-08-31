"""FastAPI app implementing the API surface from docs/08-deployment.md.

Run locally with:
    uvicorn api.app:app --reload --app-dir src

Development server for a future React/Next.js frontend. Single in-memory
AppState (src/api/state.py) — not a deployment target, and nodes are
registered by submitting documents directly (simulated mode) rather than by a
separately-running MCP node self-publishing its profile, since MCP transport
is not wired up yet (see src/nodes/server.py and the Status section in the
project README).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    AuditResponse,
    NodeRegisterRequest,
    NodeRegisterResponse,
    NodeStatus,
    QueryRequest,
    QueryResponse,
)
from .state import AppState

app = FastAPI(title="FedSafeRouter API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

state = AppState()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "nodes_registered": len(state.registry)}


@app.post("/nodes/register", response_model=NodeRegisterResponse)
def register_node(req: NodeRegisterRequest) -> NodeRegisterResponse:
    profile = state.register_node(
        req.node_id, req.documents, policy_labels=req.policy_labels, k=req.k, sigma=req.sigma
    )
    return NodeRegisterResponse(
        node_id=profile.source_id,
        document_count_bucket=profile.document_count_bucket,
        profile_version=profile.profile_version,
        centroid_count=len(profile.centroids),
    )


@app.get("/nodes", response_model=list[NodeStatus])
def list_nodes() -> list[NodeStatus]:
    return [NodeStatus(**s) for s in state.node_status()]


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    result = state.run_query(
        req.question, max_nodes=req.max_nodes, genuine_k=req.genuine_k, sigma=req.sigma
    )
    return QueryResponse(**result)


@app.get("/audit/{query_id}", response_model=AuditResponse)
def audit(query_id: str) -> AuditResponse:
    record = state.audit(query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return AuditResponse(
        query_id=record["query_id"],
        topic_key=record["topic_key"],
        coarse_candidate_ids=record["coarse_candidate_ids"],
        genuine_source_ids=record["genuine_source_ids"],
        dispatched_source_ids=record["dispatched_source_ids"],
        decoy_source_ids=record["decoy_source_ids"],
    )
