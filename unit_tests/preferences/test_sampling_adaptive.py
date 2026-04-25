"""
Unit tests for adaptive (hill-climbing) batch sampling (sample_next_batch).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import PreferenceProfile
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.sampling import sample_next_batch


@pytest.fixture
def kb():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def scorer(kb):
    profile = PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=[],
        danceable="danceable",
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )
    rules = build_rules(profile)
    weights = get_default_weights(rules)
    return PreferenceScorer(rules, weights)


class TestSampleNextBatch:
    """Test sample_next_batch (adaptive batch)."""

    def test_excludes_already_rated(self, kb, scorer):
        already_rated = ["test-mbid-001", "test-mbid-002"]
        batch = sample_next_batch(kb, n=3, scorer=scorer, already_rated_mbids=already_rated, seed=42)
        for mbid in batch:
            assert mbid not in already_rated
        assert len(batch) <= 3

    def test_returns_at_most_n(self, kb, scorer):
        batch = sample_next_batch(kb, n=10, scorer=scorer, already_rated_mbids=[], seed=1)
        assert len(batch) <= 10
        # Fixture has 4 songs
        assert len(batch) == 4

    def test_no_duplicates(self, kb, scorer):
        batch = sample_next_batch(kb, n=5, scorer=scorer, already_rated_mbids=[], seed=7)
        assert len(batch) == len(set(batch))

    def test_when_all_rated_returns_empty_or_remaining(self, kb, scorer):
        all_mbids = kb.get_all_songs()
        batch = sample_next_batch(kb, n=2, scorer=scorer, already_rated_mbids=all_mbids, seed=0)
        assert len(batch) == 0
