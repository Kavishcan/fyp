# Roadmap

Nine months. Writing runs in parallel, not at the end.

| Month | Build | Write |
|---|---|---|
| 1 | Load FeB4RAG. Baselines 0, 1, 2. Recall@K table. | Literature review |
| 2 | Threat model. Instrumentation. A1 and A2 against the unprotected router. | Finish literature review |
| 3 | Noisy profiles + query perturbation. **Noise pilot.** First privacy/utility curve. | Methodology |
| 4 | Anonymity sets. Full cost instrumentation. | Methodology |
| 5 | Compose with the trust defence. Run A3. Robustness results. | Paper intro and related work |
| 6 | MultiHop-RAG generalisation. Ablation ladder. Scaling to 100/300/1000. | Results drafting |
| 7 | Freeze code. Reproducibility pass. Release repo. | **Write and submit paper** |
| 8 | Buffer for reviewer-triggered experiments | Thesis results and discussion |
| 9 | — | Full draft, revisions, defence prep |

Month 8 as buffer is not padding. Something will break in month 4 or 5.

## Week 1 milestone, ahead of everything else

Clone the routing-hijack reference implementation and confirm it runs.

RQ3 depends on it entirely. If it is broken, fall back to RQ1 and RQ2 — same
build, narrower story. Two days spent now saves five months of exposure.

Repo: https://github.com/Junjie-Mu/routing-hijacking-fedrag

## Paper vs thesis

Not the same document.

**Paper** (6 to 9 pages): RQ1 and RQ2, FeB4RAG only, ablation ladder, A1 to A3.

**Thesis**: the paper plus the full 53-paper review, MultiHop-RAG generalisation,
scaling study, and the negative results cut from the paper.

Target a privacy or trust-in-NLP workshop, or an IR conference short paper track.
Check current deadlines — they shift year to year. A March submission window fits
this timeline. Do not aim for a main-track long paper on a first attempt with a
nine-month clock.

## Risk register

| Risk | Trigger | Mitigation |
|---|---|---|
| Distance-preserving noise collapses recall before privacy gain is meaningful | Month 3 pilot | Fall back to anonymity sets only. Weaker, still publishable. |
| A2 shows leakage is small | Month 2 | Design A2 with a strong adversary so the null result is informative |
| Trust-defence repo does not run | Week 1 | Drop RQ3, keep RQ1 and RQ2 |
| FeB4RAG cross-domain split makes routing too easy | Month 1 | Add same-domain hard split from a single BEIR dataset |
| Scope creep back toward end-to-end pipeline privacy | Any time | Re-read the scope boundaries in the proposal |

## Standing task

Set an arXiv alert for FedRAG routing. Two of the papers that define this gap
appeared within six months of writing. Re-run the literature check before the
proposal deadline and again before paper submission.
