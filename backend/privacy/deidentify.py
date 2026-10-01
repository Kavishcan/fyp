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
    ("ID", re.compile(r"\b(?i:MRN|NHS|SSN|NIC|National ID|ID|Patient ID|Record|Hospital No|Passport)\.?\s*"
                      r"(?:(?i:no|number|is)\.?\s*|#\s*|:\s*)?"
                      r"(?:[A-Z]{1,4}[- ]?)?\d[\d -]{2,14}\d(?:[- ]?[A-Z]{1,4}\b)?")),
    # Sri Lankan National Identity Card, unlabelled: old 9 digits + V/X,
    # new 12 digits beginning with the birth year (docs/49 gap).
    ("ID", re.compile(r"\b\d{9}[VvXx]\b|\b(?:19|20)\d{2}[0-8]\d{7}\b")),
    # Passport numbers only with their label (a bare "N1234567" is too often a
    # catalogue or accession number).
    ("ID", re.compile(r"\b(?i:passport)(?:\s+(?i:no|number))?\.?\s*[:#]?\s*[A-Z]{1,2}\d{6,8}\b")),
    # NOTE: no bare "ABC-123" rule. In biomedical text that shape is a
    # compound, drug or cell line (PCB-153, MB-231, GS-9620) far more often
    # than a person; an institution adds its own record format via id_patterns.
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,15}\d\b")),   # Luhn-checked in _card_sub
    ("DATE", re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b|\b(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b")),
    ("DATE", re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+(?:19|20)\d{2}\b")),
    ("DATE", re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(?:19|20)\d{2}\b")),
    # HIPAA Safe Harbor: ages over 89 are identifying (docs/49 gap).
    ("AGE", re.compile(r"\b(?:9\d|1[0-1]\d)(?:[- ](?:year|yr)s?[- ]old|[- ]?(?:yo|y/o|y\.o\.)\b)|"
                       r"\b(?i:aged|age)\s+(?:9\d|1[0-1]\d)\b")),
    # Street addresses: house number + 1-3 capitalised words + a street type,
    # optionally ", City" and a postcode (docs/49 gap).
    ("ADDRESS", re.compile(r"\b\d{1,5}[A-Z]?(?:/\d{1,4})?,?\s+(?:[A-Z][a-z]+\s+){1,3}"
                           r"(?:Street|St\.|Road|Rd\.?|Lane|Avenue|Ave\.?|Mawatha|Place|Drive|Terrace|Close|Crescent|"
                           r"Gardens|Boulevard)\b(?:,?\s+[A-Z][a-z]+(?:\s+\d{3,6})?)?")),
    ("PHONE", re.compile(r"(?<![\w-])(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]\d{3,4}[-.\s]?\d{3,4}\b")),
]

_NAME = r"[A-Z](?:'[A-Z])?[a-z]+(?:[A-Z][a-z]+)?(?:-[A-Z][a-z]+)?"   # Sarah, O'Neil, McDonald, Smith-Jones
_FULLNAME = rf"{_NAME}(?:\s+{_NAME}){{0,2}}(?:\s+\d{{1,4}})?"
_NAME_CUES: list[re.Pattern] = [
    re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Professor|Nurse|Patient|Pt)\.?\s+({_FULLNAME})"),
    re.compile(rf"\b(?:[Mm]y name is|[Nn]ame:|[Pp]atient named|[Pp]atient|[Ii] am)\s+({_FULLNAME})"),
    # Relatives and carers are identifying too (docs/49 gap): "daughter Nimali".
    re.compile(rf"\b(?:[Dd]aughter|[Ss]on|[Ww]ife|[Hh]usband|[Mm]other|[Ff]ather|[Bb]rother|[Ss]ister|[Pp]artner|"
               rf"[Ss]pouse|[Gg]uardian|[Cc]arer|[Cc]aregiver|[Nn]ext of kin)[,:]?\s+({_FULLNAME})"),
]
# Capitalised words that follow a cue but are not names.
_NOT_NAMES = {"The", "This", "A", "An", "He", "She", "They", "Was", "Is", "With", "Who", "In", "On", "At",
              "History", "Presented", "Admitted", "Discharged", "Aged", "Male", "Female", "Diagnosed",
              # "Patient <Noun>" in literature is an instrument or a population, not a person
              "Health", "Survey", "Population", "Questionnaire", "Reported", "Outcome", "Outcomes", "Care",
              "Safety", "Education", "Satisfaction", "Experience", "Experiences", "Practitioner", "Practitioners",
              "Protection", "Preference", "Preferences", "Centered", "Centred", "Assessment", "Registry",
              "Records", "Record", "Information", "Advocacy", "Engagement", "Journey", "Portal"}


# --- level "safe_harbor" (docs/54) --------------------------------------------
#
# Opt-in additions aimed at the HIPAA Safe Harbor identifier list. The default
# level ("basic") is unchanged, so every earlier measured result stays valid.
# Written against the DEV half of the docs/54 benchmark only; its TEST half
# (other templates, other names) is what is reported.

_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_MONTHS = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"}

# A labelled number of any Safe Harbor kind: accounts, health-plan and member
# ids, licences and certificates, vehicle plates and VINs, device serials,
# fax. The value must contain at least three digits so "policy changes" or
# "serial measurements" are never touched.
_SH_LABELLED = re.compile(
    r"\b(?i:account|acct|a/c|billing|policy|member(?:ship)?|insurance|insurer|health plan|beneficiary|subscriber|"
    r"claim|driving licen[cs]e|licen[cs]e|certificate|registration|number plate|licen[cs]e plate|plate|VIN|chassis|"
    r"serial|S/N|IMEI|badge|employee|staff)"
    r"(?:\s+(?i:no|number|num|id|code|#))?\.?\s*(?:[:#]\s*)?"
    r"(?=[A-Z0-9/ -]{0,30}?\d[A-Z0-9/ -]{0,30}?\d[A-Z0-9/ -]{0,30}?\d)"
    r"[A-Z0-9](?:[A-Z0-9/-]|\s(?=[A-Z0-9]))*[A-Z0-9]")
_SH_FAX = re.compile(r"\b(?i:fax)\.?\s*(?i:no|number)?\.?\s*:?\s*\+?[\d()][\d ()-]{6,18}\d")
_SH_DATES: list[re.Pattern] = [
    re.compile(r"(?<![\d.])\d{1,2}([/.-])\d{1,2}\1\d{2}(?![\d.]\d|\d)"),                      # 12/03/19, not 12.0-16.0
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\b"),                       # 3 March, 3rd of March
    re.compile(rf"\b{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b(?!\s*(?:%|mg|patients|cases))"),  # March 3rd
    # "on 12/03": only after on/dated and only with "/" — "from 3.2" is a lab
    # value and "7/10" after from/by is a pain score
    re.compile(r"\b(?i:on|dated)\s+\d{1,2}/\d{1,2}\b(?![/.]\d|\s*(?:mg|mmHg|%))"),
]
_SH_MONTH_YEAR = re.compile(rf"\b{_MONTH}\.?,?\s+((?:19|20)\d{{2}})\b")                   # March 2019 -> [DATE] 2019
_SH_INSTITUTION = re.compile(
    r"\b(?!(?:The|Our|A|An|This|That|Its|Their|His|Her|In|At|To|From|Of|Each|Every)\s)"
    r"(?:St\.?\s+|Saint\s+)?(?:[A-Z][a-z']+\s+){1,4}"
    r"(?:Hospital|Medical Cent(?:er|re)|Clinic|Infirmary|Health Cent(?:er|re)|Nursing Home|Hospice|Polyclinic)\b")
_SH_LOCATION_CUE = re.compile(
    r"\b(?:[Rr]esident of|[Rr]esides in|[Rr]esiding in|[Ll]ives in|[Ll]iving in|[Ll]ived in|[Bb]orn in|[Nn]ative of|"
    r"[Hh]ometown(?: of| is|,)?|from the (?:town|village|city|district|province) of|[Hh]ome in|"
    r"(?:travell?ed|came|moved|relocated) (?:here )?(?:from|to))\s+"
    r"((?:[A-Z][a-z]+)(?:[ -][A-Z][a-z]+){0,2})")
_SH_PLACE_PAIR = re.compile(r"\bin ([A-Z][a-z]+(?: [A-Z][a-z]+)?), (?:[A-Z][a-z]+(?: [A-Z][a-z]+)?|[A-Z]{2})\b")
_SH_POSTCODE: list[re.Pattern] = [
    re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}\b"),                                    # UK
    re.compile(r"\b[A-Z]{2}\s\d{5}(?:-\d{4})?\b"),                                          # US state + ZIP
    re.compile(r"\b(?i:zip(?: code)?|postcode|post code|postal code)\s*:?\s*[A-Z0-9]{3,4}\s?[A-Z0-9]{0,4}\b"),
]
# Names without an honorific: a 2-3 word capitalised span directly followed by
# what only a person does in a case report ("..., a 45-year-old", "was
# admitted", "'s mother"), clinician roles, signature lines and header labels.
_PERSON_NEXT = (r"(?=,\s+an?\s+\d{1,3}[- ](?:year|month|week|day)|\s+\(\d{1,3}\s*(?:y|yo|yrs?|years?)\b|"
                r"\s+(?:was|is|had|has)\s+(?:admitted|referred|brought|transferred|seen|born|discharged|a\s+\d)|"
                r"\s+(?:presented|complained|reported|underwent|died|attended|visited|consented)\b|"
                r"'s\s+(?:mother|father|wife|husband|daughter|son|family|parents|sister|brother|condition|symptoms))")
_SH_NAME_CUES: list[re.Pattern] = [
    re.compile(rf"\b({_NAME}\s+{_NAME}(?:\s+{_NAME})?){_PERSON_NEXT}"),
    re.compile(rf"\b(?:[Aa]ttending|[Cc]onsultant|[Ss]urgeon|[Pp]hysician|[Rr]eferred by|[Ss]een by|[Ss]igned(?: by)?:?|"
               rf"[Rr]eviewed by|[Cc]c:)\s+(?:Dr\.?\s+)?({_FULLNAME})"),
    re.compile(r"\b([A-Z]\.\s?(?:[A-Z]\.\s?)?[A-Z][a-z]+),?\s+(?=(?:MD|MBBS|DO|RN|FRCP|MRCP|MS|PhD)\b)"),
    # consent statements name the person who gave it
    re.compile(rf"\b(?:[Cc]onsent|[Pp]ermission|[Aa]ssent)\b[^.]{{0,40}}?\b(?:from|by)\s+({_FULLNAME})"),
    re.compile(r"\b(?:NAME|PATIENT|PT NAME|PATIENT NAME|[Nn]ame|[Pp]atient|[Pp]atient [Nn]ame)\s*:\s*"
               r"([A-Z][A-Za-z'-]+,?\s+[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+)?)"),
]
_NOT_NAME_WORDS = _NOT_NAMES | _MONTHS | {
    "Patient", "Patients", "Case", "Cases", "Our", "Their", "His", "Her", "Its", "Physical", "Clinical", "Report",
    "Emergency", "Department", "Hospital", "Medical", "Center", "Centre", "University", "General", "Type",
    "Group", "Table", "Figure", "Fig", "Disease", "Syndrome", "Doctor", "Mother", "Father", "Baby", "Infant",
    "Boy", "Girl", "Man", "Woman", "Subject", "Proband", "Index", "Control", "Controls", "Twin", "Donor"}


@dataclass
class Deidentifier:
    """`known_identifiers`: the node's own registry of names and ids.
    `backend`: optional extra callable text -> text (a validated tool).
    `level`: "basic" (docs/44, the default every measured result used) or
    "safe_harbor" (docs/54: adds labelled account/plan/licence/vehicle/device
    numbers, fax, dates without a year and month-year reduced to the year,
    institutions, residence places and postcodes, and names without an
    honorific)."""
    known_identifiers: Iterable[str] = ()
    id_patterns: Iterable[str] = ()        # the institution's own record formats, e.g. r"\bTEST-\d{4}\b"
    backend: Callable[[str], str] | None = None
    level: str = "basic"
    counts: Counter = field(default_factory=Counter)

    def __post_init__(self) -> None:
        base = {t.strip() for t in self.known_identifiers if t and t.strip()}
        # Registry names also appear surname-first ("Menon, Rahul"), without
        # the comma, or with an initial ("R. Menon") — docs/49 gap.
        variants = set(base)
        for t in base:
            parts = t.split()
            if len(parts) >= 2 and all(p[:1].isalpha() for p in parts):
                first, last = " ".join(parts[:-1]), parts[-1]
                variants |= {f"{last}, {first}", f"{last} {first}", f"{first[0]}. {last}", f"{first[0]} {last}"}
        terms = sorted(variants, key=len, reverse=True)
        self._registry = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.I) if terms else None
        self._id_patterns = [re.compile(p) for p in self.id_patterns]
        if self.level not in ("basic", "safe_harbor"):
            raise ValueError(f"unknown de-identification level {self.level!r}")

    def __call__(self, text: str) -> str:
        return self.redact(text)

    def redact(self, text: str) -> str:
        sh = self.level == "safe_harbor"
        if self.backend is not None and not sh:
            text = self.backend(text)
        if self._registry is not None:
            text, n = self._registry.subn("[NAME_OR_ID]", text)
            self.counts["REGISTRY"] += n
        for pattern in self._id_patterns:
            text, n = pattern.subn("[ID]", text)
            self.counts["ID"] += n
        if sh:
            text = self._sub(_SH_FAX, "PHONE", text)
            text = self._sub(_SH_LABELLED, "ID", text)
        for label, pattern in _STRUCTURED:
            if label == "CARD":
                text = pattern.sub(self._card_sub, text)
                continue
            if sh and label == "AGE":                       # full dates are done; now the partial ones
                for p in _SH_DATES:
                    text = self._sub(p, "DATE", text)
                text, n = _SH_MONTH_YEAR.subn(r"[DATE] \1", text)
                self.counts["DATE"] += n
            text, n = pattern.subn(f"[{label}]", text)
            self.counts[label] += n
        if sh:
            text = self._sub(_SH_INSTITUTION, "ORGANIZATION", text)
            for p in _SH_POSTCODE:
                text = self._sub(p, "LOCATION", text)
            text = _SH_LOCATION_CUE.sub(self._place_sub, text)
            text = _SH_PLACE_PAIR.sub(self._place_sub, text)
            if self.backend is not None:                    # NER after the rules, so it cannot split an address
                text = self.backend(text)
        for pattern in _NAME_CUES:
            text = pattern.sub(self._name_sub, text)
        if sh:
            for pattern in _SH_NAME_CUES:
                text = pattern.sub(self._sh_name_sub, text)
        return text

    def _sub(self, pattern: re.Pattern, label: str, text: str) -> str:
        text, n = pattern.subn(f"[{label}]", text)
        self.counts[label] += n
        return text

    def _place_sub(self, match: re.Match) -> str:
        if match.group(1).split()[0] in _MONTHS | _NOT_NAMES:
            return match.group(0)
        self.counts["LOCATION"] += 1
        return match.group(0)[: match.start(1) - match.start(0)] + "[LOCATION]" + match.group(0)[match.end(1) - match.start(0):]

    def _sh_name_sub(self, match: re.Match) -> str:
        name = match.group(1)
        if any(w.strip(",.") in _NOT_NAME_WORDS for w in name.split() if len(w.strip(",.")) > 1):   # initials pass
            return match.group(0)
        self.counts["NAME"] += 1
        return match.group(0)[: match.start(1) - match.start(0)] + "[NAME]" + match.group(0)[match.end(1) - match.start(0):]

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


