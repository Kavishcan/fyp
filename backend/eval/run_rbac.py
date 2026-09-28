"""Role-based access to node collections: what can each role extract? (docs/45)

A hospital node holds three collections — "public" (scifact abstracts),
"research" (nfcorpus abstracts) and "clinical_notes" (fictional patient
notes built from trec-covid text, de-identified as docs/44) — with the
policy researcher -> {research}, clinician -> {research, clinical_notes}.
"public" is readable by every authorised client.

For each client (no role, researcher, clinician, and a researcher who LIES
about being a clinician) two adversarial extractions are run with the real
code paths:

- PSI dump: probe EVERY published cluster id of EVERY collection —
  ignoring the client's own role filter — and open whatever the node's
  evaluations allow. Fraction of each collection's documents obtained.
- Legacy dump: call the unauthenticated text/vector retrieve path with
  every document's own text as the query. Fraction of each collection
  returned.

That a clinician's ordinary query retrieves clinical notes (and a
researcher's does not) is checked end to end in tests/test_rbac.py.

Structure visibility (role-scoped publication): what each client can learn
about a restricted collection WITHOUT reading its documents — the share of
its cluster centroids it can obtain, and how many words that occur only in
restricted documents appear in the node's public description/topics. The
"before" rows reconstruct what the previous design published (every
cluster centroid, topics over every document) from the same node.

In-process nodes, hashing embedder (the enforcement does not depend on the
embedding model). Fictional values only.

Run: python -m eval.run_rbac
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from eval.run_feb4rag import sample_corpus
from eval.run_node_deid import fictional_record, inject
from eval.sweep import RESULTS_DIR
from nodes.embedding import HashingEmbedder
from nodes.metadata import describe_documents
from nodes.simulator import build_simulated_source
from privacy.credentials import Authorizer, ClientPolicy, new_credential, permitted_collections
from privacy.psi import PSIClient

POLICY = {"researcher": ["research"], "clinician": ["research", "clinical_notes"]}
CLIENTS = {"no_role": (), "researcher": ("researcher",), "clinician": ("clinician",)}


def build(seed: int, per_collection: int):
    rng = random.Random(seed)
    public = sample_corpus("scifact", per_collection, 5_000, rng)
    research = sample_corpus("nfcorpus", per_collection, 5_000, rng)
    clinical = [inject(d[:400], fictional_record(rng, i), cued=True)
                for i, d in enumerate(sample_corpus("trec-covid", per_collection, 20_000, rng))]
    docs = public + research + clinical
    cols = ["public"] * len(public) + ["research"] * len(research) + ["clinical_notes"] * len(clinical)
    node, profile = build_simulated_source("hosp", docs, HashingEmbedder(), k=3, sigma=0.0,
                                           rng=np.random.default_rng(seed), collections=cols, access_policy=POLICY)
    creds = {name: new_credential(name, roles=roles) for name, roles in CLIENTS.items()}
    node.authorizer = Authorizer("hosp", {n: ClientPolicy(c.key, 10**6, CLIENTS[n]) for n, c in creds.items()})
    return node, profile, creds, cols


def psi_dump(node, profile, cred) -> dict[str, float]:
    """Probe every cluster id the node holds — public AND restricted, whether
    or not the client could see its centroid — and open what the node allows."""
    all_ids = sorted(node.psi.table)
    q = PSIClient.blind(all_ids)
    node.authorizer.check(cred.sign("hosp", q.blinded), q.blinded)
    allowed = permitted_collections(node.access_policy, node.authorizer.roles_of(cred.client_id),
                                    node.psi.collections, authorised=True)
    opened = PSIClient.open_matches_multi(q, node.psi.evaluate_for(q.blinded, allowed), "hosp", node.psi.envelopes_for(None))
    got = [p["document"] for ps in opened.values() for p in ps]
    return fractions(got, node)


def legacy_dump(node) -> dict[str, float]:
    got = []
    for text in node.documents:
        got += [p.document for p in node.retrieve_from_text(text, top_n=3)]
    return fractions(got, node)


def fractions(got: list[str], node) -> dict[str, float]:
    got_set = set(got)
    out = {}
    for c in sorted(set(node.collections)):
        docs = [d for d, col in zip(node.documents, node.collections) if col == c]
        out[c] = sum(1 for d in docs if d in got_set) / len(docs)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--per-collection", type=int, default=150)
    args = parser.parse_args()

    node, profile, creds, cols = build(args.seed, args.per_collection)
    node.local_embedder = node.local_embedder or HashingEmbedder()
    print(f"node: {len(node.documents)} docs, collections "
          f"{ {c: cols.count(c) for c in sorted(set(cols))} }, {len(node.psi.table)} clusters "
          f"({len(profile.cluster_centroids)} published in the profile)", flush=True)
    rows = []
    for name, cred in creds.items():
        rows.append({"client": name, "path": "psi_dump_all_clusters", **psi_dump(node, profile, cred)})
    liar = type(creds["researcher"])(client_id="researcher", key=creds["researcher"].key, roles=("clinician",))
    rows.append({"client": "researcher_claiming_clinician", "path": "psi_dump_all_clusters", **psi_dump(node, profile, liar)})
    rows.append({"client": "anyone", "path": "legacy_retrieve_every_doc", **legacy_dump(node)})
    for r in rows:
        print(f"  {r['client']:<30} {r['path']:<26} " + " ".join(f"{c}={r[c]:.3f}" for c in ("public", "research", "clinical_notes")), flush=True)

    # --- structure visibility ------------------------------------------------
    restricted = {}
    for cid, (c, _) in node.restricted_clusters.items():
        restricted.setdefault(c, []).append(cid)
    public_words = set(" ".join(d for d, c in zip(node.documents, node.collections) if c == "public").lower().split())
    restricted_only = {}
    for c in restricted:
        vocab = describe_documents([d for d, col in zip(node.documents, node.collections) if col == c], max_topics=64)["topics"]
        restricted_only[c] = {w for w in vocab if w not in public_words}
    before_topics = set(describe_documents(node.documents)["topics"])
    after_topics = set(profile.topics)
    for c in sorted(restricted):
        rows.append({"client": "everyone (before: all centroids in profile)", "path": f"structure:{c}",
                     "centroids_visible": 1.0,
                     "restricted_only_topic_words_published": len(before_topics & restricted_only[c])})
        for name, cred in creds.items():
            node.authorizer.check(cred.sign("hosp", []), [])
            allowed = permitted_collections(node.access_policy, node.authorizer.roles_of(name), node.psi.collections, authorised=True)
            got = {e["id"] for e in node.restricted_centroids([a for a in allowed if a != "public"]) if e["collection"] == c}
            rows.append({"client": f"{name} (after)", "path": f"structure:{c}",
                         "centroids_visible": len(got) / len(restricted[c]),
                         "restricted_only_topic_words_published": len(after_topics & restricted_only[c])})
    for r in rows:
        if str(r["path"]).startswith("structure:"):
            print(f"  {r['client']:<44} {r['path']:<24} centroids_visible={r['centroids_visible']:.3f} "
                  f"restricted-only topic words in public profile={r['restricted_only_topic_words_published']}", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"rbac_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
