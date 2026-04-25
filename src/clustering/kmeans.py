"""
Deterministic K-means clustering for Module 5.

We implement a small K-means to avoid new heavy dependencies. Determinism rules:
- Stable input ordering (MBID sort) by caller or within this module.
- Seeded centroid initialization using Python's random.Random(seed).
- Stable tie-breaks (lower centroid index wins on equal distance).
- Stable empty-cluster reinitialization (lowest MBID not currently a centroid).
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class KMeansConfig:
    k: int = 5
    max_iters: int = 25
    seed: int = 343


def _sq_dist(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((a[i] - b[i]) ** 2 for i in range(len(a)))


def _mean(vectors: List[Sequence[float]]) -> List[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += float(v[i])
    n = float(len(vectors))
    return [x / n for x in out]


def kmeans_cluster(
    vectors: Dict[str, Sequence[float]],
    *,
    config: KMeansConfig,
) -> Dict[str, int]:
    """
    Cluster points into k groups.

    Args:
        vectors: mbid -> vector
        config: KMeansConfig

    Returns:
        assignments: mbid -> cluster_id in [0, k-1]
    """
    mbids = sorted(vectors.keys())
    n = len(mbids)
    if n == 0:
        return {}

    k = int(config.k)
    if k <= 1:
        return {m: 0 for m in mbids}
    if k > n:
        k = n

    rng = Random(int(config.seed))

    # Init centroids by sampling MBIDs (deterministic under seed) then taking their vectors.
    init_mbids = mbids[:]  # stable list
    rng.shuffle(init_mbids)
    centroid_mbids = init_mbids[:k]
    centroids: List[List[float]] = [list(vectors[m]) for m in centroid_mbids]

    assignments: Dict[str, int] = {}

    for _ in range(int(config.max_iters)):
        changed = False

        # Assign step
        clusters: List[List[str]] = [[] for _ in range(k)]
        for m in mbids:
            v = vectors[m]
            best_c = 0
            best_d = _sq_dist(v, centroids[0])
            for c in range(1, k):
                d = _sq_dist(v, centroids[c])
                if d < best_d or (d == best_d and c < best_c):
                    best_d = d
                    best_c = c
            prev = assignments.get(m)
            if prev is None or prev != best_c:
                changed = True
            assignments[m] = best_c
            clusters[best_c].append(m)

        # Update step
        used_centroids = set()
        for c in range(k):
            if clusters[c]:
                centroids[c] = _mean([vectors[m] for m in clusters[c]])
                used_centroids.add(c)
            else:
                # Empty cluster: reinitialize to a stable point not already used as a centroid.
                # Choose the lowest MBID not in any current centroid_mbids list.
                current = set(centroid_mbids)
                replacement = None
                for m in mbids:
                    if m not in current:
                        replacement = m
                        break
                if replacement is None:
                    replacement = mbids[0]
                centroid_mbids[c] = replacement
                centroids[c] = list(vectors[replacement])

        if not changed:
            break

    return assignments

