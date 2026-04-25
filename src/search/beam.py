"""
Beam search variant for Module 3 retrieval.

Beam search keeps only the best ``beam_width`` frontier states at each depth.
This reduces memory/runtime compared to UCS on large graphs, but it is not
optimal: a path pruned early cannot be recovered later.

Checkpoint narrative note:
- UCS (optimal with non-negative costs) is preferable when quality is critical.
- Beam search is preferable when you need faster approximate retrieval.

Complexity (informal):
- Let ``b`` be branching factor after neighbor capping and ``d`` explored depth.
- UCS worst case grows with explored frontier states and can exceed ``O(b^d)``.
- Beam roughly caps active frontier to ``beam_width`` per level, giving a
  practical bound near ``O(d * beam_width * b)`` expansions (approximate).
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from search.costs import DissimilarityWeights, pairwise_dissimilarity
from search.graph import capped_neighbors

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


def beam_topk(
    kb: "KnowledgeBase",
    query_mbid: str,
    k: int,
    beam_width: int = 10,
    max_depth: int = 6,
    max_degree: Optional[int] = None,
    weights: Optional[DissimilarityWeights] = None,
) -> List[Tuple[str, float]]:
    """
    Approximate top-K retrieval using beam search from ``query_mbid``.

    Returns up to K unique songs (excluding query) ranked by lowest discovered
    cumulative path cost. Deterministic ordering is used for ties.

    Args:
        kb: Knowledge base.
        query_mbid: Start node; must exist in ``kb.songs``.
        k: Number of songs to return; if <= 0 returns [].
        beam_width: Number of frontier states kept per depth (>=1).
        max_depth: Number of expansion layers to explore (>=0).
        max_degree: Neighbor cap passed to ``capped_neighbors``.
        weights: Edge weights for pairwise dissimilarity.

    Returns:
        List of ``(mbid, path_cost)`` sorted by path cost ascending, then MBID.

    Raises:
        ValueError: If query MBID is missing, or if beam_width/max_depth invalid.
    """
    if query_mbid not in kb.songs:
        raise ValueError(f"Unknown song MBID: {query_mbid!r}")
    if k <= 0:
        return []
    if beam_width <= 0:
        raise ValueError("beam_width must be > 0")
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    w = weights or DissimilarityWeights()
    frontier: List[Tuple[float, str]] = [(0.0, query_mbid)]
    best: Dict[str, float] = {query_mbid: 0.0}

    for _ in range(max_depth):
        if not frontier:
            break
        next_candidates: Dict[str, float] = {}
        for cost_u, u in frontier:
            for v in capped_neighbors(kb, u, max_degree, w):
                edge = pairwise_dissimilarity(kb, u, v, w)
                new_cost = cost_u + edge
                old_global = best.get(v)
                if old_global is None or new_cost < old_global:
                    best[v] = new_cost
                old_local = next_candidates.get(v)
                if old_local is None or new_cost < old_local:
                    next_candidates[v] = new_cost

        ranked_next = sorted((c, n) for n, c in next_candidates.items())
        frontier = ranked_next[:beam_width]

    out = sorted(
        ((mbid, cost) for mbid, cost in best.items() if mbid != query_mbid),
        key=lambda x: (x[1], x[0]),
    )
    return out[:k]
