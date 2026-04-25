"""
Unit tests for neighbor generation and degree cap (Module 3 graph).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from search.costs import pairwise_dissimilarity
from search.graph import capped_neighbors, neighbor_candidates


@pytest.fixture
def kb():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


class TestNeighborCandidates:
    def test_excludes_self(self, kb):
        n = neighbor_candidates(kb, "test-mbid-001")
        assert "test-mbid-001" not in n

    def test_shares_genre_rock(self, kb):
        n = neighbor_candidates(kb, "test-mbid-001")
        assert "test-mbid-002" in n  # both rock

    def test_shares_mood_relaxed(self, kb):
        n = neighbor_candidates(kb, "test-mbid-001")
        assert "test-mbid-004" in n  # relaxed shared

    def test_danceable_bucket(self, kb):
        n = neighbor_candidates(kb, "test-mbid-003")
        assert "test-mbid-004" in n  # both danceable

    def test_union_multiple_indexes(self, kb):
        n = neighbor_candidates(kb, "test-mbid-001")
        assert len(n) >= 3  # 002, 003, 004 all connect via some index


class TestCappedNeighbors:
    def test_order_by_increasing_cost(self, kb):
        cap = capped_neighbors(kb, "test-mbid-001", max_degree=3)
        assert len(cap) <= 3
        costs = [pairwise_dissimilarity(kb, "test-mbid-001", m) for m in cap]
        assert costs == sorted(costs)

    def test_deterministic_ties(self, kb):
        a = capped_neighbors(kb, "test-mbid-001", max_degree=10)
        b = capped_neighbors(kb, "test-mbid-001", max_degree=10)
        assert a == b

    def test_none_cap_returns_all_sorted(self, kb):
        full = capped_neighbors(kb, "test-mbid-001", max_degree=None)
        uncapped = neighbor_candidates(kb, "test-mbid-001")
        assert len(full) == len(uncapped)
        assert set(full) == uncapped

    def test_negative_cap_returns_all(self, kb):
        """Negative max_degree treated as unlimited (same as None)."""
        full = capped_neighbors(kb, "test-mbid-001", max_degree=-1)
        assert len(full) == len(neighbor_candidates(kb, "test-mbid-001"))
