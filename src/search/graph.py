"""
Neighbor generation from KnowledgeBase indexes, with optional degree cap.

Neighbors are songs that share at least one genre, mood, danceability,
voice/instrumental, or timbre bucket with the current song (via indexes).
Cap keeps the cheapest edges first by ``pairwise_dissimilarity`` (deterministic
tie-break by MBID).
"""

from typing import TYPE_CHECKING, List, Optional, Set

from search.costs import DissimilarityWeights, pairwise_dissimilarity

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


def _genres_for_song(kb: "KnowledgeBase", mbid: str) -> List[str]:
    raw = kb.get_fact("has_genre", mbid)
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(g).lower() for g in raw if g is not None]
    return [str(raw).lower()]


def _moods_for_song(kb: "KnowledgeBase", mbid: str) -> List[str]:
    raw = kb.get_fact("has_mood", mbid)
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(m).lower() for m in raw if m is not None]
    return [str(raw).lower()]


def neighbor_candidates(kb: "KnowledgeBase", mbid: str) -> Set[str]:
    """
    All songs that share an index bucket with ``mbid`` (genre, mood, danceable,
    voice/instrumental, timbre). Excludes ``mbid``. Does not use popularity.
    """
    out: Set[str] = set()

    for g in _genres_for_song(kb, mbid):
        out.update(kb.songs_by_genre(g))

    for m in _moods_for_song(kb, mbid):
        out.update(kb.songs_by_mood(m))

    d = kb.get_fact("has_danceable", mbid)
    if d is not None:
        out.update(kb.songs_by_danceable(str(d).lower()))

    vi = kb.get_fact("has_voice_instrumental", mbid)
    if vi is not None:
        out.update(kb.songs_by_voice_instrumental(str(vi).lower()))

    t = kb.get_fact("has_timbre", mbid)
    if t is not None:
        out.update(kb.songs_by_timbre(str(t).lower()))

    out.discard(mbid)
    return out


def capped_neighbors(
    kb: "KnowledgeBase",
    mbid: str,
    max_degree: Optional[int],
    weights: Optional[DissimilarityWeights] = None,
) -> List[str]:
    """
    Neighbor MBIDs sorted by increasing pairwise dissimilarity from ``mbid``,
    then by MBID for stable ordering. If ``max_degree`` is None, returns all
    candidates in that order; if a positive int, returns at most that many.
    """
    candidates = neighbor_candidates(kb, mbid)
    w = weights or DissimilarityWeights()

    scored = [
        (pairwise_dissimilarity(kb, mbid, other, w), other)
        for other in candidates
    ]
    scored.sort(key=lambda x: (x[0], x[1]))

    ordered = [other for _, other in scored]
    if max_degree is None or max_degree < 0:
        return ordered
    return ordered[:max_degree]
