"""
Unit tests for pairwise dissimilarity (Module 3 edge costs).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from search.costs import DissimilarityWeights, jaccard_distance, pairwise_dissimilarity


@pytest.fixture
def kb():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


class TestJaccardDistance:
    def test_identical(self):
        assert jaccard_distance({"a", "b"}, {"a", "b"}) == 0.0

    def test_disjoint(self):
        assert jaccard_distance({"a"}, {"b"}) == 1.0

    def test_both_empty(self):
        assert jaccard_distance(set(), set()) == 0.0

    def test_one_empty(self):
        assert jaccard_distance({"a"}, set()) == 1.0


class TestPairwiseDissimilarity:
    def test_same_song_zero(self, kb):
        assert pairwise_dissimilarity(kb, "test-mbid-001", "test-mbid-001") == 0.0

    def test_symmetric(self, kb):
        a = pairwise_dissimilarity(kb, "test-mbid-001", "test-mbid-003")
        b = pairwise_dissimilarity(kb, "test-mbid-003", "test-mbid-001")
        assert a == b

    def test_non_negative(self, kb):
        for m1 in kb.get_all_songs():
            for m2 in kb.get_all_songs():
                assert pairwise_dissimilarity(kb, m1, m2) >= 0.0

    def test_identical_features_low_cost(self, kb):
        """Duplicate path: same mbid already 0; different songs always have some cost in fixture."""
        w = DissimilarityWeights()
        d = pairwise_dissimilarity(kb, "test-mbid-001", "test-mbid-002", w)
        # rock + rock overlap, but mood/timbre/genre Jaccard not identical -> > 0
        assert d > 0.0

    def test_weights_scale_genre(self, kb):
        w1 = DissimilarityWeights(genre=1.0)
        w2 = DissimilarityWeights(genre=10.0)
        d1 = pairwise_dissimilarity(kb, "test-mbid-001", "test-mbid-003", w1)
        d2 = pairwise_dissimilarity(kb, "test-mbid-001", "test-mbid-003", w2)
        assert d2 > d1


class TestCollaboratorReward:
    def test_reward_reduces_cost_when_facts_present(self):
        """Shared producer lowers dissimilarity vs same loudness gap without reward."""
        minimal = {
            "songs": {"a": {}, "b": {}},
            "facts": {
                "has_genre": {"a": ["rock"], "b": ["rock"]},
                "has_mood": {"a": ["happy"], "b": ["happy"]},
                "has_loudness": {"a": -5.0, "b": -8.0},
                "has_producer": {"a": ["P1", "Shared"], "b": ["Shared", "P2"]},
            },
            "indexes": {
                "by_genre": {"rock": ["a", "b"]},
                "by_mood": {"happy": ["a", "b"]},
                "by_danceable": {},
                "by_voice_instrumental": {},
                "by_timbre": {},
            },
        }
        import json
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(minimal, f)
            path = f.name
        try:
            k = KnowledgeBase(path)
            w0 = DissimilarityWeights(collaborator_reward_per_shared=0.0)
            w1 = DissimilarityWeights(collaborator_reward_per_shared=3.0)
            base = pairwise_dissimilarity(k, "a", "b", w0)
            with_reward = pairwise_dissimilarity(k, "a", "b", w1)
            assert base > 0.0
            assert with_reward < base
            assert with_reward >= 0.0
        finally:
            Path(path).unlink(missing_ok=True)
