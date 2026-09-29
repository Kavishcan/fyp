---
tags: [hub]
---

# FedSafeRouter — knowledge graph

**Title:** *Privacy-Aware Source Routing for Federated RAG: Mitigating Query and Access-Pattern Leakage*

Start here, then open the **graph view** (Ctrl/Cmd+G). Colours: concepts, mechanisms, attacks, experiments, results, code, literature, claims.

| Map | What it covers |
|---|---|
| [[Research question]] | the question and the two leaks |
| [[Threat model]] | who is trusted, who is not, what each party sees |
| [[Architecture]] | the recommended pipeline end to end |
| [[Mechanisms index]] | every privacy / retrieval mechanism built |
| [[Attacks index]] | every attack measured or found |
| [[Experiments index]] | datasets, harnesses, splits |
| [[Results index]] | docs/30–52 as results |
| [[Claims ledger]] | what may be claimed, with numbers and scope |
| [[Code map]] | modules and what they do |
| [[Literature map]] | prior work and how this project relates |
| [[Design timeline]] | how the design evolved and why |
| [[Future work]] | decided out of scope |

**One-sentence result:** [[Blind unlock]] is the only compared design in which no hospital receives the question **and** the contact pattern stays at the [[Inference floor]] — on three [[Hospital splits]] and over five-question sessions — at 97–98% of a local [[HyFedRAG]]-style baseline's retrieval at P = 24.
