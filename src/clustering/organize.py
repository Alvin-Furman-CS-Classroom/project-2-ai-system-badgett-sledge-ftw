"""
Module 5 organizer: cluster candidates then diversify ordering.

This is a post-retrieval step:
- Input: ranked SearchResults (top-N pool) + KB
- Output: cluster groups + a round-robin diversified list
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from search.pipeline import SearchResult

from .features import FeatureVectorSpec, build_feature_vectors
from .kmeans import KMeansConfig, kmeans_cluster


@dataclass(frozen=True)
class ClusteredResult:
    cluster_id: int
    members: Tuple[SearchResult, ...]  # ordered within cluster


@dataclass(frozen=True)
class ClusteredRecommendationSet:
    """
    Full Module 5 output.

    - clusters: per-cluster member lists (ranked within cluster)
    - diversified: final round-robin ordering (length <= top_k)
    - metadata: configuration and diagnostics for reproducibility
    """

    clusters: Tuple[ClusteredResult, ...]
    diversified: Tuple[SearchResult, ...]
    metadata: Dict[str, object]


def _rank_within_cluster(members: List[SearchResult]) -> List[SearchResult]:
    return sorted(members, key=lambda r: (-r.combined_score, r.mbid))


def _cluster_priority(cluster_members: List[SearchResult]) -> tuple[float, str]:
    """
    Cluster ordering priority: best combined_score in cluster (desc), then MBID.
    """
    if not cluster_members:
        return (-1e18, "")
    best = max(cluster_members, key=lambda r: (r.combined_score, r.mbid))
    return (best.combined_score, best.mbid)


def round_robin_diversify(
    clusters: List[List[SearchResult]],
    *,
    top_k: int,
) -> List[SearchResult]:
    """
    Interleave clusters round-robin.
    Assumes each cluster list is already sorted best-first.
    """
    if top_k <= 0:
        return []

    out: List[SearchResult] = []
    idx = 0
    while len(out) < top_k:
        added_this_round = False
        for c in range(len(clusters)):
            if idx < len(clusters[c]):
                out.append(clusters[c][idx])
                added_this_round = True
                if len(out) >= top_k:
                    break
        if not added_this_round:
            break
        idx += 1
    return out


def cluster_and_organize(
    kb,
    results: Sequence[SearchResult],
    *,
    top_k: int,
    kmeans: Optional[KMeansConfig] = None,
    feature_spec: Optional[FeatureVectorSpec] = None,
) -> ClusteredRecommendationSet:
    """
    Cluster candidates and return diversified ordering.

    Args:
        kb: KnowledgeBase-like (get_fact)
        results: ranked SearchResult list (candidate pool)
        top_k: final number to serve after diversification
        kmeans: KMeans configuration (k, seed, iters)
        feature_spec: which facts to include in vectors
    """
    kmeans = kmeans or KMeansConfig()
    feature_spec = feature_spec or FeatureVectorSpec()

    pool = list(results)
    if not pool:
        return ClusteredRecommendationSet(clusters=tuple(), diversified=tuple(), metadata={"k": 0, "pool_size": 0})

    mbids = [r.mbid for r in pool]
    vectors, vocab = build_feature_vectors(kb, mbids, spec=feature_spec)
    assignments = kmeans_cluster(vectors, config=kmeans)

    # Group results by cluster id.
    by_cluster: Dict[int, List[SearchResult]] = {}
    for r in pool:
        cid = assignments.get(r.mbid, 0)
        by_cluster.setdefault(cid, []).append(r)

    # Rank within cluster and order clusters by best member score.
    cluster_ids = sorted(by_cluster.keys())
    cluster_lists: List[List[SearchResult]] = []
    for cid in cluster_ids:
        cluster_lists.append(_rank_within_cluster(by_cluster[cid]))

    # Sort clusters by priority (best combined_score desc, then mbid).
    ordered = sorted(
        zip(cluster_ids, cluster_lists),
        key=lambda pair: (-_cluster_priority(pair[1])[0], _cluster_priority(pair[1])[1], pair[0]),
    )
    cluster_ids = [cid for cid, _ in ordered]
    cluster_lists = [lst for _, lst in ordered]

    diversified = round_robin_diversify(cluster_lists, top_k=top_k)

    clusters_out = tuple(
        ClusteredResult(cluster_id=cid, members=tuple(members)) for cid, members in zip(cluster_ids, cluster_lists)
    )
    return ClusteredRecommendationSet(
        clusters=clusters_out,
        diversified=tuple(diversified),
        metadata={
            "k": int(kmeans.k),
            "seed": int(kmeans.seed),
            "max_iters": int(kmeans.max_iters),
            "pool_size": len(pool),
            "vocab_size": len(vocab),
        },
    )

