---
tags: [literature, worksheet-import, verification-pending]
paper_no: 50
updated: 2026-09-30
---

# PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A51:N51). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Integrity, malicious sources and poisoning.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 50 |
| Citation | Wei Zou, Runpeng Geng, Binghui Wang and Jinyuan Jia (2024) |
| Paper Title | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models |
| Problem Addressed | An attacker can corrupt a RAG knowledge base by inserting a small number of malicious documents. |
| Aim / Objective | To design and evaluate knowledge-poisoning attacks in black-box and white-box RAG settings. |
| Privacy Risk Addressed | Mainly an integrity and security risk; poisoned evidence can also cause harmful information exposure. |
| Federated Component / Coordination | No federated setup; in my system a malicious client could act as the poisoning source. |
| RAG Component | Targets retrieval so that malicious text is retrieved and changes the generated answer. |
| Key Results | Reports about 90% attack success after adding five malicious texts per target question, while tested defences were weak. |
| Future Work Mentioned or Implied | Future work needs stronger detection, provenance checking and poisoning defences. |
| Relevance to My Topic | Very relevant for testing whether a bad client can hijack my router or final answer. |
| Identified Gap for My Research | It attacks a central knowledge base and does not study private multi-client routing or client trust. |
| Link | https://www.semanticscholar.org/search?q=PoisonedRAG%20Knowledge%20Corruption%20Attacks%20to%20Retrieval-Augmented%20Generation%20of%20Large%20Language%20Models&sort=relevance |
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
