"""
Integration tests for Module 2: end-to-end hill-climbing preference flow.

Tests: profile from survey-like input -> rules + weights -> initial batch ->
mock ratings -> refine -> next batch (adaptive) -> mock ratings -> refine ->
scorer on multiple songs. Asserts ordering is sensible and songs similar
to liked ones rank higher after refinement; second batch differs from first.
"""

import sys
from pathlib import Path

# Add project root and src for imports
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import PreferenceProfile
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.sampling import sample_songs, sample_next_batch
from preferences.ratings import UserRatings, Rating, refine_weights_from_ratings


def _fixture_kb_path() -> Path:
    return _project_root / "unit_tests" / "fixtures" / "test_knowledge_base.json"


@pytest.fixture
def kb():
    """Load fixture knowledge base."""
    path = _fixture_kb_path()
    if not path.exists():
        pytest.skip(f"Fixture KB not found: {path}")
    return KnowledgeBase(str(path))


@pytest.fixture
def profile_rock_and_happy():
    """Profile: prefer rock and happy mood (001 and 003 match genre or mood; 001 = rock+happy, 003 = pop+happy)."""
    return PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=["happy"],
        danceable=None,
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )


class TestModule2HillClimbingIntegration:
    """End-to-end: survey-like profile -> rules -> batch -> rate -> refine -> next batch -> rate -> refine -> score."""

    def test_full_loop_ordering_sensible(self, kb, profile_rock_and_happy):
        # 1) Build profile from survey-like input (we use fixture profile)
        profile = profile_rock_and_happy
        rules = build_rules(profile)
        assert len(rules) >= 2  # genre, mood
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)

        # 2) Get initial batch (score-based)
        batch1 = sample_songs(kb, n=2, method="score_based", scorer=scorer, seed=42)
        assert len(batch1) <= 2
        assert len(batch1) == len(set(batch1))

        # 3) Apply mock ratings: like rock song (001 or 002), dislike pop (003)
        # Fixture: 001 = rock+alt+happy, 002 = rock+sad, 003 = pop+happy, 004 = electronic+relaxed
        ratings = UserRatings()
        for mbid in batch1:
            if mbid == "test-mbid-001" or mbid == "test-mbid-002":
                ratings.add_rating(mbid, Rating.REALLY_LIKE)
            else:
                ratings.add_rating(mbid, Rating.DISLIKE)

        # 4) Refine weights
        weights = refine_weights_from_ratings(kb, rules, weights, ratings, alpha=0.2)
        scorer = PreferenceScorer(rules, weights)

        # 5) Get next batch (adaptive), excluding already-rated
        already_rated = list(ratings.ratings.keys())
        batch2 = sample_next_batch(kb, n=2, scorer=scorer, already_rated_mbids=already_rated, seed=42)
        # Second batch should not include any from batch1 (adaptive excludes already-rated)
        for mbid in batch2:
            assert mbid not in already_rated
        assert set(batch2).isdisjoint(set(batch1))

        # 6) Apply mock ratings again (e.g. like one, dislike one)
        for mbid in batch2:
            if mbid == "test-mbid-001" or mbid == "test-mbid-002":
                ratings.add_rating(mbid, Rating.LIKE)
            else:
                ratings.add_rating(mbid, Rating.DISLIKE)

        # 7) Refine again
        weights = refine_weights_from_ratings(kb, rules, weights, ratings, alpha=0.15)
        scorer = PreferenceScorer(rules, weights)

        # 8) Run scorer on all songs; assert ordering sensible
        all_mbids = kb.get_all_songs()
        scored = [(mbid, scorer.score(mbid, kb)) for mbid in all_mbids]
        scored.sort(key=lambda x: x[1], reverse=True)
        scores_by_mbid = dict(scored)

        # Rock songs (001, 002) should rank at or above pop (003) and electronic (004) after we liked rock
        rock_scores = [scores_by_mbid.get("test-mbid-001", -1), scores_by_mbid.get("test-mbid-002", -1)]
        pop_score = scores_by_mbid.get("test-mbid-003", -1)
        electronic_score = scores_by_mbid.get("test-mbid-004", -1)
        assert max(rock_scores) >= pop_score
        assert max(rock_scores) >= electronic_score

    def test_songs_similar_to_liked_rank_higher_after_refinement(self, kb):
        """After liking rock songs and disliking pop, rock songs should score higher than pop."""
        profile = PreferenceProfile(
            preferred_genres=["rock", "pop"],
            preferred_moods=["happy"],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        scorer_before = PreferenceScorer(rules, weights)

        ratings = UserRatings()
        ratings.add_rating("test-mbid-001", Rating.REALLY_LIKE)  # rock, happy
        ratings.add_rating("test-mbid-003", Rating.DISLIKE)     # pop, happy

        weights_refined = refine_weights_from_ratings(kb, rules, weights, ratings, alpha=0.2)
        scorer_after = PreferenceScorer(rules, weights_refined)

        score_001_before = scorer_before.score("test-mbid-001", kb)
        score_001_after = scorer_after.score("test-mbid-001", kb)
        score_003_after = scorer_after.score("test-mbid-003", kb)
        # 001 (liked) should score at least as high as 003 (disliked) after refinement
        assert score_001_after >= score_003_after
        # 001 should not decrease after we liked it (genre/mood rules it satisfies get boosted)
        assert score_001_after >= score_001_before

    def test_second_batch_disjoint_from_first(self, kb, profile_rock_and_happy):
        """Adaptive second batch should exclude songs from the first batch."""
        profile = profile_rock_and_happy
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)

        batch1 = sample_songs(kb, n=2, method="score_based", scorer=scorer, seed=1)
        ratings = UserRatings()
        for mbid in batch1:
            ratings.add_rating(mbid, Rating.LIKE)

        weights = refine_weights_from_ratings(kb, rules, weights, ratings, alpha=0.1)
        scorer = PreferenceScorer(rules, weights)
        already_rated = list(ratings.ratings.keys())
        batch2 = sample_next_batch(kb, n=2, scorer=scorer, already_rated_mbids=already_rated, seed=1)

        for mbid in batch2:
            assert mbid not in batch1
        assert len(batch2) <= 2
