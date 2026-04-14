"""
Module 5: Clustering (K-means) to diversify recommendations.

This package provides a deterministic post-retrieval organization layer:
- Build feature vectors for candidate MBIDs from KB facts
- Cluster candidates with deterministic K-means
- Produce a diversified (round-robin) ordering across clusters

It is intentionally optional and does not modify Module 3/4 retrieval/scoring APIs.
"""

from .features import FeatureVectorSpec, build_feature_vectors
from .kmeans import KMeansConfig, kmeans_cluster
from .organize import ClusteredResult, ClusteredRecommendationSet, cluster_and_organize

__all__ = [
    "FeatureVectorSpec",
    "build_feature_vectors",
    "KMeansConfig",
    "kmeans_cluster",
    "ClusteredResult",
    "ClusteredRecommendationSet",
    "cluster_and_organize",
]

