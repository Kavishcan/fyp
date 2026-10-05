---
tags: [hub, research-support]
updated: 2026-10-05
---

# Dataset Register

| Dataset | Actual Use | Local Experimental Scope | Real Source |
|---|---|---|---|
| PMC-Patients | Main patient-to-patient retrieval and partition experiments | 5,000 summaries, 986 queries, eight simulated owner nodes; k-means, Dirichlet, random | [Hugging Face](https://huggingface.co/datasets/zhengyun21/PMC-Patients) |
| BEIR | Source documents, relevance labels and source profiles; medical and distractor stores | Corpora vary by experiment; MIRAGE uses nfcorpus, scifact, trec-covid plus fiqa, arguana, scidocs | [Official repository](https://github.com/beir-cellar/beir) |
| FeB4RAG | Federated source-selection benchmark; published ranking/qrel data | 13 of 16 engines available locally; 785 routing requests, 640 leakage cases | [Official repository](https://github.com/ielab/FeB4RAG) |
| MIRAGE | Medical question/answer evaluation, not a hospital document collection | 150 questions, 30 each from five subsets; local Qwen3.5-9B | [Official repository](https://github.com/gzxiong/MIRAGE) |
| Fictional privacy/attack fixtures | Known identifiers and malicious-source cases | 200 privacy cases plus 60 attack cases in earlier harnesses; separate de-id canaries | [Project data repository](https://github.com/Kavishcan/fedrag-dataset/tree/main/data/processed/privacy) |
| MedRAG Textbooks | Natural-source federation (18 textbooks) | Downloaded 2026-10-02 (~204 MB), not yet run | [Hugging Face](https://huggingface.co/datasets/MedRAG/textbooks) |
| MTSamples | Real transcribed clinical reports, 40 specialties | Downloaded (16 MB, Apache-2.0 mirror), not yet run | [Hugging Face](https://huggingface.co/datasets/harishnair04/mtsamples) |
| TREC-COVID | Second retrieval benchmark, real queries | In `vendor/beir/trec-covid/` (duplicate in `vendor/trec_covid/`), not yet run as baseline comparison | [Hugging Face](https://huggingface.co/datasets/BeIR/trec-covid) |
| MedQA-USMLE | Downloaded for answer tests, **unused** (generation out of scope) | 17 MB | [Hugging Face](https://huggingface.co/datasets/GBaker/MedQA-USMLE-4-options) |
| MultiHop-RAG | Prepared supporting dataset | Not evidence for current blind retrieval results | [Official repository](https://github.com/yixuantt/MultiHop-RAG) |

**MIRAGE subsets**
- BioASQ: biomedical QA tasks; use the benchmark's supplied sampled questions.
- MedMCQA: medical multiple-choice questions.
- MedQA: medical examination-style questions.
- MMLU-medical: selected medical subject questions from MMLU.
- PubMedQA: questions associated with biomedical literature.

The MIRAGE benchmark is a question set. Current knowledge sources are sampled BEIR corpora, not the full MedRAG document stores. PMC nodes are simulated partitions of public case reports, not eight real hospitals.

Credentialed sources (MIMIC-IV-Note, PhysioNet de-id gold standard, n2c2) were deliberately not used; the user chose open data only.

Public availability does not mean free of sensitive information or unrestricted licensing. Fictional identifiers give measurable ground truth; they do not establish clinical anonymisation. Follow original dataset licences and access conditions.

More detail: [[PMC-Patients]], [[MIRAGE]], [[FeB4RAG]], [[BEIR healthcare federation]], [[Dataset strategy]].

## Implementation / Experiment Sources

- [backend/eval/run_hyfedrag_compare.py](../backend/eval/run_hyfedrag_compare.py)
- [backend/eval/run_answer_quality.py](../backend/eval/run_answer_quality.py)
- [docs/06-datasets.md](../docs/06-datasets.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
