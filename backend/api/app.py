"""FastAPI app implementing the API surface from docs/08-deployment.md.

Run locally with:
    uvicorn api.app:app --reload --app-dir backend

Development server for the Next.js frontend. Single in-memory AppState
(backend/api/state.py) — not a deployment target. Two kinds of nodes coexist
in the same registry: simulated (documents posted directly to this process)
and MCP-backed (real, separate server processes — see
backend/nodes/mcp_server.py, backend/nodes/mcp_client.py). On startup this
app auto-registers every prepared real-data node in data/mcp_nodes/ (see
data/prepare_beir_nodes.py); if that directory doesn't exist yet, it just
starts with zero MCP nodes rather than failing.

Loads backend/.env if present (OPENAI_API_KEY / GEMINI_API_KEY / LLM_PROVIDER
— see backend/generation/factory.py and README's Generation section).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .schemas import (
    ActivateNodeRequest,
    AuditResponse,
    AvailableMCPNode,
    NodeRegisterRequest,
    NodeRegisterResponse,
    NodeStatus,
    QueryRequest,
    QueryResponse,
)
from .state import AppState

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MCP_NODES_DIR = DATA_DIR / "mcp_nodes"
EXTRA_MCP_NODES_DIR = DATA_DIR / "mcp_nodes_extra"

state = AppState()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    loaded = await state.load_mcp_nodes_from_dir(MCP_NODES_DIR)
    if loaded:
        print(f"[startup] registered {len(loaded)} MCP node(s) from {MCP_NODES_DIR}: {loaded}")
    else:
        print(f"[startup] no MCP nodes found in {MCP_NODES_DIR} (run data/prepare_beir_nodes.py first)")
    yield


app = FastAPI(title="FedSafeRouter API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "nodes_registered": len(state.registry)}


@app.post("/nodes/register", response_model=NodeRegisterResponse)
def register_node(req: NodeRegisterRequest) -> NodeRegisterResponse:
    profile = state.register_node(
        req.node_id,
        req.documents,
        policy_labels=req.policy_labels,
        k=req.k,
        sigma=req.sigma,
        local_model=req.local_model,
    )
    return NodeRegisterResponse(
        node_id=profile.source_id,
        document_count_bucket=profile.document_count_bucket,
        profile_version=profile.profile_version,
        centroid_count=len(profile.centroids),
        local_model=state.node_local_models[profile.source_id],
    )


@app.get("/nodes", response_model=list[NodeStatus])
def list_nodes() -> list[NodeStatus]:
    return [NodeStatus(**s) for s in state.node_status()]


@app.get("/nodes/available", response_model=list[AvailableMCPNode])
def list_available_nodes() -> list[AvailableMCPNode]:
    """Real MCP node servers prepared by data/prepare_beir_nodes.py but not
    auto-loaded at startup — turn one on with POST /nodes/activate.
    """
    return [AvailableMCPNode(**n) for n in state.list_available_mcp_nodes(EXTRA_MCP_NODES_DIR)]


@app.post("/nodes/activate", response_model=NodeRegisterResponse)
async def activate_node(req: ActivateNodeRequest) -> NodeRegisterResponse:
    data_file = EXTRA_MCP_NODES_DIR / f"{req.node_id}.json"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail="node_id not found among available MCP nodes")
    profile = await state.register_mcp_node_async(data_file)
    return NodeRegisterResponse(
        node_id=profile.source_id,
        document_count_bucket=profile.document_count_bucket,
        profile_version=profile.profile_version,
        centroid_count=len(profile.centroids),
        local_model=state.node_local_models[profile.source_id],
    )


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