_PLACEHOLDER = re.compile(r"\[(?:EMAIL|URL|IP|ID|SSN|CARD|DATE|PHONE|NAME|NAME_OR_ID|LOCATION|AGE|ADDRESS|ORGANIZATION)\]")


def strip_placeholders(text: str) -> str:
    """For derived public metadata (topics/description): drop the placeholder
    tokens so "[NAME]" never becomes a published topic word."""
    return _PLACEHOLDER.sub(" ", text)


# --- optional NER backend: Microsoft Presidio (docs/44) -------------------------
#
# The rule + registry layers cannot see a bare name with no cue that is not in
# the institution's registry. A trained named-entity recogniser can. Presidio
# is used with spaCy's SMALL English model (en_core_web_sm, ~12 MB) — Presidio's
# default is en_core_web_lg (~560 MB), over this project's download limit, and
# the clinical transformer de-identifiers (~440 MB) are the stated production
# choice, not installed. Optional dependency: absent packages raise ImportError
# at construction, never silently fall back.

PRESIDIO_ENTITIES = ("PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD",
                     "IP_ADDRESS", "URL", "DATE_TIME", "NRP")


_FULL_NAME_SPAN = re.compile(r"^[A-Z](?:'[A-Z])?[a-z]+(?:[ '-][A-Z](?:'[A-Z])?[a-z]+)+$")


