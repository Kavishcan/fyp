# Thesis mapping

Where each repository document lands in the dissertation, and what is still
missing. The structure follows the IIT / University of Westminster template.

| Ch | Title | Source | Status |
|---|---|---|---|
| 1 | Introduction | `02-proposal.md`, `01-research-gap.md` | Drafted |
| 2 | Literature Review | Google Sheets literature matrix (55 papers) | Matrix done, prose not written |
| 3 | Methodology | — | **Missing** |
| 4 | Software Requirement Specification | `08-deployment.md` as raw material | **Missing — this is the PPRS** |
| 5 | Social, Legal, Ethical, Professional | `08-deployment.md` regulatory section | Partial |
| 6 | Design | `03-architecture.md`, `04-router-design.md` | Drafted |
| 7 | Implementation | — | Written as built |
| 8 | Testing | `05-experiments.md` | Drafted |
| 9 | Critical Evaluation | — | **Missing — needs external evaluators** |
| 10 | Conclusion | — | Written last |

## Chapter 1 subsection checklist

The template requires all of these. Present state:

- 1.1 Chapter overview — missing
- 1.2 Problem background — partial
- 1.3 Problem definition — done
- 1.4 Research motivation — partial
- 1.5 Existing work — in literature matrix
- 1.6 Research gap — done
- 1.7 Contribution to body of knowledge, split problem / research domain — done
- 1.8 Research challenges, split research / problem domain — done
- 1.9 Research questions — done
- 1.10 Research aim — done
- 1.11 Research objectives, mapped to LOs and RQs — done except LO column
- 1.12 Project scope — done
- 1.13 Hardware and software requirements — missing
- 1.14 Chapter summary — missing

## Chapter 4 — the PPRS deliverable

Required components, none yet written:

- Rich picture diagram
- Stakeholder analysis
- Selection of requirement elicitation methodologies
- Discussion and summary of findings
- Context diagram
- Use case diagram and descriptions
- Functional requirements, prioritised by MoSCoW
- Non-functional requirements

The out-of-scope list in `02-proposal.md` becomes the Won't Have requirements, and
those are excluded from testing by design in Chapter 8. State that explicitly in
both chapters so the exclusion is visible to the marker.

## Chapter 5 — SLEP

Healthcare gives this chapter real material rather than padding:

- GDPR Article 9, special category data
- Medical device regulation (EU MDR, UK MHRA, US FDA) and why this system sits
  outside it
- Data-sharing agreements and the audit-cost model
- The decoy disclosure problem: a node can ask why it received a query, and the
  honest answer is sometimes "you were a decoy". Whether that can be answered
  without undoing the privacy is an unresolved tension and should be presented as
  such.
- Dual-use: A2 is an attack. Publishing it improves defences but also describes a
  method. Address this directly.

## Chapter 9 — critical evaluation

Requires evaluation methodology, criteria, self-evaluation, **selection of
evaluators**, results, and limitations. External expert evaluation is not optional
in this template. Recruit from month 5.

## Immediate priorities

1. Chapter 4 requirements specification — blocks the PPRS
2. Chapter 3 methodology — research methodology and development methodology
3. Chapter 1 gaps: overview, background, hardware and software, summary
4. LO column on the objectives table
