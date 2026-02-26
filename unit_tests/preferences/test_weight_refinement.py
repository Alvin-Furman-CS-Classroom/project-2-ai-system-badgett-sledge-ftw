"""
Unit tests for weight refinement from user ratings (refine_weights_from_ratings).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import PreferenceProfile
from preferences.rules import build_rules, get_default_weights, evaluate_rule
from preferences.ratings import UserRatings, Rating, refine_weights_from_ratings
from preferences.scorer import PreferenceScorer


@pytest.fixture
def kb():
    """Load fixture knowledge base."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def profile_genre_and_danceable():
    """Profile with genre=rock and danceable=danceable (two rules)."""
    return PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=[],
        danceable="danceable",
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )


class TestRefineWeightsFromRatings:
    """Test refine_weights_from_ratings."""

    def test_refine_boosts_rule_for_liked_songs(self, kb, profile_genre_and_danceable):
        # Fixture: 001 = rock, not_danceable; 003 = pop, danceable; 004 = electronic, danceable
        # User likes rock (001), dislikes danceable-only pop (003) -> genre rule should get higher weight
        rules = build_rules(profile_genre_and_danceable)
        initial_weights = get_default_weights(rules)
        assert "genre" in initial_weights
        assert "danceable" in initial_weights

        ratings = UserRatings()
        ratings.add_rating("test-mbid-001", Rating.REALLY_LIKE)  # rock, not_danceable
        ratings.add_rating("test-mbid-003", Rating.DISLIKE)      # pop, danceable

        refined = refine_weights_from_ratings(kb, rules, initial_weights, ratings, alpha=0.2)

        # Genre rule: only 001 satisfies (rating 4). Danceable: only 003 satisfies (rating 1). Avg overall = 2.5.
        # Genre avg_satisfied=4 > 2.5 -> delta positive. Danceable avg_satisfied=1 < 2.5 -> delta negative.
        assert refined["genre"] >= initial_weights["genre"]
        assert refined["danceable"] <= initial_weights["danceable"]

    def test_refine_weights_still_non_negative(self, kb, profile_genre_and_danceable):
        rules = build_rules(profile_genre_and_danceable)
        initial_weights = get_default_weights(rules)
        ratings = UserRatings()
        ratings.add_rating("test-mbid-003", Rating.DISLIKE)  # pop, danceable
        ratings.add_rating("test-mbid-004", Rating.DISLIKE)  # electronic, danceable
        # Both satisfy danceable, neither satisfies genre. So genre gets avg_satisfied=0, danceable gets 1.
        refined = refine_weights_from_ratings(kb, rules, initial_weights, ratings, alpha=0.5, weight_floor=0.01)
        for w in refined.values():
            assert w >= 0.01

    def test_refine_weights_normalized_sum_to_one(self, kb, profile_genre_and_danceable):
        rules = build_rules(profile_genre_and_danceable)
        initial_weights = get_default_weights(rules)
        ratings = UserRatings()
        ratings.add_rating("test-mbid-001", Rating.LIKE)
        ratings.add_rating("test-mbid-003", Rating.LIKE)
        refined = refine_weights_from_ratings(kb, rules, initial_weights, ratings, normalize=True)
        assert abs(sum(refined.values()) - 1.0) < 1e-9

    def test_refine_empty_ratings_returns_unchanged(self, kb, profile_genre_and_danceable):
        rules = build_rules(profile_genre_and_danceable)
        initial_weights = get_default_weights(rules)
        ratings = UserRatings()
        refined = refine_weights_from_ratings(kb, rules, initial_weights, ratings)
        assert refined == initial_weights

    def test_rock_song_scores_higher_after_refinement(self, kb, profile_genre_and_danceable):
        rules = build_rules(profile_genre_and_danceable)
        initial_weights = get_default_weights(rules)
        scorer_before = PreferenceScorer(rules, initial_weights)

        ratings = UserRatings()
        ratings.add_rating("test-mbid-001", Rating.REALLY_LIKE)  # rock
        ratings.add_rating("test-mbid-003", Rating.DISLIKE)      # pop
        refined_weights = refine_weights_from_ratings(kb, rules, initial_weights, ratings, alpha=0.2)
        scorer_after = PreferenceScorer(rules, refined_weights)

        score_001_before = scorer_before.score("test-mbid-001", kb)
        score_001_after = scorer_after.score("test-mbid-001", kb)
        # 001 satisfies genre only; we boosted genre weight, so 001's score should go up
        assert score_001_after >= score_001_before
