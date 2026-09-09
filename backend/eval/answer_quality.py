"""Strict offline answer scoring. Never generates or fabricates predictions."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import string

import numpy as np

from eval.run_smart_pilot import fingerprint
from eval.run_candidate_study import save_json


def normalize_answer(text):
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", text).split())


def answer_metrics(prediction, references):
    if not isinstance(prediction, str) or not references or any(not isinstance(r, str) for r in references):
        raise ValueError("prediction and nonempty reference list must contain strings")
    pred = normalize_answer(prediction)
    scores = []
    for reference in references:
        gold = normalize_answer(reference)
        a, b = pred.split(), gold.split()
        common = sum((Counter(a) & Counter(b)).values())
        f1 = float(a == b) if not a or not b else 2 * common / (len(a) + len(b))
        scores.append((float(pred == gold), f1))
    return dict(exact_match=max(s[0] for s in scores), token_f1=max(s[1] for s in scores))


def unique_rows(path):
    result = {}
    with path.open() as f:
        for row in map(json.loads, f):
            key = row["query_id"], row["method"]
            if key in result:
                raise ValueError("duplicate query/method row")
            result[key] = row
    if not result:
        raise ValueError("empty input")
    return result


def score(study, predictions_path, generation_manifest, output):
    manifest = json.loads((study / "manifest.json").read_text())
    if not manifest["completed"]:
        raise ValueError("incomplete prepared study")
    for name in ("answer-requests.jsonl", "answer-references.jsonl"):
        if fingerprint(study / name) != manifest["artifacts"][name]:
            raise ValueError("prepared answer inputs changed")
    generation = json.loads(generation_manifest.read_text())
    for name in ("model", "provider", "temperature", "max_output_tokens", "requests_sha256"):
        if name not in generation:
            raise ValueError(f"generation manifest missing {name}")
    if not generation["model"] or not generation["provider"] or generation["max_output_tokens"] <= 0:
        raise ValueError("invalid generation configuration")
    if generation["requests_sha256"] != manifest["artifacts"]["answer-requests.jsonl"]:
        raise ValueError("generation request fingerprint mismatch")
    requests = unique_rows(study / "answer-requests.jsonl")
    references = unique_rows(study / "answer-references.jsonl")
    predictions = unique_rows(predictions_path)
    if set(requests) != set(references) or set(predictions) != set(references):
        raise ValueError("predictions must cover exactly every prepared query/method, including failures")
    rows = []
    for key in sorted(references):
        pred = predictions[key]
        if pred.get("error"):
            metrics = dict(exact_match=0., token_f1=0.)
        else:
            metrics = answer_metrics(pred["answer"], references[key]["answers"])
        rows.append(dict(query_id=key[0], method=key[1], failed=int(bool(pred.get("error"))), **metrics))
    groups = defaultdict(list)
    for row in rows:
        groups[row["method"]].append(row)
    summary = {method: dict(cases=len(group), failures=sum(r["failed"] for r in group),
                            **{metric: float(np.mean([r[metric] for r in group]))
                               for metric in ("exact_match", "token_f1")}) for method, group in groups.items()}
    if output.exists():
        raise ValueError("refusing to overwrite answer scores")
    save_json(output, dict(status="scored supplied predictions; authenticity requires run audit", generation=generation,
                          predictions_sha256=fingerprint(predictions_path),
                          generation_manifest_sha256=fingerprint(generation_manifest), summary=summary, rows=rows,
                          limitation="Lexical EM/F1 only; not semantic correctness, faithfulness or publication evidence."))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", required=True, type=Path)
    p.add_argument("--predictions", required=True, type=Path)
    p.add_argument("--generation-manifest", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(score(a.study, a.predictions, a.generation_manifest, a.output), indent=2))
