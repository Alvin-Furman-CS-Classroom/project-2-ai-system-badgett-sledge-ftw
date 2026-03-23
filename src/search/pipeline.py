"""
Module 3 pipeline: UCS retrieval + Module 2 preference scores.

Runs Uniform Cost Search for candidate songs, then combines shortest-path cost
with ``PreferenceScorer`` using per-query min–max normalization on the
candidate set. The query song is never included (UCS already excludes it).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from preferences.scorer import PreferenceScorer

from search.costs import DissimilarityWeights
from search.ucs import ucs_topk

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


@dataclass(frozen=True)
class SearchResult:
    """One recommendation: graph path cost, rule-based preference, and blend."""

    mbid: str
    path_cost: float
    preference_score: float
    combined_score: float


def _min_max_normalize(values: List[float]) -> List[float]:
    """
    Map values to [0, 1] using min–max on this batch.

    If all values are equal (or the list has one element), returns 0.5 for each
    so neither term dominates from degenerate scaling.
    """
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def find_similar(
    kb: "KnowledgeBase",
    query_mbid: str,
    scorer: PreferenceScorer,
    k: int,
    *,
    alpha: float = 1.0,
    beta: float = 1.0,
    max_degree: Optional[int] = None,
    dissimilarity_weights: Optional[DissimilarityWeights] = None,
) -> List[SearchResult]:
    """
    Retrieve up to ``k`` songs similar to ``query_mbid`` via UCS, then rank by a
    linear blend of normalized path cost and normalized preference score.

    **Normalization (per call, over the candidate list only):**

    - ``C_norm``: min–max of path costs in the batch. Lower path cost is better,
      so the cost term uses ``-C_norm`` in the blend.
    - ``P_norm``: min–max of preference scores for the same batch.

    **Combined score** (higher is better)::

        combined = -alpha * C_norm + beta * P_norm

    Tie-break on ``combined_score``: descending, then MBID ascending.

    Popularity is not used anywhere (see UCS and ``PreferenceScorer`` inputs).

    Args:
        kb: Knowledge base.
        query_mbid: Seed song; must exist in ``kb.songs``; never appears in results.
        scorer: Module 2 ``PreferenceScorer`` (rules + weights).
        k: Maximum number of results.
        alpha: Weight on the (negated) normalized path cost term.
        beta: Weight on the normalized preference term.
        max_degree: Neighbor cap for UCS (see ``ucs_topk``).
        dissimilarity_weights: Edge weights for UCS (see ``DissimilarityWeights``).

    Returns:
        Sorted list of ``SearchResult``, longest-first by ``combined_score``.
    """
    raw = ucs_topk(
        kb,
        query_mbid,
        k,
        max_degree=max_degree,
        weights=dissimilarity_weights,
    )
    if not raw:
        return []

    mbids = [mbid for mbid, _ in raw]
    costs = [c for _, c in raw]
    prefs = [scorer.score(mbid, kb) for mbid in mbids]

    c_norm = _min_max_normalize(costs)
    p_norm = _min_max_normalize(prefs)

    merged: List[SearchResult] = []
    for i, mbid in enumerate(mbids):
        combined = -alpha * c_norm[i] + beta * p_norm[i]
        merged.append(
            SearchResult(
                mbid=mbid,
                path_cost=costs[i],
                preference_score=prefs[i],
                combined_score=combined,
            )
        )

    merged.sort(key=lambda r: (-r.combined_score, r.mbid))
    return merged
