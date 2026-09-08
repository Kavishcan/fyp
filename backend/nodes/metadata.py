"""Opt-out, document-only source metadata. No queries, qrels or LLM calls.

The deterministic extractive description can reveal collection topics and
names despite heuristic redaction. It is not a privacy-preserving summary.
"""
from __future__ import annotations

from collections import Counter
import re

import numpy as np

from baselines.base import SourceProfile
from nodes.profile import redact_pii

METHOD = "document-frequency-keywords-v1"
_WORDS = re.compile(r"\b[a-z]{3,}\b")
_STOP = frozenset("""a about above after again against all also among an and any are
as at be because been before being below between both but by can could did do
does doing down during each few for from further had has have having here how
however i if in into is it its itself just may might more most much must no nor
not now of off on once only or other our out over own per same should so some
such than that the their them then there these they this those through to too
under until up upon us use used using very was we were what when where which
while who whom why will with within without would you your abstract background
conclusion conclusions data demonstrate demonstrated et found introduction
methods new paper patients result results showed shows significant significantly
study studies suggest text therefore these thus via whether redacted email phone
id one two three four five six seven eight nine ten first second third
""".split())


def describe_documents(documents: list[str], *, max_topics: int = 16) -> dict:
    if not 1 <= max_topics <= 64:
        raise ValueError("max_topics must be between 1 and 64")
    counts: Counter[str] = Counter()
    for document in documents:
        # Document frequency, not raw word repetition; one document gets one vote.
        words = set(_WORDS.findall(redact_pii(document).lower())) - _STOP
        counts.update(words)
    topics = sorted(counts, key=lambda term: (-counts[term], term))[:max_topics]
    return {
        "description": "Collection topics: " + ", ".join(topics) + "." if topics else "",
        "topics": topics,
        "metadata_method": METHOD,
    }


def attach_metadata(profile: SourceProfile, documents: list[str], embedder, *, enabled: bool = True) -> None:
    """Build inside the source and publish only compact text/topics/vector."""
    profile.description = ""
    profile.topics = []
    profile.description_embedding = None
    profile.metadata_method = "disabled" if not enabled else METHOD
    profile.metadata_embedding_model = ""
    if not enabled:
        return
    metadata = describe_documents(documents)
    profile.description = metadata["description"]
    profile.topics = metadata["topics"]
    if profile.description:
        encode = getattr(embedder, "embed", embedder)
        vector = np.asarray(encode([profile.description])[0], dtype=np.float64)
        if vector.ndim != 1 or not np.isfinite(vector).all():
            raise ValueError("description embedding must be a finite vector")
        profile.description_embedding = vector
        profile.metadata_embedding_model = getattr(embedder, "model_name", "unspecified")
