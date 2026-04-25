"""
Uniform Cost Search over the song graph (Module 3).

Expands using ``capped_neighbors`` and ``pairwise_dissimilarity`` edge costs.
Returns up to K other songs in order of minimum path cost from the query song.
"""

import heapq
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from search.costs import DissimilarityWeights, pairwise_dissimilarity
from search.graph import capped_neighbors

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


def ucs_topk(
    kb: "KnowledgeBase",
    query_mbid: str,
    k: int,
    max_degree: Optional[int] = None,
    weights: Optional[DissimilarityWeights] = None,
) -> List[Tuple[str, float]]:
    """
    Run UCS from ``query_mbid`` and collect the first K settled songs other than
    the query, in non-decreasing order of shortest-path cost.

    Tie-breaking when popping from the frontier: lower MBID first (via
    ``(cost, mbid)`` tuple ordering), so results are deterministic.

    If fewer than K songs are reachable in the graph, returns fewer than K
    entries. Does not use popularity.

    Args:
        kb: Knowledge base.
        query_mbid: Start node; must exist in ``kb.songs``.
        k: Number of results (other songs) to return; if <= 0, returns [].
        max_degree: Passed to ``capped_neighbors`` (None = all candidates).
        weights: Edge cost weights; default ``DissimilarityWeights()``.

    Returns:
        List of ``(mbid, path_cost)`` for songs other than ``query_mbid``.

    Raises:
        ValueError: If ``query_mbid`` is not in the knowledge base.
    """
    if query_mbid not in kb.songs:
        raise ValueError(f"Unknown song MBID: {query_mbid!r}")
    if k <= 0:
        return []

    w = weights or DissimilarityWeights()
    # Frontier: (path_cost, mbid); heapq breaks ties by mbid for determinism.
    heap: List[Tuple[float, str]] = [(0.0, query_mbid)]
    best: Dict[str, float] = {query_mbid: 0.0}
    results: List[Tuple[str, float]] = []

    while heap and len(results) < k:
        cost_u, u = heapq.heappop(heap)
        if cost_u > best.get(u, float("inf")):
            continue
        if u != query_mbid:
            results.append((u, cost_u))
            if len(results) >= k:
                break
        for v in capped_neighbors(kb, u, max_degree, w):
            edge = pairwise_dissimilarity(kb, u, v, w)
            new_cost = cost_u + edge
            if new_cost < best.get(v, float("inf")):
                best[v] = new_cost
                heapq.heappush(heap, (new_cost, v))

    return results