def presidio_backend(spacy_model: str = "en_core_web_sm", entities: Iterable[str] = ("PERSON",),
                     score_threshold: float = 0.5, full_names_only: bool = True) -> Callable[[str], str]:
    """A `Deidentifier.backend`: Presidio analyzer + anonymizer, replacing each
    entity with `[NAME]` (PERSON) or `[<ENTITY>]`.

    Defaults measured in docs/44. The small spaCy model over-fires badly on
    biomedical abstracts: LOCATION tagged "Mediterranean" (diet), "MM",
    "cyanobacteria"; PERSON tagged "BMAA", "Cox" (regression), "Cd", "Proteus
    mirabilis". With PERSON+LOCATION it altered 66% of clean documents. So:
    PERSON only (a country named in a study is not a patient identifier), and
    `full_names_only` keeps a PERSON span only if it is two or more
    capitalised words — the shape of a patient's name, not of an acronym,
    species, statistic or single cited surname."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": spacy_model}]})
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    anonymizer = AnonymizerEngine()
    wanted = list(entities)
    operators = {e: OperatorConfig("replace", {"new_value": "[NAME]" if e == "PERSON" else f"[{e}]"}) for e in wanted}

    def redact(text: str) -> str:
        results = analyzer.analyze(text=text, language="en", entities=wanted, score_threshold=score_threshold)
        if full_names_only:
            results = [r for r in results if r.entity_type != "PERSON" or _FULL_NAME_SPAN.match(text[r.start:r.end])]
        return anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text if results else text

    redact.name = f"presidio[{spacy_model}]"  # type: ignore[attr-defined]
    return redact
