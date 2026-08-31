# Data

Prep scripts and node partitioning. Raw data is gitignored.

- FeB4RAG — primary routing benchmark, 16 clients. Precomputed pools support
  evaluation; document-derived profiles require the relevant underlying BEIR
  corpora or verified published artifacts.
- MultiHop-RAG — external validation, 49 clients
- MedQA-USMLE — healthcare case study, ~150 questions
- BEIR single-dataset hard split — same-domain difficulty control
- Synthetic privacy and attack set

Every empirical claim about these datasets must be verified by inspection, not
assumed. See the Dataset Comparison Matrix.
