"""
Feature vector builder for Module 5 clustering.

We keep the feature set simple and interpretable, mirroring Modules 2/4:
- multi-hot: genres, moods
- one-hot/binary: danceable, voice_instrumental, timbre
- loudness bucket

Vectors are built only for the candidate pool (top-N recommendations), so the
vocabulary is derived from that pool for compactness and determinism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class FeatureVectorSpec:
    """
    Defines which KB facts to encode and how.

    This is a light contract so tests and callers can keep behavior stable.
    """

    include_genres: bool = True
    include_moods: bool = True
    include_danceable: bool = True
    include_voice_instrumental: bool = True
    include_timbre: bool = True
    include_loudness_bucket: bool = True


def _as_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def _loudness_bucket(loudness) -> str | None:
    if not isinstance(loudness, (int, float)):
        return None
    if loudness <= -20:
        return "quiet"
    if loudness >= -8:
        return "loud"
    return "medium"


def build_feature_vectors(
    kb,
    mbids: Sequence[str],
    *,
    spec: FeatureVectorSpec | None = None,
) -> Tuple[Dict[str, List[float]], List[str]]:
    """
    Build numeric vectors for each MBID.

    Returns:
        (vectors, vocabulary)
        - vectors: mbid -> list[float] (0/1 values)
        - vocabulary: list[str] feature keys in the same order as vector dimensions
    """
    spec = spec or FeatureVectorSpec()

    # Build vocabulary from the candidate pool.
    vocab_set = set()
    for mbid in mbids:
        if spec.include_genres:
            for g in _as_list(kb.get_fact("has_genre", mbid)):
                s = g.strip().lower()
                if s:
                    vocab_set.add(f"genre:{s}")
        if spec.include_moods:
            for m in _as_list(kb.get_fact("has_mood", mbid)):
                s = m.strip().lower()
                if s:
                    vocab_set.add(f"mood:{s}")
        if spec.include_danceable:
            v = kb.get_fact("has_danceable", mbid)
            if v is not None:
                s = str(v).strip().lower()
                if s:
                    vocab_set.add(f"danceable:{s}")
        if spec.include_voice_instrumental:
            v = kb.get_fact("has_voice_instrumental", mbid)
            if v is not None:
                s = str(v).strip().lower()
                if s:
                    vocab_set.add(f"vi:{s}")
        if spec.include_timbre:
            v = kb.get_fact("has_timbre", mbid)
            if v is not None:
                s = str(v).strip().lower()
                if s:
                    vocab_set.add(f"timbre:{s}")
        if spec.include_loudness_bucket:
            b = _loudness_bucket(kb.get_fact("has_loudness", mbid))
            if b:
                vocab_set.add(f"loudness_bucket:{b}")

    vocab: List[str] = sorted(vocab_set)
    index = {k: i for i, k in enumerate(vocab)}

    vectors: Dict[str, List[float]] = {}
    for mbid in mbids:
        vec = [0.0] * len(vocab)

        if spec.include_genres:
            for g in _as_list(kb.get_fact("has_genre", mbid)):
                key = f"genre:{g.strip().lower()}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0
        if spec.include_moods:
            for m in _as_list(kb.get_fact("has_mood", mbid)):
                key = f"mood:{m.strip().lower()}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0
        if spec.include_danceable:
            v = kb.get_fact("has_danceable", mbid)
            if v is not None:
                key = f"danceable:{str(v).strip().lower()}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0
        if spec.include_voice_instrumental:
            v = kb.get_fact("has_voice_instrumental", mbid)
            if v is not None:
                key = f"vi:{str(v).strip().lower()}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0
        if spec.include_timbre:
            v = kb.get_fact("has_timbre", mbid)
            if v is not None:
                key = f"timbre:{str(v).strip().lower()}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0
        if spec.include_loudness_bucket:
            b = _loudness_bucket(kb.get_fact("has_loudness", mbid))
            if b:
                key = f"loudness_bucket:{b}"
                i = index.get(key)
                if i is not None:
                    vec[i] = 1.0

        vectors[mbid] = vec

    return vectors, vocab

