"""
Unit tests for Uniform Cost Search (Module 3).
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from search.costs import DissimilarityWeights
from search.ucs import ucs_topk


@pytest.fixture
def kb_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def kb_linear_loudness():
    """Four songs share one genre; path cost from q follows loudness gaps only."""
    minimal = {
        "songs": {"q": {}, "a": {}, "b": {}, "c": {}},
        "facts": {
            "has_genre": {
                "q": ["rock"],
                "a": ["rock"],
                "b": ["rock"],
                "c": ["rock"],
            },
            "has_loudness": {"q": -10.0, "a": -10.0, "b": -5.0, "c": -20.0},
        },
        "indexes": {
            "by_genre": {"rock": ["q", "a", "b", "c"]},
            "by_danceable": {},
            "by_voice_instrumental": {},
            "by_timbre": {},
            "by_mood": {},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(minimal, f)
        path = f.name
    try:
        yield KnowledgeBase(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestUcsTopkFixtureKb:
    def test_excludes_query(self, kb_fixture):
        out = ucs_topk(kb_fixture, "test-mbid-001", k=3)
        ids = [mbid for mbid, _ in out]
        assert "test-mbid-001" not in ids

    def test_length_at_most_k(self, kb_fixture):
        assert len(ucs_topk(kb_fixture, "test-mbid-001", k=2)) <= 2

    def test_non_decreasing_cost(self, kb_fixture):
        out = ucs_topk(kb_fixture, "test-mbid-001", k=4)
        costs = [c for _, c in out]
        assert costs == sorted(costs)

    def test_deterministic(self, kb_fixture):
        a = ucs_topk(kb_fixture, "test-mbid-001", k=3)
        b = ucs_topk(kb_fixture, "test-mbid-001", k=3)
        assert a == b

    def test_unknown_mbid_raises(self, kb_fixture):
        with pytest.raises(ValueError, match="Unknown"):
            ucs_topk(kb_fixture, "not-a-real-mbid", k=1)

    def test_k_zero_empty(self, kb_fixture):
        assert ucs_topk(kb_fixture, "test-mbid-001", k=0) == []


class TestUcsTopkLinear:
    def test_orders_by_direct_edge_cost(self, kb_linear_loudness):
        w = DissimilarityWeights()
        out = ucs_topk(kb_linear_loudness, "q", k=3, weights=w)
        assert [mbid for mbid, _ in out] == ["a", "b", "c"]
        costs = [c for _, c in out]
        assert costs[0] < costs[1] < costs[2]

    def test_k_larger_than_graph_returns_three(self, kb_linear_loudness):
        out = ucs_topk(kb_linear_loudness, "q", k=100)
        assert len(out) == 3


class TestUcsMaxDegree:
    def test_large_max_degree_matches_unlimited_on_clique(self, kb_linear_loudness):
        """When cap >= degree, behavior matches uncapped expansion."""
        w = DissimilarityWeights()
        full = ucs_topk(kb_linear_loudness, "q", k=3, max_degree=None, weights=w)
        capped = ucs_topk(kb_linear_loudness, "q", k=3, max_degree=10, weights=w)
        assert full == capped
