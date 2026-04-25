import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clustering.kmeans import KMeansConfig, kmeans_cluster


def test_kmeans_deterministic_with_seed():
    vectors = {
        "a": [0.0, 0.0],
        "b": [0.1, 0.0],
        "c": [10.0, 10.0],
        "d": [10.1, 10.0],
    }
    cfg = KMeansConfig(k=2, seed=123, max_iters=10)
    a1 = kmeans_cluster(vectors, config=cfg)
    a2 = kmeans_cluster(vectors, config=cfg)
    assert a1 == a2


def test_kmeans_k_greater_than_n_caps():
    vectors = {"a": [0.0], "b": [1.0]}
    cfg = KMeansConfig(k=10, seed=1, max_iters=5)
    out = kmeans_cluster(vectors, config=cfg)
    assert set(out.keys()) == {"a", "b"}
    assert set(out.values()) <= {0, 1}


def test_kmeans_k_one_single_cluster():
    vectors = {"a": [0.0], "b": [1.0]}
    cfg = KMeansConfig(k=1, seed=1, max_iters=5)
    out = kmeans_cluster(vectors, config=cfg)
    assert set(out.values()) == {0}

