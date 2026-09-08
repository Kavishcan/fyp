"""Pydantic request/response models for the API surface in docs/08-deployment.md."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class NodeRegisterRequest(BaseModel):
    node_id: str
    documents: List[str] = Field(min_length=1)
    policy_labels: List[str] = []
    k: int = 1
    sigma: float = 0.0
    local_model: Optional[str] = None  # any name; omit to share the routing embedder (see backend/api/embedder.py)
    mcp_endpoint: Optional[str] = None  # reserved for real deployment; unused in simulated mode
    publish_metadata: bool = True


class NodeRegisterResponse(BaseModel):
    node_id: str
    document_count_bucket: str
    profile_version: int
    centroid_count: int
    local_model: str
    note: str = "simulated mode: profile computed server-side from submitted documents"


class AvailableMCPNode(BaseModel):
    node_id: str
    local_model: str
    document_count: int


class ActivateNodeRequest(BaseModel):
    node_id: str


class NodeStatus(BaseModel):
    node_id: str
    trust: float
    trust_observations: int
    document_count_bucket: str
    profile_version: int
    local_model: str
    transport: str  # "mcp" (real, separate process) or "simulated" (in-process)
    description: str = ""
    topics: List[str] = Field(default_factory=list)
    metadata_method: str = ""


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    max_nodes: int = Field(default=5, ge=0)  # hard fan-out cap in smart mode
    genuine_k: int = Field(default=2, ge=0)  # legacy mode only
    sigma: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    routing_mode: Literal["legacy", "smart"] = "legacy"
    exposure_budget: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    minimum_gain: float = Field(default=0.05, ge=0, le=1, allow_inf_nan=False)
    minimum_trust: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    aggregation: Literal["mean", "max"] = "mean"
    relevance_mode: Literal["centroid", "description", "combined"] = "centroid"
    description_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    selection_policy: Literal["overlap", "relative"] = "overlap"
    relative_score_floor: float = Field(default=0.8, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_mode(self):
        if self.routing_mode == "legacy" and self.selection_policy != "overlap":
            raise ValueError("relative selection requires smart mode")
        if self.routing_mode == "smart" and self.sigma != 0:
            raise ValueError("smart mode does not apply embedding perturbation")
        if self.routing_mode == "legacy" and self.exposure_budget is not None:
            raise ValueError("strict exposure_budget requires smart mode")
        if self.routing_mode == "legacy" and self.relevance_mode != "centroid":
            raise ValueError("metadata relevance requires smart mode")
        return self


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
    routing_details: Optional[dict] = None


class AuditResponse(BaseModel):
    query_id: str
    topic_key: str
    coarse_candidate_ids: List[str]
    genuine_source_ids: List[str]
    dispatched_source_ids: List[str]
    decoy_source_ids: List[str]
    routing_details: Optional[dict] = None
