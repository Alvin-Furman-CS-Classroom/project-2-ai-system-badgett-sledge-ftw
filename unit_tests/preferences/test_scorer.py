"""
Unit tests for PreferenceScorer (score, score_all).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import PreferenceProfile
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer


@pytest.fixture
def kb():
    """Load fixture knowledge base."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def profile_rock_danceable():
    """Profile that prefers rock and danceable."""
    return PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=[],
        danceable="danceable",
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )


@pytest.fixture
def scorer_rock_danceable(profile_rock_danceable):
    """Scorer with rules for rock + danceable."""
    rules = build_rules(profile_rock_danceable)
    weights = get_default_weights(rules)
    return PreferenceScorer(rules, weights)


class TestPreferenceScorer:
    """Test PreferenceScorer score and score_all."""

    def test_score_higher_for_full_match(self, kb, scorer_rock_danceable):
        # test-mbid-003: pop, danceable -> only danceable rule matches (genre fails)
        # test-mbid-001: rock, alternative, not_danceable -> only genre matches
        # No song in fixture is both rock AND danceable; so best is one rule match.
        scores_003 = scorer_rock_danceable.score("test-mbid-003", kb)
        scores_001 = scorer_rock_danceable.score("test-mbid-001", kb)
        assert scores_003 > 0
        assert scores_001 > 0
        # 003: danceable=1, genre=0 -> 0.5; 001: danceable=0, genre=1 -> 0.5
        assert abs(scores_003 - 0.5) < 1e-9
        assert abs(scores_001 - 0.5) < 1e-9

    def test_score_zero_when_no_match(self, kb):
        profile = PreferenceProfile(
            preferred_genres=["jazz"],
            preferred_moods=[],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)
        # All fixture songs are rock/pop/electronic
        assert scorer.score("test-mbid-001", kb) == 0.0
        assert scorer.score("test-mbid-004", kb) == 0.0

    def test_score_all_returns_list_of_tuples(self, kb, scorer_rock_danceable):
        mbids = ["test-mbid-001", "test-mbid-002", "test-mbid-003", "test-mbid-004"]
        result = scorer_rock_danceable.score_all(mbids, kb)
        assert len(result) == 4
        for mbid, score in result:
            assert mbid in mbids
            assert isinstance(score, (int, float))
            assert score >= 0.0

    def test_score_all_empty_list(self, kb, scorer_rock_danceable):
        result = scorer_rock_danceable.score_all([], kb)
        assert result == []

    def test_scorer_with_empty_rules(self, kb):
        scorer = PreferenceScorer(rules=[], weights={})
        assert scorer.score("test-mbid-001", kb) == 0.0
        assert scorer.score_all(["test-mbid-001"], kb) == [("test-mbid-001", 0.0)]

    def test_song_matching_all_rules_scores_highest(self, kb):
        # Profile: genre rock OR pop, danceable, mood happy -> 003 matches all (pop, danceable, happy)
        profile = PreferenceProfile(
            preferred_genres=["rock", "pop"],
            preferred_moods=["happy"],
            danceable="danceable",
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)
        results = scorer.score_all(
            ["test-mbid-001", "test-mbid-002", "test-mbid-003", "test-mbid-004"], kb
        )
        scores_by_mbid = dict(results)
        # 001: rock+alt, not_danceable, happy+relaxed -> genre=1, danceable=0, mood=1 -> 2/3
        # 003: pop, danceable, happy+party -> genre=1, danceable=1, mood=1 -> 3/3
        assert scores_by_mbid["test-mbid-003"] >= scores_by_mbid["test-mbid-002"]
        assert scores_by_mbid["test-mbid-003"] >= scores_by_mbid["test-mbid-004"]
        assert scores_by_mbid["test-mbid-003"] == pytest.approx(1.0)
