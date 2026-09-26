"""Node-side de-identification: does PII leave a hospital node? (docs/44)

Three measurements, all through the node's real code paths:

A. Detection recall on the project's 200 synthetic privacy cases
   (fedrag-dataset): each case carries a fictional name, email and reference
   id. Fraction of each value type absent after redaction, for the old
   embed-only regex (nodes/profile.redact_pii), the new rules
   (privacy/deidentify), and rules + the node's registry of its own
   identifiers.

B. Canary leakage through serving. Simulated nodes are built from real
   nfcorpus documents with fictional patient records injected into a share
   of them — name, MRN, date of birth, phone, email — in two templates: with
   a cue ("Patient Rahul Menon, MRN ...") and bare ("Rahul Menon was
   admitted ..."). A fully AUTHORISED client then dumps everything the node
   will ever serve: it probes every cluster over PSI and opens every
   envelope, calls legacy retrieve for every document, and reads the public
   profile (description, topics). A canary value counts as leaked if it
   appears anywhere in that output. Conditions: no de-identification (the
   node before docs/44: embeddings were redacted, served text was not),
   rules, rules + registry.

C. Cost on clean text. On 2,000-document nfcorpus and scifact pools with no
   injected PII: fraction of documents altered, placeholders by type (false
   positives), and dense recall@10 of the judged queries against raw versus
   de-identified documents (bge-base).

Fictional values only. Not a validation of a clinical de-identifier.

Run: python -m eval.run_node_deid
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from collections import Counter

import numpy as np

from eval.embed_cache import CachedEmbedder
from eval.sweep import REPO_ROOT, RESULTS_DIR, HashingEmbedder, SentenceTransformerEmbedder
from nodes.embedding import HashingEmbedder as NodeHashing
from nodes.profile import redact_pii
from nodes.simulator import build_simulated_source
from privacy.cluster_index import assign_clusters
from privacy.deidentify import Deidentifier
from privacy.psi import PSIClient

CASES = REPO_ROOT.parent / "fedrag-dataset" / "data" / "processed" / "privacy" / "privacy_cases.jsonl"

FIRST = ["Amelia", "Rahul", "Chen", "Olumide", "Sofia", "Kavya", "Liam", "Aisha", "Mateo", "Hannah",
         "Tomasz", "Priya", "Noah", "Fatima", "Kenji", "Isla", "Arjun", "Zara", "Lucas", "Nadia"]
LAST = ["Hart", "Menon", "Wei", "Adeyemi", "Rossi", "Iyer", "Walsh", "Rahman", "Garcia", "Becker",
        "Nowak", "Sharma", "Clarke", "Haddad", "Sato", "Morgan", "Pillai", "Khan", "Silva", "Petrov"]


def fictional_record(rng: random.Random, i: int) -> dict:
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    return {
        "name": name,
        "mrn": f"MRN {rng.randint(1000000, 9999999)}",
        "dob": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{rng.randint(1940, 2005)}",
        "phone": f"+44 7700 {rng.randint(100000, 999999)}",
        "email": f"{name.split()[0].lower()}.{name.split()[1].lower()}{i}@example.invalid",
    }


def inject(doc: str, rec: dict, cued: bool) -> str:
    if cued:
        return (f"Patient {rec['name']}, {rec['mrn']}, DOB {rec['dob']}, tel {rec['phone']}, "
                f"email {rec['email']}. {doc}")
    return (f"{rec['name']} was admitted; record {rec['mrn']}, born {rec['dob']}, "
            f"contact {rec['phone']} / {rec['email']}. {doc}")


def leaked(values: list[str], served: str) -> float:
    served_l = served.lower()
    return float(np.mean([1.0 if v.lower() in served_l else 0.0 for v in values])) if values else 0.0


def dump_node(node, profile) -> str:
    """Everything an authorised client can ever obtain from this node."""
    out = [profile.description or "", " ".join(profile.topics or [])]
    cids = list(range(len(profile.cluster_centroids)))
    q = PSIClient.blind(cids)
    opened = PSIClient.open_matches(q, PSIClient.unblind(q, node.psi.evaluate(q.blinded)), node.source_id,
                                    node.psi.envelopes_for(None))
    out += [p["document"] for ps in opened.values() for p in ps]
    out += list(node.documents)   # legacy/smart/v2 retrieve serves these texts
    return "\n".join(out)


def part_a() -> list[dict]:
    cases = [json.loads(l) for l in CASES.read_text().splitlines() if l.strip()]
    registry = [v["value"] for c in cases for v in c["sensitive_values"] if v["type"] != "fictional_email"]
    conditions = {"embed_only_regex (before)": redact_pii, "rules": Deidentifier().redact,
                  "rules + registry": Deidentifier(known_identifiers=registry).redact}
    rows = []
    for name, fn in conditions.items():
        by_type = Counter(); total = Counter()
        for c in cases:
            text = fn(c["augmented_query"])
            for v in c["sensitive_values"]:
                total[v["type"]] += 1
                by_type[v["type"]] += 0 if v["value"].lower() in text.lower() else 1
        rows.append({"part": "A", "condition": name, **{f"removed_{t}": by_type[t] / total[t] for t in sorted(total)},
                     "cases": len(cases)})
    return rows


def part_b(embedder, seed: int, n_nodes: int, docs_per_node: int, share: float) -> list[dict]:
    from eval.run_feb4rag import sample_corpus

    rng = random.Random(seed)
    corpus = sample_corpus("nfcorpus", n_nodes * docs_per_node, 50_000, rng)
    rows = []
    for cued in (True, False):
        nodes_docs, records = [], []
        for n in range(n_nodes):
            docs = corpus[n * docs_per_node:(n + 1) * docs_per_node]
            recs = []
            for i in range(len(docs)):
                if rng.random() < share:
                    rec = fictional_record(rng, n * 1000 + i)
                    docs[i] = inject(docs[i], rec, cued)
                    recs.append(rec)
            nodes_docs.append(docs)
            records.append(recs)
        for cond in ("none (before)", "rules", "rules + registry"):
            leak = Counter(); total = Counter()
            for n, (docs, recs) in enumerate(zip(nodes_docs, records)):
                registry = [r["name"] for r in recs] + [r["mrn"] for r in recs] if cond == "rules + registry" else []
                node, profile = build_simulated_source(f"hosp_{n}", list(docs), embedder, k=3, sigma=0.0,
                                                       rng=np.random.default_rng(seed), deidentify=cond != "none (before)",
                                                       known_identifiers=registry)
                served = dump_node(node, profile)
                for rec in recs:
                    for field_ in ("name", "mrn", "dob", "phone", "email"):
                        total[field_] += 1
                        leak[field_] += 1 if rec[field_].lower() in served.lower() else 0
            rows.append({"part": "B", "template": "cued" if cued else "bare", "condition": cond,
                         "records": total["name"],
                         **{f"leaked_{f}": leak[f] / total[f] if total[f] else float("nan") for f in ("name", "mrn", "dob", "phone", "email")}})
            print(f"  B {rows[-1]['template']:<5} {cond:<18} " + " ".join(
                f"{f}={rows[-1]['leaked_' + f]:.3f}" for f in ("name", "mrn", "dob", "phone", "email")), flush=True)
    return rows


def part_c(embedder, seed: int) -> list[dict]:
    from eval.run_bucket_recall import dense_recall, load_pool

    rows = []
    deid = Deidentifier()
    for corpus in ("nfcorpus", "scifact"):
        ids, texts, queries, relevant = load_pool(corpus, 100, 2000, seed)
        before = Counter(deid.counts)
        clean = deid.redact_all(texts)
        changed = sum(1 for a, b in zip(texts, clean) if a != b)
        added = {k: deid.counts[k] - before.get(k, 0) for k in deid.counts}
        qv = embedder.embed([t for _, t in queries]); qv /= np.linalg.norm(qv, axis=1, keepdims=True)
        raw = embedder.embed(texts); raw /= np.linalg.norm(raw, axis=1, keepdims=True)
        cln = embedder.embed(clean); cln /= np.linalg.norm(cln, axis=1, keepdims=True)
        rows.append({"part": "C", "corpus": corpus, "docs": len(texts), "docs_altered": changed / len(texts),
                     "placeholders": json.dumps({k: v for k, v in added.items() if v}),
                     "dense_recall@10_raw": dense_recall(qv, raw, relevant, 10),
                     "dense_recall@10_deidentified": dense_recall(qv, cln, relevant, 10)})
        print(f"  C {corpus}: altered {rows[-1]['docs_altered']:.3f} {rows[-1]['placeholders']} "
              f"recall@10 {rows[-1]['dense_recall@10_raw']:.3f} -> {rows[-1]['dense_recall@10_deidentified']:.3f}", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--nodes", type=int, default=6)
    parser.add_argument("--docs-per-node", type=int, default=60)
    parser.add_argument("--share", type=float, default=0.3, help="share of documents carrying a patient record")
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    eval_embedder = (CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
                     if args.embedder == "sentence-transformer" else HashingEmbedder())
    rows = part_a()
    for r in rows:
        print("  A", r["condition"], {k: round(v, 3) for k, v in r.items() if k.startswith("removed_")}, flush=True)
    rows += part_b(NodeHashing(n_features=256), args.seed, args.nodes, args.docs_per_node, args.share)
    rows += part_c(eval_embedder, args.seed)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"node_deid_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with out.open("w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
