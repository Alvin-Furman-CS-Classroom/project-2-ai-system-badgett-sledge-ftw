"""
Unit tests for Module 3 pipeline (UCS + PreferenceScorer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.survey import PreferenceProfile
from search.pipeline import SearchResult, _min_max_normalize, find_similar


@pytest.fixture
def kb():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def scorer_rock_happy(kb):
    profile = PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=["happy"],
        danceable=None,
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )
    rules = build_rules(profile)
    weights = get_default_weights(rules)
    return PreferenceScorer(rules, weights)


class TestMinMaxNormalize:
    def test_empty(self):
        assert _min_max_normalize([]) == []

    def test_spread(self):
        assert _min_max_normalize([0.0, 10.0]) == [0.0, 1.0]

    def test_equal_values(self):
        assert _min_max_normalize([3.0, 3.0, 3.0]) == [0.5, 0.5, 0.5]

    def test_single_value(self):
        assert _min_max_normalize([42.0]) == [0.5]


class TestFindSimilar:
    def test_excludes_query(self, kb, scorer_rock_happy):
        out = find_similar(kb, "test-mbid-001", scorer_rock_happy, k=4)
        assert all(r.mbid != "test-mbid-001" for r in out)

    def test_returns_search_results(self, kb, scorer_rock_happy):
        out = find_similar(kb, "test-mbid-001", scorer_rock_happy, k=2)
        assert len(out) <= 2
        for r in out:
            assert isinstance(r, SearchResult)
            assert r.path_cost >= 0.0

    def test_sorted_by_combined_desc(self, kb, scorer_rock_happy):
        out = find_similar(kb, "test-mbid-001", scorer_rock_happy, k=4)
        scores = [r.combined_score for r in out]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic(self, kb, scorer_rock_happy):
        a = find_similar(kb, "test-mbid-001", scorer_rock_happy, k=3)
        b = find_similar(kb, "test-mbid-001", scorer_rock_happy, k=3)
        assert a == b

    def test_k_zero_empty(self, kb, scorer_rock_happy):
        assert find_similar(kb, "test-mbid-001", scorer_rock_happy, k=0) == []

    def test_unknown_query_raises(self, kb, scorer_rock_happy):
        with pytest.raises(ValueError, match="Unknown"):
            find_similar(kb, "missing-mbid", scorer_rock_happy, k=1)

    def test_beta_boosts_high_preference(self, kb):
        """Higher beta should not break ordering when only one candidate; use k=3."""
        profile = PreferenceProfile(
            preferred_genres=["rock"],
            preferred_moods=["happy"],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)
        out = find_similar(kb, "test-mbid-001", scorer, k=3, alpha=0.0, beta=1.0)
        # Pure preference sort: combined_score == P_norm contribution only
        prefs = [r.preference_score for r in out]
        assert prefs == sorted(prefs, reverse=True)
