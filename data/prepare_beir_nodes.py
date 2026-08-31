"""Prepares real per-node document files for the MCP demo from real BEIR
corpora and MMLU (docs/06-datasets.md), rather than toy strings.

Two output directories:
- data/mcp_nodes/       — a small default set, auto-registered on backend
  startup (fast boot).
- data/mcp_nodes_extra/ — everything else. NOT auto-loaded — listed via
  GET /nodes/available and turned on individually via POST /nodes/activate,
  so "as many MCP servers as the data supports" doesn't mean a slow boot
  spawning dozens of subprocesses before the app is usable.

Corpora are read lazily (a bounded slice of lines, not the whole file) so this
is safe to run against multi-GB corpora like msmarco without loading them
into memory. Missing corpora (not yet downloaded into backend/vendor/beir/)
are skipped, not fatal — run this again after fetching more.

See this module's own docstring history / README's "MCP nodes" section for
the fetch commands.

Run: python data/prepare_beir_nodes.py
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parent.parent
BEIR_DIR = REPO_ROOT / "backend" / "vendor" / "beir"
MMLU_FILE = REPO_ROOT / "backend" / "vendor" / "mmlu" / "test.parquet"
DEFAULT_DIR = REPO_ROOT / "data" / "mcp_nodes"
EXTRA_DIR = REPO_ROOT / "data" / "mcp_nodes_extra"

DOCS_PER_NODE = 40
NODES_PER_CORPUS = 3
LOCAL_MODELS = ["toy-e5", "toy-bge", "toy-gte", "toy-ance", "toy-instructor", None]

# All 13 corpora FeB4RAG's RAGRoute config actually uses (docs/06-datasets.md).
BEIR_CORPORA = [
    "arguana", "nfcorpus", "scifact", "fiqa", "trec-covid", "scidocs",
    "webis-touche2020", "nq", "dbpedia-entity", "hotpotqa", "msmarco",
    "fever", "climate-fever",
]

# Kept small and fixed so startup stays fast regardless of how many corpora
# are actually downloaded.
DEFAULT_NODE_IDS = {"arguana_1", "arguana_2", "nfcorpus_1", "nfcorpus_2"}

MMLU_SUBJECTS = [
    "professional_law", "high_school_psychology", "elementary_mathematics",
    "philosophy", "prehistory", "moral_scenarios", "professional_medicine",
    "computer_security",
]


def _iter_corpus_lines(corpus_name: str):
    path = BEIR_DIR / corpus_name / "corpus.jsonl"
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            doc = json.loads(line)
            title = doc.get("title", "").strip()
            text = doc.get("text", "").strip()
            yield f"{title}. {text}" if title else text


def _write_spec(directory: Path, node_id: str, local_model: str | None, documents: list[str]) -> None:
    if not documents:
        return
    directory.mkdir(parents=True, exist_ok=True)
    spec = {"node_id": node_id, "local_model": local_model, "documents": documents}
    (directory / f"{node_id}.json").write_text(json.dumps(spec))
    print(f"wrote {directory.name}/{node_id}.json ({len(documents)} documents)")


def prepare_beir_corpora() -> None:
    for corpus_name in BEIR_CORPORA:
        lines = _iter_corpus_lines(corpus_name)
        safe_name = corpus_name.replace("-", "")
        for i in range(1, NODES_PER_CORPUS + 1):
            chunk = list(itertools.islice(lines, DOCS_PER_NODE))
            if not chunk:
                break  # corpus missing or exhausted
            node_id = f"{safe_name}_{i}"
            local_model = LOCAL_MODELS[(i - 1) % len(LOCAL_MODELS)]
            directory = DEFAULT_DIR if node_id in DEFAULT_NODE_IDS else EXTRA_DIR
            _write_spec(directory, node_id, local_model, chunk)


def prepare_mmlu() -> None:
    if not MMLU_FILE.exists():
        print(f"skipping MMLU: {MMLU_FILE} not found")
        return
    table = pq.read_table(MMLU_FILE).to_pandas()
    letters = ["A", "B", "C", "D"]
    for i, subject in enumerate(MMLU_SUBJECTS):
        rows = table[table["subject"] == subject].head(DOCS_PER_NODE)
        if rows.empty:
            continue
        documents = []
        for _, row in rows.iterrows():
            choice_lines = "; ".join(f"{letters[j]}) {c}" for j, c in enumerate(row["choices"]))
            answer_letter = letters[row["answer"]]
            documents.append(f"{row['question']} Choices: {choice_lines}. Answer: {answer_letter}")
        node_id = f"mmlu_{subject}"
        local_model = LOCAL_MODELS[i % len(LOCAL_MODELS)]
        _write_spec(EXTRA_DIR, node_id, local_model, documents)


def main() -> None:
    prepare_beir_corpora()
    prepare_mmlu()


if __name__ == "__main__":
    main()
