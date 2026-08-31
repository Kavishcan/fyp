/**
 * Typed client for the FedSafeRouter FastAPI backend (backend/api/).
 * Mirrors backend/api/schemas.py — keep these in sync by hand for now; once
 * the backend stabilises, generate this from /openapi.json instead.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface NodeRegisterRequest {
  node_id: string;
  documents: string[];
  policy_labels?: string[];
  k?: number;
  sigma?: number;
  /** Any name. Omit to share the routing embedder (no heterogeneity). A
   * distinct name simulates a genuinely different, incomparable embedding
   * model for this node's own local retrieval — see backend/api/embedder.py. */
  local_model?: string;
}

export interface NodeRegisterResponse {
  node_id: string;
  document_count_bucket: string;
  profile_version: number;
  centroid_count: number;
  local_model: string;
  note: string;
}

export interface NodeStatus {
  node_id: string;
  trust: number;
  trust_observations: number;
  document_count_bucket: string;
  profile_version: number;
  local_model: string;
}

export interface QueryRequest {
  question: string;
  max_nodes?: number;
  genuine_k?: number;
  sigma?: number;
}

export interface Citation {
  node_id: string;
  document: string;
  score: number;
}

export interface QueryResponse {
  query_id: string;
  answer: string | null;
  citations: Citation[];
  nodes_contacted: string[];
  generation_status: string;
}

export interface AuditResponse {
  query_id: string;
  topic_key: string;
  coarse_candidate_ids: string[];
  genuine_source_ids: string[];
  dispatched_source_ids: string[];
  decoy_source_ids: string[];
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(`${res.status} ${res.statusText}: ${body}`, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; nodes_registered: number }>("/health"),

  registerNode: (req: NodeRegisterRequest) =>
    request<NodeRegisterResponse>("/nodes/register", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  listNodes: () => request<NodeStatus[]>("/nodes"),

  query: (req: QueryRequest) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  audit: (queryId: string) => request<AuditResponse>(`/audit/${encodeURIComponent(queryId)}`),
};

export { ApiError, BASE_URL };
