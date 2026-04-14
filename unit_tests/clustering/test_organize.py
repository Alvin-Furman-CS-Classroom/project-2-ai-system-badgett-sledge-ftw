import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from knowledge_base_wrapper import KnowledgeBase
from search.pipeline import SearchResult

from clustering.kmeans import KMeansConfig
from clustering.organize import cluster_and_organize, round_robin_diversify


def test_round_robin_basic():
    clusters = [
        [SearchResult("a", 0.0, 0.0, 3.0), SearchResult("b", 0.0, 0.0, 1.0)],
        [SearchResult("c", 0.0, 0.0, 2.0)],
    ]
    out = round_robin_diversify(clusters, top_k=3)
    assert [r.mbid for r in out] == ["a", "c", "b"]


def test_cluster_and_organize_returns_top_k_and_metadata():
    kb_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    kb = KnowledgeBase(str(kb_path))

    # Use real MBIDs from fixture so feature extraction works.
    results = [
        SearchResult("test-mbid-002", 1.0, 0.2, 0.9),
        SearchResult("test-mbid-003", 1.1, 0.1, 0.8),
        SearchResult("test-mbid-004", 1.2, 0.3, 0.7),
        SearchResult("test-mbid-005", 1.3, 0.4, 0.6),
    ]
    out = cluster_and_organize(
        kb,
        results,
        top_k=3,
        kmeans=KMeansConfig(k=2, seed=42, max_iters=10),
    )
    assert len(out.diversified) == 3
    assert out.metadata["pool_size"] == 4
    assert "vocab_size" in out.metadata

