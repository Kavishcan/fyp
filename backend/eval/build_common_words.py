"""Build privacy/data/common_words.txt.gz for the safe_harbor de-identifier (docs/54).

A word that clinical writers use in lower case is a common word; a town or a
person's name essentially never is. The list holds every alphabetic token
seen in ALL-lower-case at least `--min-count` times in PMC-Patients reports.
The reports used by eval/run_deid_benchmark.py (the first 2 x 400 + 1,000
of its seeded shuffle, plus its last 1,000) are excluded, so the benchmark
text never shapes the list.

Run: python -m eval.build_common_words
"""
from __future__ import annotations

import argparse
import gzip
import random
import re
from collections import Counter
from pathlib import Path

from eval.run_deid_benchmark import CSV_PATH

OUT = Path(__file__).resolve().parents[1] / "privacy" / "data" / "common_words.txt.gz"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=int, default=30000)
    parser.add_argument("--min-count", type=int, default=3)
    args = parser.parse_args()
    import pandas as pd

    df = pd.read_csv(CSV_PATH, usecols=["patient"])
    pool = [t for t in df["patient"].tolist() if isinstance(t, str) and 400 < len(t) < 6000]
    random.Random(7).shuffle(pool)                      # the benchmark's shuffle
    usable = pool[3000:-1000][: args.reports]
    counts = Counter()
    for text in usable:
        counts.update(w for w in re.findall(r"\b[a-z][a-z']+\b", text))
    words = sorted(w for w, c in counts.items() if c >= args.min_count)
    with gzip.open(OUT, "wt", encoding="utf-8") as h:
        h.write("\n".join(words))
    print(f"{len(words)} common words from {len(usable)} reports -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
