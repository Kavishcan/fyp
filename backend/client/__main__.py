"""Ask a federation from the command line, with no server in the path (docs/52).

    python -m client --nodes ../data/mcp_nodes/*.json --question "..." [--probes 8]
                     [--credential cred.json] [--generate] [--cover-ticks 5 --interval 2]

Each `--nodes` file is a node's data file; the node runs as its own MCP
process (nodes/mcp_server.py) and receives only blinded points and the
credential. ROUTING_EMBEDDER must match the nodes'. `--credential` is a JSON
file {"client_id": ..., "key_hex": ..., "roles": [...]} issued by the
federation. `--generate` answers with the local Ollama model
(LLM_PROVIDER=ollama). With `--cover-ticks N`, the question is sent inside a
constant-rate schedule of N rounds (the others cover rounds), one per
`--interval` seconds, at a random tick.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from client import CoverTrafficScheduler, Device, MCPTransport
from nodes.mcp_client import MCPNodeHandle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nodes", nargs="+", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--probes", type=int, default=8)
    parser.add_argument("--evidence", type=int, default=2)
    parser.add_argument("--credential", type=Path)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--cover-ticks", type=int, default=0)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    credential = None
    if args.credential:
        from privacy.credentials import Credential

        spec = json.loads(args.credential.read_text())
        credential = Credential(spec["client_id"], bytes.fromhex(spec["key_hex"]), tuple(spec.get("roles", ())))
    generator = None
    if args.generate:
        from generation.ollama_generator import OllamaGenerator

        generator = OllamaGenerator()
    device = Device(credential=credential, generator=generator, probes=args.probes, evidence_top_k=args.evidence)
    for f in args.nodes:
        device.connect(MCPTransport(MCPNodeHandle(f.stem, f)))
    print(f"connected to {len(device.transports)} nodes; tables cached: "
          f"{sum(t.size_bytes() for t in device.cache.tables.values()) / 1e6:.2f} MB")

    if args.cover_ticks:
        scheduler = CoverTrafficScheduler(device, interval_s=args.interval)
        real_at = random.randrange(args.cover_ticks)
        answered = []
        for i in range(args.cover_ticks):
            if i == real_at:
                scheduler.submit(args.question)
            answered += scheduler.run(1)
        result = answered[0].result
        print(f"rounds sent: {scheduler.rounds} (identical on the wire)")
    else:
        result = device.ask(args.question)

    print("each node received:", {n: f"{s['points']} points, {s['request_bytes']} B" for n, s in result["sent"].items()})
    print("real probes (known only here):", result["real_probes"])
    for c in result["citations"]:
        print(f"  [{c['node_id']}/{c['collection']}] {c['document'][:120]}")
    if result["answer"]:
        print("answer:", result["answer"])
    if result["errors"]:
        print("errors:", result["errors"])


if __name__ == "__main__":
    main()
