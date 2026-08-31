"""Generation interface.

docs/03-architecture.md and docs/02-proposal.md specify generation on a LOCAL
open-weight model, precisely so retrieved passages and the query never leave
the trust boundary — that is what keeps prompt/output leakage out of scope.

The concrete generators in this package (OpenAI, Gemini) are a deliberate,
documented departure from that design, added for the demo API/frontend, not
for the research pipeline. Using them means retrieved passages leave the
trust boundary to a third-party provider. Do not use their output as evidence
for any privacy claim the thesis makes — see the README's Generation section.

Any generator, local or remote, satisfies this same interface, so a real
local-model implementation can be dropped in later (backend/nodes or a new
backend/generation/local.py) without touching backend/api/state.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

FIXED_PROMPT_TEMPLATE = """Answer the question using only the passages below. \
If the passages don't contain the answer, say so plainly rather than guessing.

Question: {question}

Passages:
{passages}

Answer:"""


def build_prompt(question: str, passages: list[str]) -> str:
    """One fixed template, used by every provider — no per-provider prompt
    engineering, matching the "keep generation dumb" rule in docs/02-proposal.md.
    """
    numbered = "\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages))
    return FIXED_PROMPT_TEMPLATE.format(question=question, passages=numbered or "(none returned)")


class Generator(ABC):
    name: str

    @abstractmethod
    def generate(self, question: str, passages: list[str]) -> str:
        """Return a generated answer grounded in `passages`."""
