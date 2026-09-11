"""Transport-cost measurement over REAL MCP node subprocesses (docs/33).

eval/run_scaling.py measures routing at 30–1,000 virtual sources in-process.
This measures the other half the proposal promised — routing latency and
communication volume with genuinely separate node processes — and keeps the
two apart, as CLAUDE.md requires: the numbers here are per-contact transport
cost on this machine, not a distributed deployment and not a retrieval-quality
result.

Every node is one `python -m nodes.mcp_server` process talked to over the MCP
stdio protocol via nodes/mcp_client.MCPNodeHandle. The client deliberately
spawns a fresh subprocess per call, so per-contact latency here is dominated
by interpreter start-up plus profile construction, not by retrieval; a
persistent-session client would remove most of it. That is reported, not
hidden, because it is what the shipped coordinator does.

Node data files come from data/mcp_nodes + data/mcp_nodes_extra (generated
by data/prepare_beir_nodes.py from real BEIR/MMLU slices). Those slices are
not aligned to BEIR qrels, so no recall is computed — only cost. The routing
embedder in this path is the 256-d hashing placeholder the live demo uses,
so routing decisions here are not the bge-base decisions of docs/31–33.

Per (registered node count, mode):
- registration_ms_per_node   get_profile over MCP, one spawn per node.
- total_ms / embed_ms / routing_ms / retrieval_ms   per-query stages from
                             api/state.py instrumentation.
- contact_ms                 mean per contacted node (one MCP round trip).
- request_bytes / response_bytes   application JSON payloads per query.
- psi_envelopes_delivered / psi_passages_disclosed   psi mode only: mean per
                             contacted node (docs/35 disclosure axis).

Mode `psi` (docs/03 target): blinded cluster ids out, OPRF outputs and an
envelope set back, two MCP round trips per contact in this client. The node
never receives the query or a vector.

Run: python -m eval.run_mcp_transport
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time
from pathlib import Path

import numpy as np

from api.state import AppState
from eval.sweep import BEIR_DIR, REPO_ROOT, RESULTS_DIR

NODE_DIRS = (REPO_ROOT / "data" / "mcp_nodes", REPO_ROOT / "data" / "mcp_nodes_extra")


def available_node_files() -> list[Path]:
    files: list[Path] = []
    for directory in NODE_DIRS:
        if directory.is_dir():
            files.extend(sorted(directory.glob("*.json")))
    return files


def sample_queries(corpora: list[str], per_corpus: int) -> list[str]:
    """Real BEIR query texts; relevance is not used here, only the text."""
    texts: list[str] = []
    for corpus in corpora:
        path = BEIR_DIR / corpus / "queries.jsonl"
        if not path.exists():
            continue
        with path.open() as handle:
            for i, line in enumerate(handle):
                if i >= per_corpus:
                    break
                texts.append(json.loads(line)["text"])
    return texts


def register_nodes(state: AppState, files: list[Path], *, persistent: bool = False) -> list[float]:
    """Registers each node over MCP and returns per-node registration ms."""
    async def _go():
        timings = []
        for data_file in files:
            started = time.perf_counter()
            await state.register_mcp_node_async(data_file, persistent=persistent)
            timings.append((time.perf_counter() - started) * 1000.0)
        return timings

    return asyncio.run(_go())


def summarise(logs: list[dict], *, mode: str, registered: int, registration_ms: list[float],
              transport: str = "mcp-stdio-subprocess-per-call") -> dict:
    def stage(name: str) -> list[float]:
        return [log["stage_latency_ms"].get(name, float("nan")) for log in logs]

    contact_ms = [ms for log in logs for ms in log["stage_latency_ms"].get("retrieval_per_node", {}).values()]
    psi_nodes = [info for log in logs for info in (log.get("extra", {}).get("routing", {}).get("psi", {}) or {}).get("per_node", {}).values()]
    contacts = [len(log["dispatched_source_ids"]) for log in logs]
    req = [log["bytes_transferred"].get("request_total", 0) for log in logs]
    resp = [log["bytes_transferred"].get("response_total", 0) for log in logs]
    errors = sum(len(log.get("extra", {}).get("routing", {}).get("retrieval_errors", {}) or {}) for log in logs)
    return {
        "mode": mode,
        "registered_nodes": registered,
        "queries": len(logs),
        "transport": transport,
        "registration_ms_per_node": float(np.mean(registration_ms)),
        "registration_total_ms": float(np.sum(registration_ms)),
        "contacts": float(np.mean(contacts)),
        "total_ms": float(np.mean(stage("total"))),
        "total_p95_ms": float(np.percentile(stage("total"), 95)),
        "embed_ms": float(np.mean(stage("embed"))),
        "routing_ms": float(np.mean(stage("routing"))),
        "retrieval_ms": float(np.mean(stage("retrieval_total"))),
        "contact_ms": float(np.mean(contact_ms)) if contact_ms else float("nan"),
        "contact_p95_ms": float(np.percentile(contact_ms, 95)) if contact_ms else float("nan"),
        "request_bytes": float(np.mean(req)),
        "response_bytes": float(np.mean(resp)),
        "retrieval_errors": errors,
        "psi_envelopes_delivered": float(np.mean([i["envelopes_delivered"] for i in psi_nodes])) if psi_nodes else float("nan"),
        "psi_passages_disclosed": float(np.mean([i["passages_disclosed"] for i in psi_nodes])) if psi_nodes else float("nan"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--node-counts", nargs="+", type=int, default=[10, 30, 0],
                        help="registered nodes per tier; 0 means every available node file")
    parser.add_argument("--modes", nargs="+", choices=["legacy", "smart", "v2", "psi"], default=["legacy", "v2", "psi"])
    parser.add_argument("--psi-fetch-set", type=int, default=None, help="psi: envelope anonymity set per node (None = all)")
    parser.add_argument("--persistent", action="store_true", help="keep one server process + MCP session per node")
    parser.add_argument("--n-queries", type=int, default=20)
    parser.add_argument("--query-corpora", nargs="+", default=["arguana", "nfcorpus", "scifact", "fiqa"])
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    args = parser.parse_args()

    files = available_node_files()
    if not files:
        raise SystemExit("no node data files; run data/prepare_beir_nodes.py first")
    per_corpus = max(1, -(-args.n_queries // len(args.query_corpora)))
    questions = sample_queries(args.query_corpora, per_corpus)[: args.n_queries]
    if not questions:
        raise SystemExit("no BEIR queries found under vendor/beir")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    log_dir = REPO_ROOT / "backend" / "experiments" / "runs" / f"mcp_transport_{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(files)} node files available, {len(questions)} queries", flush=True)

    rows: list[dict] = []
    for count in args.node_counts:
        chosen = files if count == 0 else files[:count]
        if count and len(chosen) < count:
            print(f"only {len(chosen)} node files; tier {count} runs with all of them", flush=True)
        for mode in args.modes:
            log_path = log_dir / f"{mode}_{len(chosen)}.jsonl"
            state = AppState(instrumentation_path=str(log_path))
            state.generator = None  # transport only; never call an external LLM here
            registration_ms = register_nodes(state, chosen, persistent=args.persistent)
            print(f"tier {len(chosen)} nodes, mode {mode}: registered in "
                  f"{sum(registration_ms) / 1000:.1f}s", flush=True)
            for question in questions:
                state.run_query(question, max_nodes=args.max_nodes, genuine_k=args.genuine_k,
                                sigma=0.0, routing_mode=mode, psi_fetch_set=args.psi_fetch_set)
            logs = state.instrumentation.read_all()
            row = summarise(logs, mode=mode, registered=len(chosen), registration_ms=registration_ms,
                            transport="mcp-stdio-persistent-session" if args.persistent else "mcp-stdio-subprocess-per-call")
            for node_id in list(state.nodes):
                state.remove_node(node_id)  # closes persistent sessions
            rows.append(row)
            print(f"  total {row['total_ms']:.0f}ms/query, contact {row['contact_ms']:.0f}ms, "
                  f"request {row['request_bytes']:.0f}B, response {row['response_bytes']:.0f}B", flush=True)
            _write(RESULTS_DIR / f"mcp_transport_{run_id}.csv", rows)

    print(json.dumps(rows, indent=2))
    print(f"wrote {RESULTS_DIR / f'mcp_transport_{run_id}.csv'}\nraw logs in {log_dir}")


def _write(path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
