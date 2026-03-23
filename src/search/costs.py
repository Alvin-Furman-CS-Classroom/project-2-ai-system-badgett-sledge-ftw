"""
Pairwise dissimilarity between songs for Module 3 edge costs.

Uses only KB facts (no popularity). Costs are symmetric and non-negative.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, FrozenSet, Optional, Set

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


def _as_lower_str_set(value: Any) -> FrozenSet[str]:
    if value is None:
        return frozenset()
    if isinstance(value, list):
        return frozenset(str(x).lower() for x in value if x is not None)
    return frozenset({str(value).lower()})


def jaccard_distance(set_a: Set[str], set_b: Set[str]) -> float:
    """
    Distance 0 = identical, 1 = disjoint (or one empty when the other is not).
    Empty/empty yields 0.
    """
    if not set_a and not set_b:
        return 0.0
    if not set_a or not set_b:
        return 1.0
    union = len(set_a | set_b)
    inter = len(set_a & set_b)
    return 1.0 - (inter / union) if union else 0.0


def _numeric_abs_diff(
    kb: "KnowledgeBase",
    mbid_a: str,
    mbid_b: str,
    fact_type: str,
    per_unit_scale: float,
    missing_penalty: float,
) -> float:
    va = kb.get_fact(fact_type, mbid_a)
    vb = kb.get_fact(fact_type, mbid_b)
    if va is None and vb is None:
        return 0.0
    if va is None or vb is None:
        return missing_penalty
    try:
        return abs(float(va) - float(vb)) * per_unit_scale
    except (TypeError, ValueError):
        return missing_penalty


def _categorical_mismatch(
    kb: "KnowledgeBase",
    mbid_a: str,
    mbid_b: str,
    fact_type: str,
    mismatch_penalty: float,
) -> float:
    va = kb.get_fact(fact_type, mbid_a)
    vb = kb.get_fact(fact_type, mbid_b)
    if va is None and vb is None:
        return 0.0
    if va is None or vb is None:
        return mismatch_penalty * 0.5
    if str(va).lower() == str(vb).lower():
        return 0.0
    return mismatch_penalty


@dataclass(frozen=True)
class DissimilarityWeights:
    """Weights for combining feature dissimilarities into one edge cost."""

    genre: float = 4.0
    mood: float = 3.0
    loudness_per_db: float = 0.12
    duration_per_sec: float = 0.015
    danceable_mismatch: float = 2.0
    voice_instrumental_mismatch: float = 1.5
    timbre_mismatch: float = 1.5
    tempo_per_bpm: float = 0.02
    missing_numeric_penalty: float = 0.8
    collaborator_reward_per_shared: float = 0.0  # set >0 when KB has list facts


def pairwise_dissimilarity(
    kb: "KnowledgeBase",
    mbid_a: str,
    mbid_b: str,
    weights: Optional[DissimilarityWeights] = None,
) -> float:
    """
    Symmetric dissimilarity between two songs in [0, inf), suitable for UCS edge costs.

    Combines Jaccard distance on genre/mood tags, scaled numeric differences,
    and categorical mismatches. Optional collaborator overlap reduces cost when
    ``weights.collaborator_reward_per_shared > 0`` and facts like ``has_producer``
    exist as list values on both songs.
    """
    if mbid_a == mbid_b:
        return 0.0
    w = weights or DissimilarityWeights()

    g_a = _as_lower_str_set(kb.get_fact("has_genre", mbid_a))
    g_b = _as_lower_str_set(kb.get_fact("has_genre", mbid_b))
    m_a = _as_lower_str_set(kb.get_fact("has_mood", mbid_a))
    m_b = _as_lower_str_set(kb.get_fact("has_mood", mbid_b))

    total = w.genre * jaccard_distance(g_a, g_b) + w.mood * jaccard_distance(m_a, m_b)

    total += _numeric_abs_diff(
        kb, mbid_a, mbid_b, "has_loudness",
        w.loudness_per_db, w.missing_numeric_penalty,
    )
    total += _numeric_abs_diff(
        kb, mbid_a, mbid_b, "has_duration",
        w.duration_per_sec, w.missing_numeric_penalty,
    )
    total += _numeric_abs_diff(
        kb, mbid_a, mbid_b, "has_tempo",
        w.tempo_per_bpm, w.missing_numeric_penalty,
    )

    total += _categorical_mismatch(
        kb, mbid_a, mbid_b, "has_danceable", w.danceable_mismatch,
    )
    total += _categorical_mismatch(
        kb, mbid_a, mbid_b, "has_voice_instrumental", w.voice_instrumental_mismatch,
    )
    total += _categorical_mismatch(
        kb, mbid_a, mbid_b, "has_timbre", w.timbre_mismatch,
    )

    if w.collaborator_reward_per_shared > 0:
        reward = _collaborator_overlap_reward(kb, mbid_a, mbid_b)
        total = max(0.0, total - w.collaborator_reward_per_shared * reward)

    return total


def _collaborator_overlap_reward(kb: "KnowledgeBase", mbid_a: str, mbid_b: str) -> float:
    """Count shared names across optional list facts (producers, writers, etc.)."""
    fact_names = (
        "has_producer",
        "has_writer",
        "has_featured_artist",
    )
    shared = 0
    for fname in fact_names:
        fact_dict = kb.facts.get(fname)
        if not fact_dict:
            continue
        va = fact_dict.get(mbid_a)
        vb = fact_dict.get(mbid_b)
        if not va or not vb:
            continue
        set_a = _as_lower_str_set(va)
        set_b = _as_lower_str_set(vb)
        shared += len(set_a & set_b)
    return float(shared)
