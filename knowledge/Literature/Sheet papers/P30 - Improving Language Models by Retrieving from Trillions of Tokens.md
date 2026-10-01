---
tags: [literature, worksheet-import, verification-pending]
paper_no: 30
updated: 2026-09-30
---

# Improving Language Models by Retrieving from Trillions of Tokens

**Evidence status:** worksheet working note, imported without endorsing its findings. Not a new AI-written paper summary. Verify authors, title, publication, numerical results and limitations against primary full text before citing or submitting.

[Original worksheet row](https://docs.google.com/spreadsheets/d/1BWkLNfDZFp8uc6_9dodZvj2tnWzAc-uka_u_6eGhaGk/edit#gid=1678965797&range=A31:N31). Original wording is preserved below, including any errors. The recorded Semantic Scholar URL is a search link, not a verified paper record.

**Reading themes:** RAG foundations and evidence organisation.

## Original Worksheet Record

| Field | Recorded Content |
|---|---|
| No. | 30 |
| Citation | Sebastian Borgeaud, Arthur Mensch, Jordan Hoffmann, Trevor Cai, Eliza Rutherford, Katie Millican, George van den Driessche, Jean-Baptiste Lespiau, Bogdan Damoc, Aidan Clark, Diego de Las Casas, Aurelia Guy, Jacob Menick, Roman Ring, Tom Hennigan, Saffron Huang, Loren Maggiore, Chris Jones, Albin Cassirer, Andy Brock, Michela Paganini, Geoffrey Irving, Oriol Vinyals, Simon Osindero, Karen Simonyan, Jack W. Rae, Erich Elsen and Laurent Sifre (2021) |
| Paper Title | Improving Language Models by Retrieving from Trillions of Tokens |
| Problem Addressed | Very large LMs are expensive if they must memorise all knowledge internally. |
| Aim / Objective | To improve language models by retrieving from a massive external token database. |
| Privacy Risk Addressed | No privacy control; external memory could expose private or sensitive content. |
| Federated Component / Coordination | No federated component; uses a central large-scale retrieval database. |
| RAG Component | Retrieves chunks and uses them during generation with cross-attention. |
| Key Results | Retrieval helps smaller models perform closer to larger models. |
| Future Work Mentioned or Implied | Future work should improve scalable and controlled retrieval-augmented models. |
| Relevance to My Topic | Supports the idea that external knowledge reduces model memorisation needs. |
| Identified Gap for My Research | Need private distributed memory access instead of one huge central memory. |
| Link | https://www.semanticscholar.org/search?q=Improving%20Language%20Models%20by%20Retrieving%20from%20Trillions%20of%20Tokens&sort=relevance |
| Priority | Medium |

## Verify During Reading

- [ ] Resolve the canonical paper record, complete author list and version.
- [ ] Trace query, embedding, document, profile and model-update flows.
- [ ] Identify trusted components, attacker access and visible metadata.
- [ ] Record datasets, partitions, baselines, budgets and actual measured outcomes.
- [ ] Distinguish author-stated limitations from your own inferred gaps.
- [ ] Decide whether it is a direct baseline, related method or background only.
- [ ] Write your own critical summary after reading the paper.

Project comparison: [[Research gap analysis]], [[Threat model]], [[Architecture]], [[Claims ledger]]. Return to [[Paper register]].
