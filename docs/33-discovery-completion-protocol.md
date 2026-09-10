# Experimental discovery/completion acquisition

This is a candidate algorithm, not a verified novelty or superiority claim.
Keep source routing frozen: hybrid lexical weight .25, at most three sources.
Each request costs one of twelve passage acquisition slots, even on failure.
The generator context contains the top five passages by original-query cosine.

Seed one discovery request per selected source. Discovery returns the highest
ranked chunk from an unseen parent document. After observing five parents,
also consider completion: another chunk from an already observed parent.

Discovery priority is (source prior + sum of observed discovery similarities)
divided by (1 + discovery requests)^2. Completion priority is best observed
parent similarity times its missing-query-term fraction divided by
(1 + completion requests). Missing terms are a heuristic, not missing facts.
Ties are deterministic. Empty or invalid arms close; failures are not refunded.
Only query, published profiles and already returned content inform the policy.

## Frozen comparison

Compare equal cosine, equal parent-cap1, adaptive discovery-only, and adaptive
discovery/completion using identical source selection, embeddings and budgets.
Report document recall and normalized literal supporting-fact coverage separately.
Facts are evaluator-only. Unmatchable facts remain in the denominator; report
their prevalence. Literal coverage does not establish semantic completeness.
Previously inspected MultiHop queries make this an exploratory experiment.
Do not tune on these results and relabel them held-out.

## Scope and prior work

Source routing is reused, not the proposed contribution. The hypothesis concerns
budget allocation between document discovery and within-document completion.
Active acquisition already exists: read FLARE
https://aclanthology.org/2023.emnlp-main.495/ and IRCoT
https://aclanthology.org/2023.acl-long.557/ alongside the reading pack in doc 32.
Compare carefully with SCOUT-RAG https://arxiv.org/abs/2602.08400 before claiming
a research gap. The mechanism is currently an opt-in Python experiment; existing
HTTP/MCP production paths stay unchanged until results justify integration.
