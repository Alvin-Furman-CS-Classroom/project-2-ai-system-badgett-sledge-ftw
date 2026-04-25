"""
Integration tests for Module 3: KnowledgeBase + PreferenceScorer + find_similar.

Exercises: KB fixture -> rules/scorer from profile -> UCS pipeline -> ranked
``SearchResult`` list. Asserts query exclusion, length bounds, and that when
preference weight dominates (alpha=0), higher rule-satisfaction songs rank above
lower ones among returned candidates.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.survey import PreferenceProfile
from search.pipeline import SearchResult, find_similar


def _fixture_kb_path() -> Path:
    return _project_root / "unit_tests" / "fixtures" / "test_knowledge_base.json"


@pytest.fixture
def kb():
    path = _fixture_kb_path()
    if not path.exists():
        pytest.skip(f"Fixture KB not found: {path}")
    return KnowledgeBase(str(path))


@pytest.fixture
def profile_genre_rock_only():
    """Only genre rule: rock matches 001 and 002, not 003 or 004."""
    return PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=[],
        danceable=None,
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )


class TestModule3FindSimilarIntegration:
    """End-to-end: KB + Module 2 scorer + Module 3 ``find_similar``."""

    def test_returns_search_results_and_excludes_query(self, kb, profile_genre_rock_only):
        rules = build_rules(profile_genre_rock_only)
        weights = get_default_weights(rules)
        scorer = PreferenceScorer(rules, weights)

        out = find_similar(kb, "test-mbid-001", scorer, k=3)
        assert len(out) <= 3
        assert all(isinstance(r, SearchResult) for r in out)
        assert all(r.mbid != "test-mbid-001" for r in out)

    def test_deterministic_repeat(self, kb, profile_genre_rock_only):
        rules = build_rules(profile_genre_rock_only)
        scorer = PreferenceScorer(rules, get_default_weights(rules))
        a = find_similar(kb, "test-mbid-001", scorer, k=3)
        b = find_similar(kb, "test-mbid-001", scorer, k=3)
        assert a == b

    def test_pure_preference_orders_by_scorer_when_alpha_zero(self, kb, profile_genre_rock_only):
        """
        With alpha=0, ranking follows normalized preference only; rock (002) should
        rank above pop (003) when both appear in the UCS candidate set.
        """
        rules = build_rules(profile_genre_rock_only)
        scorer = PreferenceScorer(rules, get_default_weights(rules))

        out = find_similar(
            kb,
            "test-mbid-001",
            scorer,
            k=4,
            alpha=0.0,
            beta=1.0,
        )
        mbids = [r.mbid for r in out]
        if "test-mbid-002" in mbids and "test-mbid-003" in mbids:
            assert mbids.index("test-mbid-002") < mbids.index("test-mbid-003")

    def test_combined_scores_non_increasing(self, kb, profile_genre_rock_only):
        rules = build_rules(profile_genre_rock_only)
        scorer = PreferenceScorer(rules, get_default_weights(rules))
        out = find_similar(kb, "test-mbid-001", scorer, k=3, alpha=1.0, beta=1.0)
        scores = [r.combined_score for r in out]
        assert scores == sorted(scores, reverse=True)

    def test_unknown_query_raises(self, kb, profile_genre_rock_only):
        rules = build_rules(profile_genre_rock_only)
        scorer = PreferenceScorer(rules, get_default_weights(rules))
        with pytest.raises(ValueError, match="Unknown"):
            find_similar(kb, "not-in-kb", scorer, k=1)
