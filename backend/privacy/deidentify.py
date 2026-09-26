"""Node-side de-identification, applied ONCE at index time (docs/44).

Before this module the node redacted only what it embedded
(nodes/profile.redact_pii inside embed_documents): the vectors were clean,
but the TEXT the node served — legacy/smart retrieve results, v2 results,
and the PSI envelopes — was the raw document. Any PII in a hospital's corpus
reached every client the node served. Now the node de-identifies its
documents before anything else sees them, so embeddings, the published
profile (description/topics, centroids), the cluster table, the envelopes
and every retrieve result are built from the same de-identified text. There
is no path from the raw document to the wire.

Three layers, all local, no downloads:

1. Structured identifiers (regex): email, URL, IPv4, phone, SSN, card-like
   digit runs, dates, record identifiers (MRN/ID patterns such as
   "MRN 1234567", "TEST-0001", "NHS 943 476 5919").
2. Names with a cue (rules): honorifics (Mr/Mrs/Ms/Dr/Prof/Patient ...) and
   self-identification ("my name is", "patient named", "I am").
3. A node-supplied registry (`known_identifiers`): the institution's own
   list of patient/staff names and ids — the realistic source of truth a
   hospital has. Matched case-insensitively as whole words.

What this is NOT: a validated clinical de-identifier. It does not detect a
bare name with no cue and not in the registry, free-text addresses, or
quasi-identifiers (rare diagnosis + age + town). A deployment must put a
validated tool (Presidio, Philter, the institution's own) at this same
point; `Deidentifier.backend` is where it plugs in. The measurement in
docs/44 states per-type recall so the gap is a number, not a promise.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable

# Order matters: longer / more specific patterns first so their spans are
# replaced before a broader pattern (phone) sees the digits.
_STRUCTURED: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("URL", re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.I)),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # A labelled identifier: the label is case-insensitive, the value must be
    # digits (optionally with an upper-case prefix) so ordinary words after
    # "record" or "id" are never swallowed.
    ("ID", re.compile(r"\b(?i:MRN|NHS|SSN|ID|Patient ID|Record|Hospital No)\.?\s*(?:(?i:no|number|is)\.?\s*|#\s*|:\s*)?"
                      r"(?:[A-Z]{1,4}[- ]?)?\d[\d -]{2,14}\d\b")),
    # NOTE: no bare "ABC-123" rule. In biomedical text that shape is a
    # compound, drug or cell line (PCB-153, MB-231, GS-9620) far more often
    # than a person; an institution adds its own record format via id_patterns.
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,15}\d\b")),   # Luhn-checked in _card_sub
    ("DATE", re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b|\b(?:19|20)\d{2}-\d{2}-\d{2}\b")),
    ("DATE", re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)\d{2}\b")),
    ("PHONE", re.compile(r"(?<![\w-])(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]\d{3,4}[-.\s]?\d{3,4}\b")),
]

_NAME = r"[A-Z](?:'[A-Z])?[a-z]+(?:[A-Z][a-z]+)?(?:-[A-Z][a-z]+)?"   # Sarah, O'Neil, McDonald, Smith-Jones
_FULLNAME = rf"{_NAME}(?:\s+{_NAME}){{0,2}}(?:\s+\d{{1,4}})?"
_NAME_CUES: list[re.Pattern] = [
    re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Professor|Nurse|Patient|Pt)\.?\s+({_FULLNAME})"),
    re.compile(rf"\b(?:[Mm]y name is|[Nn]ame:|[Pp]atient named|[Pp]atient|[Ii] am)\s+({_FULLNAME})"),
]
# Capitalised words that follow a cue but are not names.
_NOT_NAMES = {"The", "This", "A", "An", "He", "She", "They", "Was", "Is", "With", "Who", "In", "On", "At",
              "History", "Presented", "Admitted", "Discharged", "Aged", "Male", "Female", "Diagnosed",
              # "Patient <Noun>" in literature is an instrument or a population, not a person
              "Health", "Survey", "Population", "Questionnaire", "Reported", "Outcome", "Outcomes", "Care",
              "Safety", "Education", "Satisfaction", "Experience", "Experiences", "Practitioner", "Practitioners",
              "Protection", "Preference", "Preferences", "Centered", "Centred", "Assessment", "Registry",
              "Records", "Record", "Information", "Advocacy", "Engagement", "Journey", "Portal"}


@dataclass
class Deidentifier:
    """`known_identifiers`: the node's own registry of names and ids.
    `backend`: optional extra callable text -> text (a validated tool)."""
    known_identifiers: Iterable[str] = ()
    id_patterns: Iterable[str] = ()        # the institution's own record formats, e.g. r"\bTEST-\d{4}\b"
    backend: Callable[[str], str] | None = None
    counts: Counter = field(default_factory=Counter)

    def __post_init__(self) -> None:
        terms = sorted({t.strip() for t in self.known_identifiers if t and t.strip()}, key=len, reverse=True)
        self._registry = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.I) if terms else None
        self._id_patterns = [re.compile(p) for p in self.id_patterns]

    def __call__(self, text: str) -> str:
        return self.redact(text)

    def redact(self, text: str) -> str:
        if self.backend is not None:
            text = self.backend(text)
        if self._registry is not None:
            text, n = self._registry.subn("[NAME_OR_ID]", text)
            self.counts["REGISTRY"] += n
        for pattern in self._id_patterns:
            text, n = pattern.subn("[ID]", text)
            self.counts["ID"] += n
        for label, pattern in _STRUCTURED:
            if label == "CARD":
                text = pattern.sub(self._card_sub, text)
                continue
            text, n = pattern.subn(f"[{label}]", text)
            self.counts[label] += n
        for pattern in _NAME_CUES:
            text = pattern.sub(self._name_sub, text)
        return text

    def _card_sub(self, match: re.Match) -> str:
        digits = [int(c) for c in match.group(0) if c.isdigit()]
        total = 0
        for i, d in enumerate(reversed(digits)):
            d = d * 2 if i % 2 else d
            total += d - 9 if d > 9 else d
        if total % 10:
            return match.group(0)            # not a card number (fails Luhn)
        self.counts["CARD"] += 1
        return "[CARD]"

    def _name_sub(self, match: re.Match) -> str:
        name = match.group(1)
        first = name.split()[0]
        if first in _NOT_NAMES:
            return match.group(0)
        self.counts["NAME"] += 1
        return match.group(0)[: match.start(1) - match.start(0)] + "[NAME]"

    def redact_all(self, documents: list[str]) -> list[str]:
        return [self.redact(d) for d in documents]


_PLACEHOLDER = re.compile(r"\[(?:EMAIL|URL|IP|ID|SSN|CARD|DATE|PHONE|NAME|NAME_OR_ID)\]")


def strip_placeholders(text: str) -> str:
    """For derived public metadata (topics/description): drop the placeholder
    tokens so "[NAME]" never becomes a published topic word."""
    return _PLACEHOLDER.sub(" ", text)
