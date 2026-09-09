"""Opt-in evidence allocation endpoint adapter, separate from privacy routing."""
from __future__ import annotations

import hashlib
import uuid

import numpy as np

from eval.instrument import QueryLog
from nodes.mcp_client import MCPNodeHandle
from router.evidence_budget import AllocationConfig, Candidate, allocate, unit_rows


def run_evidence_query(state, question, config: AllocationConfig):
    query_id = str(uuid.uuid4())
    query = state.routing_embedder.embed([question])[0]
    profiles = [p for p in state.registry.all_profiles()
                if set(p.policy_labels).issubset(state.allowed_policy_labels)]

    def retrieve(sid, offset):
        node = state.nodes[sid]
        if isinstance(node, MCPNodeHandle):
            page = node.retrieve_from_text(question, top_n=1, offset=offset)
            if len(page) > 1:
                raise ValueError("node exceeded requested page size")
            text = page[0]["document"] if page else None
        else:
            page = node.retrieve_from_text(question, top_n=1, offset=offset)
            text = page[0].document if page else None
        if text is None:
            return None
        document_id = hashlib.sha256(" ".join(text.split()).encode()).hexdigest()
        return Candidate(sid, document_id, text, state.routing_embedder.embed([text])[0])

    result = allocate(query, profiles, retrieve, config, question=question)
    details = result.to_dict()
    details.update(mode="evidence_budget", embedding_model=state.routing_embedder.model_name,
                   privacy_guarantee=False, generation_context_limit="final_k passages; not a token budget")
    q = unit_rows(np.asarray(query)[None])[0]
    citations = [dict(node_id=p.source_id, document=p.document,
                      score=float(unit_rows(np.asarray(p.embedding)[None])[0] @ q)) for p in result.final]
    state.instrumentation.record(QueryLog(
        query_id=query_id, topic_key="evidence-budget", coarse_candidate_ids=[p.source_id for p in profiles],
        genuine_source_ids=result.contacted, dispatched_source_ids=result.contacted,
        stage_latency_ms={"allocation_and_retrieval": result.elapsed_ms}, extra={"routing": details}))
    answer, status = None, "no_evidence" if not citations else "not_implemented"
    if citations and state.generator is not None:
        try:
            answer = state.generator.generate(question, [c["document"] for c in citations])
            status = state.generator.name
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
    return dict(query_id=query_id, answer=answer, citations=citations,
                nodes_contacted=result.contacted, generation_status=status, routing_details=details)
