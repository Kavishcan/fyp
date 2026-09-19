"""One command for the thesis' central table (docs/41 traceability).

Two uses:

    python -m eval.scorecard              # assemble from the latest result CSVs
    python -m eval.scorecard --run        # run every backing harness first, then assemble
    python -m eval.scorecard --run --only leakage feb4rag

Assembly reads the newest CSV of each kind under data/eval_results/ and
writes `scorecard_<run>.csv` plus a Markdown table with the configurations
as rows and the measured axes as columns — leakage, exposure, evidence
integrity, routing quality, answer accuracy and cost — each cell carrying
the docs note it comes from. It computes nothing new and never changes a
number: if a harness has not been run, the cell is blank and says so.

`--run` executes the harnesses in the order below with the arguments each
docs note records, so the reproduce commands in docs/33–42 and this file
are the same commands. Long ones (answer quality needs Ollama; transport
spawns 30 MCP processes) can be skipped with --only.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import subprocess
import sys
import time
from pathlib import Path

from eval.sweep import RESULTS_DIR

# name -> (module, args, docs note)
HARNESSES: dict[str, tuple[str, list[str], str]] = {
    "leakage": ("eval.run_leakage", ["--conditions", "random", "broadcast", "cosine@g", "cosine@K",
                                     "sticky_decoys", "random_any", "cells_1x4", "oracle"], "docs/39–40"),
    "healthcare": ("eval.run_healthcare", [], "docs/40"),
    "privacy_cases": ("eval.run_privacy_cases", [], "docs/37, 40"),
    "feb4rag": ("eval.run_feb4rag", [], "docs/36"),
    "a3_trust": ("eval.run_v2_a3", ["--trust-weight", "0.5"], "docs/42"),
    "transport": ("eval.run_mcp_transport", ["--node-counts", "30", "--modes", "legacy", "v2", "psi",
                                             "--n-queries", "16", "--persistent"], "docs/37"),
    "answer_quality": ("eval.run_answer_quality", ["--per-subset", "30", "--distractors", "fiqa", "arguana",
                                                   "scidocs", "dbpedia-entity", "webis-touche2020", "--max-nodes", "4",
                                                   "--top-per-node", "1", "--conditions", "closed_book", "psi",
                                                   "broadcast", "psi_rerank", "psi_cells"], "docs/38"),
}


def latest(prefix: str, *, exclude: tuple[str, ...] = ("per_seed", "per_question", "per_corpus")) -> Path | None:
    files = [Path(f) for f in glob.glob(str(RESULTS_DIR / f"{prefix}_*.csv")) if not any(x in f for x in exclude)]
    return max(files, key=os.path.getmtime) if files else None


def rows(path: Path | None) -> list[dict]:
    if path is None:
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle))


def merged(prefix: str, key: str, *, exclude: tuple[str, ...] = ("per_seed", "per_question", "per_corpus")) -> tuple[list[dict], list[Path]]:
    """All result files of a kind, newest wins per `key` value — so a partial
    re-run (e.g. only the cells conditions) does not blank the conditions it
    did not repeat. Returns the rows and the files that contributed."""
    files = sorted((Path(f) for f in glob.glob(str(RESULTS_DIR / f"{prefix}_*.csv")) if not any(x in f for x in exclude)),
                   key=os.path.getmtime)
    table: dict[str, dict] = {}
    used: list[Path] = []
    for f in files:
        for r in rows(f):
            if r.get(key) is not None:
                table[r[key]] = r
                if f not in used:
                    used.append(f)
    return list(table.values()), used


def pick(table: list[dict], key: str, value: str, column: str) -> float | None:
    for r in table:
        if r.get(key) == value and r.get(column) not in (None, "", "nan"):
            try:
                v = float(r[column])
                return None if math.isnan(v) else v
            except ValueError:
                return None
    return None


def assemble() -> tuple[list[dict], dict[str, str]]:
    leak, leak_files = merged("leakage", "condition")
    health, health_files = merged("healthcare", "condition")
    priv, priv_files = merged("privacy_cases", "mode")          # (mode, input) — see priv_row
    attack, attack_files = merged("attack_cases", "mode")       # refined below by evidence_top_k
    feb, feb_files = merged("feb4rag", "mode")
    ans, ans_files = merged("answer_quality", "condition")
    # answer_quality rows are per (condition, subset); the table wants "all".
    ans = [r for r in {(r["condition"], r.get("subset")): r for r in sum((rows(f) for f in ans_files), [])}.values()
           if r.get("subset") == "all"]
    tr, tr_files = merged("mcp_transport", "mode")
    # privacy/attack rows are keyed by two fields; re-merge on the pair.
    priv = list({(r["mode"], r.get("input")): r for r in sum((rows(f) for f in priv_files), [])}.values())
    attack = list({(r["mode"], str(r.get("evidence_top_k"))): r for r in sum((rows(f) for f in attack_files), [])}.values())
    tr = [r for r in tr if "persistent" in r.get("transport", "")] or tr

    # A3: the trust-weight column exists only in files written after docs/42;
    # older files are gate-only runs and supply the w=0 baseline via `none`.
    a3_files = sorted((Path(f) for f in glob.glob(str(RESULTS_DIR / "v2_a3_*.csv")) if "per_seed" not in f), key=os.path.getmtime)
    a3: dict[str, dict] = {}
    for f in a3_files:
        for r in rows(f):
            if r.get("condition") == "none":
                a3["none"] = r
            elif r.get("condition") == "trust" and "trust_weight" in r:
                a3[f"w={float(r['trust_weight']):g}"] = r
    src = {"leakage": leak_files, "healthcare": health_files, "privacy_cases": priv_files, "attack_cases": attack_files,
           "feb4rag": feb_files, "answer_quality": ans_files, "mcp_transport": tr_files, "v2_a3": a3_files}

    ranking = pick(feb, "mode", "profile_ranking", "ndcg@1_mean")
    mrr = pick(feb, "mode", "profile_ranking", "mrr_best_mean")

    def config(name, leak_cond, health_cond, priv_mode, priv_input, attack_mode, attack_topk, feb_mode, ans_cond, tr_mode):
        return {
            "configuration": name,
            "topic_attack_feb4rag": pick(leak, "condition", leak_cond, "topic_engine_acc_mean") if leak_cond else None,
            "source_attack_feb4rag": pick(leak, "condition", leak_cond, "source_attack_acc_mean") if leak_cond else None,
            "topic_attack_healthcare": pick(health, "condition", health_cond, "topic_acc_mean") if health_cond else None,
            "sensitive_values_exposed": pick(priv, "input", priv_input, "sensitive_values_exposed_to_nodes") if priv_mode else None,
            "planted_passage_cited": pick(attack, "evidence_top_k", attack_topk, "malicious_passage_cited") if attack_mode else None,
            "graded_gain_feb4rag": pick(leak, "condition", leak_cond, "captured_gain_mean") if leak_cond else None,
            "ndcg@1_profile_ranking": ranking if feb_mode else None,
            "mrr_profile_ranking": mrr if feb_mode else None,
            "answer_accuracy_mirage": pick(ans, "condition", ans_cond, "accuracy") if ans_cond else None,
            "contact_ms_persistent": pick(tr, "mode", tr_mode, "contact_ms") if tr_mode else None,
            "request_bytes_per_query": pick(tr, "mode", tr_mode, "request_bytes") if tr_mode else None,
        }

    def priv_row(mode, inp):
        # privacy_cases rows are keyed by (mode, input); pick by mode first.
        for r in priv:
            if r.get("mode") == mode and r.get("input") == inp:
                return r
        return None

    def exposed(mode, inp="augmented"):
        r = priv_row(mode, inp)
        return float(r["sensitive_values_exposed_to_nodes"]) if r else None

    def cited(mode, topk):
        for r in attack:
            if r.get("mode") == mode and str(r.get("evidence_top_k")) == str(topk):
                return float(r["malicious_passage_cited"])
        return None

    table = [
        config("normal cosine router (top-k, no decoys)", "cosine@K", "cosine@K", "legacy", "augmented", "legacy", "all", True, None, "legacy"),
        config("+ topic-stable decoys (v2 pattern)", "sticky_decoys", "sticky_decoys", "v2", "augmented", "v2", "all", True, None, "v2"),
        config("+ PSI dispatch", "sticky_decoys", "sticky_decoys", "psi", "augmented", "psi", "all", True, "psi", "psi"),
        config("+ anonymity cells", "cells_1x4", "cells_1x4", "psi", "augmented", "psi", "all", True, "psi_cells", "psi"),
        config("+ cross-node evidence rerank (top-2)", "cells_1x4", "cells_1x4", "psi", "augmented", "psi", "2", True, "psi_cells", "psi"),
        config("broadcast (reference)", "broadcast", "broadcast", None, None, None, None, True, "broadcast", None),
        config("oracle (reference)", "oracle", "oracle", None, None, None, None, True, None, None),
    ]
    for r in table:
        mode = {"normal cosine router (top-k, no decoys)": "legacy", "+ topic-stable decoys (v2 pattern)": "v2"}.get(r["configuration"], "psi")
        if r["configuration"].startswith(("broadcast", "oracle")):
            continue
        r["sensitive_values_exposed"] = exposed(mode)
        r["planted_passage_cited"] = cited(mode, "2" if "rerank" in r["configuration"] else "all")
    trust, base = a3.get("w=0.5"), a3.get("none")
    extra = {
        "a3_attacker_selected_no_trust": float(base["attacker_selection_rate_mean"]) if base else None,
        "a3_honest_recall_no_trust": float(base["honest_source_recall_mean"]) if base else None,
        "a3_attacker_selected_trust_w0.5": float(trust["attacker_selection_rate_mean"]) if trust else None,
        "a3_honest_recall_trust_w0.5": float(trust["honest_source_recall_mean"]) if trust else None,
    }
    table.append({"configuration": "+ trust ranking term (w=0.5) vs forged-profile attacker (docs/42)",
                  **{k: None for k in table[0] if k != "configuration"}, **extra})
    sources = {k: (", ".join(f.name for f in v) if v else "MISSING — run the harness") for k, v in src.items()}
    return table, sources


def to_markdown(table: list[dict], sources: dict[str, str]) -> str:
    cols = [c for c in table[0] if c != "configuration"]
    for r in table:
        for c in cols:
            r.setdefault(c, None)
    extra = [c for c in table[-1] if c not in table[0]]
    lines = ["| configuration | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for r in table:
        lines.append("| " + r["configuration"] + " | " + " | ".join(
            "" if r.get(c) is None else f"{r[c]:.3f}" if abs(r[c]) < 100 else f"{r[c]:,.0f}" for c in cols) + " |")
    if extra:
        lines.append("")
        lines.append("| " + " | ".join(extra) + " |")
        lines.append("|" + "---:|" * len(extra))
        lines.append("| " + " | ".join("" if table[-1].get(c) is None else f"{table[-1][c]:.3f}" for c in extra) + " |")
    lines += ["", "Sources (newest CSV of each kind):", ""] + [f"- {k}: `{v}`" for k, v in sources.items()]
    lines += ["", "Blank = not measured for that configuration or harness not run. Numbers are copied, not recomputed;",
              "each column's definition and caveats are in the docs note the harness records (docs/36–42)."]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="store_true", help="run the backing harnesses before assembling")
    parser.add_argument("--only", nargs="+", choices=list(HARNESSES), help="with --run: subset of harnesses")
    args = parser.parse_args()

    if args.run:
        for name in (args.only or list(HARNESSES)):
            module, margs, note = HARNESSES[name]
            print(f"== {name} ({note}): python -m {module} {' '.join(margs)}", flush=True)
            started = time.perf_counter()
            result = subprocess.run([sys.executable, "-m", module, *margs], cwd=Path(__file__).resolve().parent.parent)
            print(f"== {name} exit {result.returncode} in {time.perf_counter() - started:.0f}s", flush=True)
            if result.returncode:
                print(f"== {name} FAILED; continuing with the others", flush=True)

    table, sources = assemble()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    cols = list(dict.fromkeys(k for r in table for k in r))
    with (RESULTS_DIR / f"scorecard_{run_id}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        writer.writerows(table)
    md = to_markdown(table, sources)
    (RESULTS_DIR / f"scorecard_{run_id}.md").write_text(md)
    print(md)
    print(f"\nwrote {RESULTS_DIR / f'scorecard_{run_id}.csv'} and .md")


if __name__ == "__main__":
    main()
