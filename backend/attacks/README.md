# Attacks

- `a1_inversion.py` — query inversion by an honest-but-curious router
- `a2_source_inference.py` — topic-to-node map reconstruction from selection patterns
- `a3_hijack.py` — integration with Mu and Li's routing hijack

A2 is the project's primary new measurement. Build it with a strong adversary — many observed
queries, known topic taxonomy, full selection sequence — so that a low leakage
figure is evidence of safety rather than of a weak attack.
