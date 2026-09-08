# Attack evaluation

- a1_inversion.py: embedding-only query reconstruction experiments.
- a2_source_inference.py: inference from observable selection patterns.
- a3_hijack.py: routing-hijacking integration.

These are experiment components, not evidence that the smart router resists
attacks. New smart-mode evaluation must be run explicitly. A1 does not protect
against the live coordinator, which already receives the raw question.

A2 needs a stated observer, held-out queries and topic knowledge independent of
the test relevance answer key. Fewer recipients do not imply lower A2 success.

A3 must test fabricated profiles, matching bait, cold starts and source changes.
Coordinator-embedded consistency is not authenticated honesty. See
[experiment plan](../../docs/05-experiments.md).
