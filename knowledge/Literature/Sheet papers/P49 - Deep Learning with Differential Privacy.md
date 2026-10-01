---
tags: [literature, worksheet-import, verification-pending]
paper_no: 49
updated: 2026-09-30
---

# Deep Learning with Differential Privacy

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A50:N50). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** Federated architectures and training; Private retrieval and input protection.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 49 |
| Citation | Martín Abadi, Andy Chu, Ian Goodfellow, H. Brendan McMahan, Ilya Mironov, Kunal Talwar and Li Zhang (2016) |
| Paper Title | Deep Learning with Differential Privacy |
| Problem Addressed | Deep models may memorise and reveal sensitive examples from their training data. |
| Aim / Objective | To train deep networks with differential privacy using clipped noisy gradients and privacy accounting. |
| Privacy Risk Addressed | Addresses training-data and membership leakage from the trained model. |
| Federated Component / Coordination | No federated component in the paper, although DP-SGD can be combined with FL. |
| RAG Component | No RAG component. |
| Key Results | Shows deep neural networks can be trained with a measurable privacy budget at a manageable utility cost. |
| Future Work Mentioned or Implied | Future work should improve the privacy-utility trade-off and make private training more efficient. |
| Relevance to My Topic | Could be used when training my router or retriever on sensitive client data. |
| Identified Gap for My Research | Training privacy does not protect live RAG queries, document retrieval, prompts or outputs. |
| Link | https://www.semanticscholar.org/search?q=Deep%20Learning%20with%20Differential%20Privacy&sort=relevance |
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
