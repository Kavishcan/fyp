"""Enumeration cost against a PSI node (docs/37, experiment E9).

A malicious *client* wants the node's whole table. Under the OPRF it can
only open an envelope for a cluster id the node has evaluated for it, and
the node evaluates at most `nprobe` ids per query. Centroids are public, so
the attacker can target every cluster deliberately. Without the OPRF (labels
keyed by a plain hash of the id) the whole table opens offline from one
download — the OPRF is what turns enumeration into a per-query cost the node
can rate-limit and audit.

This simulates both attackers against a node with C clusters and reports
queries-to-open-everything; with a rate limit R queries per credential per
day that is a number of days. It is arithmetic made explicit, not a
security result: a colluding pool of credentials divides the cost.

Run: python -m eval.run_psi_enumeration
"""
from __future__ import annotations

import argparse
import json
import math
import random

from privacy.psi import PSIClient, PSINode


def simulate(clusters: int, nprobe: int, *, adaptive: bool, seed: int, daily_budget: int | None = None) -> int:
    """Queries until every cluster's envelope has been opened. With
    `daily_budget`, the real Authorizer gates each query and the count is in
    DAYS of budget consumed (the enumerator resumes each day)."""
    node = PSINode("target")
    node.build_table({c: [{"document": f"c{c}", "embedding": [0.0]}] for c in range(clusters)})
    rng = random.Random(seed)
    opened: set[int] = set()
    queries = 0
    envelopes = node.envelopes_for(None)
    authz = cred = None
    day = 0.0
    if daily_budget is not None:
        from privacy.credentials import Authorizer, ClientPolicy, Unauthorized, new_credential

        cred = new_credential("enumerator")
        authz = Authorizer("target", {"enumerator": ClientPolicy(cred.key, daily_budget)})
    while len(opened) < clusters:
        pool = [c for c in range(clusters) if c not in opened] if adaptive else list(range(clusters))
        wanted = rng.sample(pool, min(nprobe, len(pool)))
        q = PSIClient.blind(wanted)
        if authz is not None:
            try:
                authz.check(cred.sign("target", q.blinded, now=day), q.blinded, now=day)
            except Unauthorized:
                day += 86400.0   # budget gone: wait for tomorrow
                continue
        outputs = PSIClient.unblind(q, node.evaluate(q.blinded))
        opened |= set(PSIClient.open_matches(q, outputs, node.node_id, envelopes))
        queries += 1
    return queries if daily_budget is None else int(day // 86400) + 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clusters", nargs="+", type=int, default=[4, 20, 150, 200])
    parser.add_argument("--nprobe", type=int, default=2)
    parser.add_argument("--rate-limit-per-day", type=int, default=100,
                        help="per-credential daily EVALUATION budget enforced by privacy/credentials.Authorizer")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    args = parser.parse_args()

    rows = []
    for clusters in args.clusters:
        adaptive = [simulate(clusters, args.nprobe, adaptive=True, seed=s) for s in args.seeds]
        blind = [simulate(clusters, args.nprobe, adaptive=False, seed=s) for s in args.seeds]
        gated = [simulate(clusters, args.nprobe, adaptive=True, seed=s, daily_budget=args.rate_limit_per_day) for s in args.seeds]
        rows.append({
            "clusters": clusters, "nprobe": args.nprobe,
            "without_oprf_queries": 0,  # one download opens everything offline
            "adaptive_queries": sum(adaptive) / len(adaptive),
            "adaptive_lower_bound": math.ceil(clusters / args.nprobe),
            "random_queries": sum(blind) / len(blind),
            "daily_evaluation_budget": args.rate_limit_per_day,
            "days_to_dump_with_authorizer": sum(gated) / len(gated),   # enforced by the real gate, not arithmetic
        })
        print(rows[-1], flush=True)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
