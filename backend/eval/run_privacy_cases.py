"""Synthetic privacy and attack cases from the project's fedrag-dataset
(docs/37): what does each dispatch mode expose, and does routing stay
within the allowed clients?

`privacy_cases.jsonl` (200): a FeB4RAG request prefixed with three fictional
sensitive values (name, email, reference id) and an `allowed_clients` list.
`attack_cases.jsonl` (60): a malicious source that publishes an attractive
profile and returns "TEST ATTACK" content as evidence.

Per privacy case and mode, three things are measured:

- sensitive_values_exposed_to_nodes   fraction of the three values a
  contacted node can read from what it receives. Text modes: string match
  on the payload. v2: what the docs/32 nearest-neighbour inverter recovers
  from the dispatched vector, against a reference pool of all 200 augmented
  and 200 original requests — a lower bound on a real inverter. psi: the
  node receives blinded group elements; exposure is 0 by construction
  (DDH), and the empirical column checks that repeated blindings of the same
  case share no bytes.
- allowed_client_reached / unnecessary_contacts   routing against the
  case's `allowed_clients`, counted over the genuine set and over the full
  dispatched set (decoys are unnecessary contacts by design — that is the
  A2 price, shown rather than hidden).
- redaction   the repository's regex heuristic (nodes/profile.redact_pii)
  applied to the text before a text-mode dispatch, as the cheap comparison.

Per attack case: attacker selection rate and how often its returned passage
is cited (each contacted node contributes its top passage; there is no
cross-node evidence filter in the pipeline, so cited = contacted).

Engines are the 13 FeB4RAG engines with local BEIR corpora, profiled from
corpus samples exactly as eval/run_feb4rag.py. In-process; no MCP.

Run: python -m eval.run_privacy_cases
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path

import numpy as np

from attacks.a1_inversion import NearestNeighbourInversion
from baselines.base import SourceProfile
from eval.embed_cache import CachedEmbedder
from eval.run_feb4rag import available_engines, sample_corpus
from eval.run_mode_comparison import dispatch_for_mode
from eval.sweep import REPO_ROOT, RESULTS_DIR, HashingEmbedder, SentenceTransformerEmbedder, _normalise, build_node_profiles
from nodes.profile import redact_pii
from nodes.simulator import forge_profile
from privacy.psi import PSIClient

DATASET_DIR = REPO_ROOT.parent / "fedrag-dataset" / "data" / "processed" / "privacy"
MODES = ("legacy", "smart", "v2", "psi")


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def exposed_fraction(text: str, values: list[str]) -> float:
    return float(np.mean([1.0 if v.lower() in text.lower() else 0.0 for v in values])) if values else 0.0


def run(args) -> tuple[list[dict], list[dict]]:
    cases = load_jsonl(DATASET_DIR / "privacy_cases.jsonl")
    attacks = load_jsonl(DATASET_DIR / "attack_cases.jsonl")
    engines = available_engines()
    if args.embedder == "sentence-transformer":
        embedder = CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
    else:
        embedder = HashingEmbedder()

    rng = random.Random(args.seed)
    node_docs = {e: sample_corpus(e, args.docs_per_engine, args.scan_lines, rng) for e in engines}
    profiles = build_node_profiles(node_docs, embedder, k=3, seed=args.seed)
    print(f"{len(engines)} engines, {len(cases)} privacy cases, {len(attacks)} attack cases", flush=True)

    augmented = [c["augmented_query"] for c in cases]
    originals = [c["original_query"] for c in cases]
    aug_vec = [_normalise(v) for v in embedder.embed(augmented)]
    red_texts = [redact_pii(t) for t in augmented]
    red_vec = [_normalise(v) for v in embedder.embed(red_texts)]
    inverter = NearestNeighbourInversion(augmented + originals, np.array(aug_vec + [_normalise(v) for v in embedder.embed(originals)]))

    orig_vec = [_normalise(v) for v in embedder.embed(originals)]
    np_rng = np.random.default_rng(args.seed)
    rows: list[dict] = []
    # `redacted`: False = augmented text as-is; True = regex-redacted; "original"
    # = the un-augmented request, the routing reference the PII prefix is
    # measured against.
    for mode in MODES:
        for redacted in (False, True, "original"):
            if redacted is True and mode in {"v2", "psi"} and not args.redact_all:
                continue
            if redacted == "original" and mode != "legacy":
                continue
            exp, reached_g, reached_d, unnecessary_g, unnecessary_d, contacts, linkable = [], [], [], [], [], [], []
            for i, case in enumerate(cases):
                values = [v["value"] for v in case["sensitive_values"]]
                allowed = set(case["allowed_clients"]) & set(engines)
                if redacted == "original":
                    text, vec = originals[i], orig_vec[i]
                elif redacted:
                    text, vec = red_texts[i], red_vec[i]
                else:
                    text, vec = augmented[i], aug_vec[i]
                dispatched = dispatch_for_mode(
                    "v2" if mode == "psi" else mode, vec, profiles, "|".join(sorted(allowed)), allowed,
                    max_nodes=args.max_nodes, genuine_k=args.genuine_k, coarse_k=args.coarse_k, sigma=0.0, rng=np_rng,
                )
                # Genuine set = the local ranking's top genuine_k (identical across modes that rank locally).
                genuine = dispatched[: args.genuine_k] if mode == "smart" else [
                    s for s in _genuine_ids(vec, profiles, args.genuine_k) if s in dispatched]
                if mode in {"legacy", "smart"}:
                    exp.append(exposed_fraction(text, values))
                elif mode == "v2":
                    exp.append(exposed_fraction(inverter.recover(vec), values))
                else:
                    q1, q2 = PSIClient.blind([0, 1]), PSIClient.blind([0, 1])
                    linkable.append(1.0 if set(q1.blinded) & set(q2.blinded) else 0.0)
                    exp.append(0.0)
                reached_g.append(1.0 if set(genuine) & allowed else 0.0)
                reached_d.append(1.0 if set(dispatched) & allowed else 0.0)
                unnecessary_g.append(len([s for s in genuine if s not in allowed]))
                unnecessary_d.append(len([s for s in dispatched if s not in allowed]))
                contacts.append(len(dispatched))
            rows.append({
                "mode": mode, "input": {False: "augmented", True: "regex_redacted", "original": "original_no_pii"}[redacted],
                "cases": len(cases),
                "sensitive_values_exposed_to_nodes": float(np.mean(exp)),
                "psi_blinding_linkable": float(np.mean(linkable)) if linkable else float("nan"),
                "allowed_client_reached_genuine": float(np.mean(reached_g)),
                "allowed_client_reached_dispatched": float(np.mean(reached_d)),
                "unnecessary_contacts_genuine": float(np.mean(unnecessary_g)),
                "unnecessary_contacts_dispatched": float(np.mean(unnecessary_d)),
                "contacts": float(np.mean(contacts)),
            })
            print(f"  {mode:<7} input={rows[-1]['input']:<15} exposed {rows[-1]['sensitive_values_exposed_to_nodes']:.3f} "
                  f"reached(genuine) {rows[-1]['allowed_client_reached_genuine']:.3f} "
                  f"unnecessary(dispatched) {rows[-1]['unnecessary_contacts_dispatched']:.2f}", flush=True)

    # Attack cases: one forged-profile attacker returning the malicious content.
    attack_rows: list[dict] = []
    attack_vecs = {}
    for a in attacks:
        case = next(c for c in cases if c["case_id"] == a["privacy_case_id"])
        attack_vecs[a["attack_id"]] = aug_vec[cases.index(case)]
    mean_query = _normalise(np.mean(np.array(list(attack_vecs.values())), axis=0))
    attacker = forge_profile(next(iter(profiles.values())), mean_query.reshape(1, -1))
    attacker.source_id = "attacker"
    with_attacker = {**profiles, "attacker": attacker}
    for mode in MODES:
        selected, cited = [], []
        for a in attacks:
            vec = attack_vecs[a["attack_id"]]
            dispatched = dispatch_for_mode(
                "v2" if mode == "psi" else mode, vec, with_attacker, "attack", set(),
                max_nodes=args.max_nodes, genuine_k=args.genuine_k, coarse_k=args.coarse_k, sigma=0.0, rng=np_rng,
            )
            hit = "attacker" in dispatched
            selected.append(1.0 if hit else 0.0)
            cited.append(1.0 if hit else 0.0)  # each contacted node's top passage is cited; no cross-node filter
        attack_rows.append({"mode": mode, "attack_cases": len(attacks),
                            "attacker_selected": float(np.mean(selected)),
                            "malicious_passage_cited": float(np.mean(cited)),
                            "attack_types": sorted({a["attack_type"] for a in attacks})})
        print(f"  attack {mode:<7} selected {attack_rows[-1]['attacker_selected']:.3f}", flush=True)
    return rows, attack_rows


def _genuine_ids(query_vec: np.ndarray, profiles: dict, genuine_k: int) -> list[str]:
    from baselines.cosine_router import CosineRouter

    router = CosineRouter(aggregation="max")
    router.register_sources(list(profiles.values()))
    return list(router.rank(query_vec, top_k=genuine_k).ranked_source_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs-per-engine", type=int, default=1500)
    parser.add_argument("--scan-lines", type=int, default=200_000)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--redact-all", action="store_true", help="also run redacted input through v2/psi")
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    rows, attack_rows = run(args)
    for name, data in (("privacy_cases", rows), ("attack_cases", attack_rows)):
        out = RESULTS_DIR / f"{name}_{run_id}.csv"
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
        print(f"wrote {out}")
    print(json.dumps({"privacy": rows, "attacks": attack_rows}, indent=2))


if __name__ == "__main__":
    main()
