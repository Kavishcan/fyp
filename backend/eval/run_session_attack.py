"""Session attack: does the routing pattern leak more when an observer links
several follow-up questions about the same patient? (docs/50)

Single-question attacks (docs/39–40, 46) assume every question is seen in
isolation. A clinician asks follow-ups about one patient; the questions come
from the same device and credential, close in time, so a network observer or
a colluding set of hospitals can link them. This harness measures both
routing attacks as the session grows:

- topic inference: naive Bayes over contacted sets, prior once, one
  likelihood per question (attacks/a2_topic_inference.HistoryAttacker
  .rank_session), trained on one half of the sessions, tested on the other;
- source attack: the most frequently contacted hospital across the session
  (expected accuracy with ties split evenly) — intersection by counting.

Sessions: PMC-Patients query patients (the docs/46 setup) whose summaries
have at least five sentences, split into five consecutive chunks — five
follow-up questions about one patient. Label: the hospital holding most of
the patient's cross-article similar patients (docs/46).

Policies: cosine top-4; genuine top-1 + 3 topic-stable decoys; genuine
top-1 + 3 random decoys; fixed anonymity cells of 4; blind unlock (every
hospital, identical traffic — docs/47). The pattern is fully determined by
the selection, so no cryptography runs here.

Run: python -m eval.run_session_attack
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import time
from collections import Counter

import numpy as np

from api.topic import assign_topic_key
from attacks.a2_topic_inference import HistoryAttacker
from baselines.cosine_router import CosineRouter
from eval.embed_cache import CachedEmbedder
from eval.run_hyfedrag_compare import load
from eval.sweep import RESULTS_DIR, SentenceTransformerEmbedder
from nodes.simulator import build_simulated_source
from privacy.cluster_index import kmeans_unit
from router.anonymity import add_decoys, build_cells, cell_cover

POLICIES = ["cosine_top4", "topic_stable_decoys", "random_decoys", "cells", "blind_unlock"]
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def session_chunks(text: str, n: int = 5) -> list[str] | None:
    sentences = [s for s in _SENTENCE.split(text.strip()) if len(s.split()) >= 3]
    if len(sentences) < n:
        return None
    bounds = np.linspace(0, len(sentences), n + 1).astype(int)
    return [" ".join(sentences[a:b]) for a, b in zip(bounds[:-1], bounds[1:])]


def source_attack(session: list[list[str]], genuine: str) -> float:
    """Expected accuracy of naming the most-contacted hospital (ties split)."""
    counts = Counter(s for contacted in session for s in contacted)
    top = max(counts.values())
    tied = [s for s, c in counts.items() if c == top]
    return 1.0 / len(tied) if genuine in tied else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", type=int, default=1000)
    parser.add_argument("--corpus", type=int, default=5000)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    t0 = time.perf_counter()
    corpus, queries = load(args.queries, args.corpus, args.seed)
    embedder = CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
    uids = list(corpus)
    vecs = embedder.embed([corpus[u] for u in uids])
    vecs = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    _, assign = kmeans_unit(vecs, args.clients, args.seed)
    client_of = {u: f"hospital_{int(a)}" for u, a in zip(uids, assign.tolist())}
    clients = sorted(set(client_of.values()))
    profiles = []
    for i, c in enumerate(clients):
        docs = [corpus[u] for u in uids if client_of[u] == c]
        _, prof = build_simulated_source(c, docs, embedder, k=3, sigma=0.0, rng=np.random.default_rng(args.seed + i),
                                         deidentify=False, psi=False)
        profiles.append(prof)
    router = CosineRouter(aggregation="max")
    router.register_sources(profiles)
    cells = build_cells(clients, {c: c for c in clients}, 4)

    sessions = []
    for qid, text, rel in queries:
        chunks = session_chunks(text)
        if chunks:
            label = Counter(client_of[u] for u in rel).most_common(1)[0][0]
            sessions.append((qid, chunks, label))
    chunk_vecs = embedder.embed([c for _, chunks, _ in sessions for c in chunks])
    chunk_vecs = chunk_vecs / np.maximum(np.linalg.norm(chunk_vecs, axis=1, keepdims=True), 1e-12)
    print(f"{len(sessions)} five-question sessions, {len(clients)} hospitals ({time.perf_counter() - t0:.0f}s)", flush=True)

    def contacted(policy: str, q: np.ndarray, salt: int) -> list[str]:
        ranked = list(router.rank(q, top_k=len(clients)).ranked_source_ids)
        if policy == "cosine_top4":
            return ranked[:4]
        if policy == "topic_stable_decoys":
            return add_decoys(ranked[:1], clients, 4, topic_key=assign_topic_key(q, profiles))
        if policy == "random_decoys":
            return add_decoys(ranked[:1], clients, 4, rng=random.Random(salt))
        if policy == "cells":
            return cell_cover(ranked[:1], cells, 4)
        return list(clients)                       # blind unlock: every hospital, identical traffic

    half = len(sessions) // 2
    test_labels = [lab for *_, lab in sessions[half:]]
    floor = max(Counter(test_labels).values()) / len(test_labels)
    rows = []
    for policy in POLICIES:
        patterns = []
        k = 0
        for s_i, (_, chunks, _) in enumerate(sessions):
            patterns.append([contacted(policy, chunk_vecs[k + j], salt=args.seed * 100_000 + s_i * 10 + j)
                             for j in range(len(chunks))])
            k += len(chunks)
        attacker = HistoryAttacker().fit([(p, lab) for pats, (*_, lab) in zip(patterns[:half], sessions[:half])
                                          for p in pats])
        for L in range(1, 6):
            topic = np.mean([attacker.rank_session(p[:L])[0] == lab
                             for p, (*_, lab) in zip(patterns[half:], sessions[half:])])
            source = np.mean([source_attack(p[:L], lab) for p, (*_, lab) in zip(patterns[half:], sessions[half:])])
            rows.append({"policy": policy, "session_length": L, "topic_inference": float(topic),
                         "source_attack": float(source), "topic_majority_floor": floor,
                         "source_chance": 1.0 / len(clients), "sessions_tested": len(sessions) - half})
        r = [x for x in rows if x["policy"] == policy]
        print(f"  {policy:<20} topic " + " ".join(f"L{x['session_length']}={x['topic_inference']:.3f}" for x in r)
              + " | source " + " ".join(f"L{x['session_length']}={x['source_attack']:.3f}" for x in r), flush=True)
    print(f"  floors: topic majority {floor:.3f}, source chance {1 / len(clients):.3f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"session_attack_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
