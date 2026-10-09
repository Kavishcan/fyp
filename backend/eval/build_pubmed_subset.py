"""Build the PubMed corpus subset for the C-FedRAG-style evaluation (docs/57).

C-FedRAG (Addison et al., 2024, p.6) retrieved from MedRAG's PubMed corpus,
keeping the top 10,000 scoring snippets per question set. The full MedRAG
PubMed corpus (23.9M snippets) is far above the project's 500 MB download
limit, so this script builds a comparable subset from NCBI's public
E-utilities API (no account or key):

- source abstracts: the PubMed IDs MIRAGE lists for every PubMedQA and
  BioASQ question (the abstract the question was written from);
- distractors: for each question, the top `--per-question` PubMed hits for
  the question text (relevance sort), i.e. topically close abstracts that do
  not answer it; questions with fewer hits (PubMed ANDs a sentence's terms)
  get a second search on their content words joined with OR. 20 per question gives about 10,000 per question set, the
  size C-FedRAG used.

One snippet per abstract, title + abstract text, as in MedRAG's PubMed
corpus. Abstracts keep their conclusion section (MedRAG does too), so the
source abstract often states the answer; every retrieval condition sees the
same corpus. Abstracts without text are dropped.

Output: backend/vendor/pubmed_subset/pubmed_subset.jsonl (id, pmid, title,
content, source = "gold" | "distractor", questions) and manifest.json.
Search results are cached in esearch_cache.json, so an interrupted run
resumes. NCBI allows 3 requests per second without a key; the script waits
0.4 s between requests.

Run: python -m eval.build_pubmed_subset
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from eval.sweep import REPO_ROOT

MIRAGE = REPO_ROOT / "backend" / "vendor" / "ragroute" / "data" / "benchmark" / "MIRAGE.json"
OUT_DIR = REPO_ROOT / "backend" / "vendor" / "pubmed_subset"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PAUSE_S = 0.4
STOPWORDS = {"what", "which", "does", "with", "from", "that", "this", "there", "their", "they", "have", "been",
             "were", "when", "where", "into", "than", "then", "them", "these", "those", "about", "after", "before",
             "being", "between", "could", "should", "would", "while", "whether", "other", "patients", "patient",
             "associated", "effect", "effects", "role", "used", "using", "common", "most", "more", "less"}


def _get(url: str, params: dict, retries: int = 4) -> bytes:
    query = urllib.parse.urlencode({**params, "tool": "fedsaferag-fyp"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=60) as resp:
                data = resp.read()
            time.sleep(PAUSE_S)
            return data
        except Exception:  # network hiccup or 429: back off and retry
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def esearch(term: str, retmax: int) -> list[str]:
    data = json.loads(_get(f"{EUTILS}/esearch.fcgi", {"db": "pubmed", "term": term, "retmax": retmax,
                                                         "sort": "relevance", "retmode": "json"}))
    return data.get("esearchresult", {}).get("idlist", [])


def efetch(pmids: list[str]) -> dict[str, tuple[str, str]]:
    """pmid -> (title, abstract) for the abstracts that have text."""
    root = ET.fromstring(_get(f"{EUTILS}/efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}))
    out = {}
    for art in root.iter("PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID")
        title = "".join(art.find(".//ArticleTitle").itertext()).strip() if art.find(".//ArticleTitle") is not None else ""
        parts = []
        for node in art.findall(".//Abstract/AbstractText"):
            text = "".join(node.itertext()).strip()
            if text:
                label = node.get("Label")
                parts.append(f"{label.title()}: {text}" if label else text)
        if pmid and parts:
            out[pmid] = (title, " ".join(parts))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subsets", nargs="+", default=["pubmedqa", "bioasq"])
    parser.add_argument("--per-question", type=int, default=20, help="distractor hits per question")
    parser.add_argument("--batch", type=int, default=200, help="PubMed IDs per efetch request")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mirage = json.loads(MIRAGE.read_text())
    questions = [(s, qid, item) for s in args.subsets for qid, item in mirage[s].items()]
    gold: dict[str, set[str]] = {}
    for s, qid, item in questions:
        for p in item.get("PMID", []):
            gold.setdefault(str(p), set()).add(f"{s}:{qid}")
    print(f"{len(questions)} questions, {len(gold)} source PubMed IDs", flush=True)

    cache_path = OUT_DIR / "esearch_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    t0 = time.perf_counter()
    for i, (s, qid, item) in enumerate(questions):
        key = f"{s}:{qid}"
        if key in cache:
            continue
        cache[key] = esearch(item["question"], args.per_question)
        if (i + 1) % 50 == 0:
            cache_path.write_text(json.dumps(cache))
            print(f"  searched {i + 1}/{len(questions)} ({time.perf_counter() - t0:.0f}s)", flush=True)
    cache_path.write_text(json.dumps(cache))
    # A full-sentence query is matched as AND of its terms, so many questions
    # return few hits. Second pass for those: the question's content words
    # joined with OR, still relevance-sorted (Best Match ranks abstracts that
    # match more of the words first).
    for i, (s, qid, item) in enumerate(questions):
        key = f"{s}:{qid}"
        if len(cache[key]) >= args.per_question or f"{key}|or" in cache:
            continue
        words = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]+", item["question"])
                 if len(w) > 3 and w.lower() not in STOPWORDS]
        cache[f"{key}|or"] = esearch(" OR ".join(dict.fromkeys(words)), args.per_question) if words else []
        if (i + 1) % 50 == 0:
            cache_path.write_text(json.dumps(cache))
            print(f"  OR-searched up to {i + 1}/{len(questions)} ({time.perf_counter() - t0:.0f}s)", flush=True)
    cache_path.write_text(json.dumps(cache))

    hits: dict[str, set[str]] = {}
    for key, ids in cache.items():
        key = key.split("|")[0]
        for p in ids:
            hits.setdefault(p, set()).add(key)
    wanted = sorted(set(gold) | set(hits), key=int)
    print(f"{len(wanted)} unique PubMed IDs to fetch ({len(set(hits) - set(gold))} distractor-only)", flush=True)

    records: dict[str, tuple[str, str]] = {}
    for start in range(0, len(wanted), args.batch):
        records.update(efetch(wanted[start:start + args.batch]))
        print(f"  fetched {min(start + args.batch, len(wanted))}/{len(wanted)} ({len(records)} with abstracts)", flush=True)

    out_path = OUT_DIR / "pubmed_subset.jsonl"
    n_gold = n_dist = 0
    with open(out_path, "w") as handle:
        for p in wanted:
            if p not in records:
                continue
            title, content = records[p]
            source = "gold" if p in gold else "distractor"
            n_gold += source == "gold"
            n_dist += source == "distractor"
            handle.write(json.dumps({"id": f"pubmed_{p}", "pmid": p, "title": title, "content": content,
                                     "source": source, "questions": sorted(gold.get(p, set()))}) + "\n")
    missing_gold = sorted(set(gold) - set(records), key=int)
    manifest = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "subsets": args.subsets, "questions": len(questions),
                "per_question": args.per_question, "gold_pmids": len(gold), "gold_with_abstract": n_gold,
                "gold_missing": missing_gold, "distractors": n_dist, "snippets": n_gold + n_dist,
                "source": "NCBI E-utilities esearch (relevance) + efetch", "bytes": out_path.stat().st_size}
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: v for k, v in manifest.items() if k != "gold_missing"}, indent=2))
    print(f"gold abstracts missing text: {len(missing_gold)}; wrote {out_path}")


if __name__ == "__main__":
    main()
