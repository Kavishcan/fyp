---
tags: [literature, worksheet-import, verification-pending]
paper_no: 32
updated: 2026-09-30
---

# REPLUG: Retrieval-Augmented Black-Box Language Models

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A33:N33). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation; Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 32 |
| Citation | Weijia Shi, Sewon Min, Michihiro Yasunaga, Minjoon Seo, Rich James, Mike Lewis, Luke Zettlemoyer and Wen-tau Yih (2023) |
| Paper Title | REPLUG: Retrieval-Augmented Black-Box Language Models |
| Problem Addressed | Many strong LLMs are black boxes, so users cannot fine-tune or change internals. |
| Aim / Objective | To augment black-box LMs using an external tunable retriever. |
| Privacy Risk Addressed | Private retrieved context may leak to the external LLM provider. |
| Federated Component / Coordination | No federated component. |
| RAG Component | Retrieved documents are inserted into the black-box model prompt. |
| Key Results | Improves black-box LM performance with retriever tuning. |
| Future Work Mentioned or Implied | Future work should improve retriever tuning for black-box LMs. |
| Relevance to My Topic | Important if my prototype uses hosted LLM APIs. |
| Identified Gap for My Research | Need privacy controls before sending retrieved client context to black-box LLMs. |
| Link | https://www.semanticscholar.org/search?q=REPLUG%20Retrieval-Augmented%20Black-Box%20Language%20Models&sort=relevance |
| Priority | High |

## Verify During Reading

- [ ] Resolve the canonical paper record, complete author list and version.
- [ ] Trace query, embedding, document, profile and model-update flows.
- [ ] Identify trusted components, attacker access and visible metadata.
- [ ] Record datasets, partitions, baselines, budgets and actual measured outcomes.
- [ ] Distinguish author-stated limitations from your own inferred gaps.
- [ ] Decide whether it is a direct baseline, related method or background only.
- [ ] Write your own critical summary after reading the paper.

Project comparison: [[Research gap analysis]], [[Threat model]], [[Architecture]], [[Claims ledger]]. Return to [[Paper register]].
