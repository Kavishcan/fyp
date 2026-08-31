"""Pydantic request/response models for the API surface in docs/08-deployment.md."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class NodeRegisterRequest(BaseModel):
    node_id: str
    documents: List[str] = Field(min_length=1)
    policy_labels: List[str] = []
    k: int = 1
    sigma: float = 0.0
    mcp_endpoint: Optional[str] = None  # reserved for real deployment; unused in simulated mode


class NodeRegisterResponse(BaseModel):
    node_id: str
    document_count_bucket: str
    profile_version: int
    centroid_count: int
    note: str = "simulated mode: profile computed server-side from submitted documents"


class NodeStatus(BaseModel):
    node_id: str
    trust: float
    trust_observations: int
    document_count_bucket: str
    profile_version: int


class QueryRequest(BaseModel):
    question: str
    max_nodes: int = 5  # m: total dispatched, genuine + decoys
    genuine_k: int = 2  # k: genuine relevant sources selected before decoys
    sigma: float = 0.0  # empirical query perturbation magnitude; 0 = baseline


class Citation(BaseModel):
    node_id: str
    document: str
    score: float


class QueryResponse(BaseModel):
    query_id: str
    answer: Optional[str]
    citations: List[Citation]
    nodes_contacted: List[str]
    generation_status: str = "not_implemented"


class AuditResponse(BaseModel):
    query_id: str
    topic_key: str
    coarse_candidate_ids: List[str]
    genuine_source_ids: List[str]
    dispatched_source_ids: List[str]
    decoy_source_ids: List[str]
