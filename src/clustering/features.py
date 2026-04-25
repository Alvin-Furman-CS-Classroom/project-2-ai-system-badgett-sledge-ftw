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


def _feature_keys_for_mbid(kb, mbid: str, spec: FeatureVectorSpec) -> List[str]:
    """
    Build normalized feature keys for one MBID under the given spec.

    This helper is shared by both vocabulary construction and vector filling so
    feature semantics stay consistent in one place.
    """
    keys: List[str] = []

    if spec.include_genres:
        for g in _as_list(kb.get_fact("has_genre", mbid)):
            s = g.strip().lower()
            if s:
                keys.append(f"genre:{s}")

    if spec.include_moods:
        for m in _as_list(kb.get_fact("has_mood", mbid)):
            s = m.strip().lower()
            if s:
                keys.append(f"mood:{s}")

    if spec.include_danceable:
        v = kb.get_fact("has_danceable", mbid)
        if v is not None:
            s = str(v).strip().lower()
            if s:
                keys.append(f"danceable:{s}")

    if spec.include_voice_instrumental:
        v = kb.get_fact("has_voice_instrumental", mbid)
        if v is not None:
            s = str(v).strip().lower()
            if s:
                keys.append(f"vi:{s}")

    if spec.include_timbre:
        v = kb.get_fact("has_timbre", mbid)
        if v is not None:
            s = str(v).strip().lower()
            if s:
                keys.append(f"timbre:{s}")

    if spec.include_loudness_bucket:
        b = _loudness_bucket(kb.get_fact("has_loudness", mbid))
        if b:
            keys.append(f"loudness_bucket:{b}")

    return keys


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

    feature_keys_by_mbid: Dict[str, List[str]] = {
        mbid: _feature_keys_for_mbid(kb, mbid, spec) for mbid in mbids
    }

    # Build vocabulary from the candidate pool.
    vocab_set = {key for keys in feature_keys_by_mbid.values() for key in keys}

    vocab: List[str] = sorted(vocab_set)
    index = {k: i for i, k in enumerate(vocab)}

    vectors: Dict[str, List[float]] = {}
    for mbid in mbids:
        vec = [0.0] * len(vocab)
        for key in feature_keys_by_mbid[mbid]:
            i = index.get(key)
            if i is not None:
                vec[i] = 1.0

        vectors[mbid] = vec

    return vectors, vocab

