"""
Unit tests for rules and weight vector (build_rules, evaluate_rule, get_default_weights).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import PreferenceProfile
from preferences.rules import Rule, build_rules, evaluate_rule, get_default_weights


@pytest.fixture
def kb():
    """Load fixture knowledge base."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


class TestBuildRules:
    """Test building rules from a preference profile."""

    def test_build_rules_full_profile(self):
        profile = PreferenceProfile(
            preferred_genres=["rock", "pop"],
            preferred_moods=["happy"],
            danceable="danceable",
            voice_instrumental="voice",
            timbre="bright",
            loudness_min=-10.0,
            loudness_max=-5.0,
        )
        rules = build_rules(profile)
        rule_ids = [r.rule_id for r in rules]
        assert "genre" in rule_ids
        assert "mood" in rule_ids
        assert "danceable" in rule_ids
        assert "voice_instrumental" in rule_ids
        assert "timbre" in rule_ids
        assert "loudness" in rule_ids
        assert len(rules) == 6

    def test_build_rules_genre_and_mood_only(self):
        profile = PreferenceProfile(
            preferred_genres=["rock"],
            preferred_moods=[],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        assert len(rules) == 1
        assert rules[0].rule_id == "genre"
        assert rules[0].target == ["rock"]

    def test_build_rules_empty_profile(self):
        profile = PreferenceProfile(
            preferred_genres=[],
            preferred_moods=[],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=None,
            loudness_max=None,
        )
        rules = build_rules(profile)
        assert rules == []

    def test_build_rules_loudness_ordering(self):
        profile = PreferenceProfile(
            preferred_genres=[],
            preferred_moods=[],
            danceable=None,
            voice_instrumental=None,
            timbre=None,
            loudness_min=-5.0,
            loudness_max=-15.0,
        )
        rules = build_rules(profile)
        assert len(rules) == 1
        assert rules[0].rule_id == "loudness"
        assert rules[0].target == (-15.0, -5.0)


class TestEvaluateRule:
    """Test rule evaluation against the fixture KB."""

    def test_genre_rule_match(self, kb):
        rule = Rule(rule_id="genre", fact_type="has_genre", target=["rock"])
        assert evaluate_rule(rule, "test-mbid-001", kb) == 1.0  # rock, alternative
        assert evaluate_rule(rule, "test-mbid-002", kb) == 1.0  # rock
        assert evaluate_rule(rule, "test-mbid-003", kb) == 0.0  # pop (no match)
        assert evaluate_rule(rule, "test-mbid-004", kb) == 0.0  # electronic (no match)

    def test_genre_rule_no_match(self, kb):
        rule = Rule(rule_id="genre", fact_type="has_genre", target=["jazz"])
        assert evaluate_rule(rule, "test-mbid-001", kb) == 0.0
        assert evaluate_rule(rule, "test-mbid-003", kb) == 0.0

    def test_mood_rule_match(self, kb):
        rule = Rule(rule_id="mood", fact_type="has_mood", target=["happy"])
        assert evaluate_rule(rule, "test-mbid-001", kb) == 1.0
        assert evaluate_rule(rule, "test-mbid-003", kb) == 1.0
        assert evaluate_rule(rule, "test-mbid-002", kb) == 0.0  # sad

    def test_danceable_rule(self, kb):
        rule = Rule(rule_id="danceable", fact_type="has_danceable", target="danceable")
        assert evaluate_rule(rule, "test-mbid-003", kb) == 1.0
        assert evaluate_rule(rule, "test-mbid-004", kb) == 1.0
        assert evaluate_rule(rule, "test-mbid-001", kb) == 0.0

    def test_loudness_rule(self, kb):
        rule = Rule(rule_id="loudness", fact_type="has_loudness", target=(-12.0, -5.0))
        # test-mbid-001: -8.5, test-mbid-003: -5.8 -> in range
        assert evaluate_rule(rule, "test-mbid-001", kb) == 1.0
        assert evaluate_rule(rule, "test-mbid-003", kb) == 1.0
        # test-mbid-004: -12.0 -> in range
        assert evaluate_rule(rule, "test-mbid-004", kb) == 1.0
        # test-mbid-002: -10.2 -> in range
        assert evaluate_rule(rule, "test-mbid-002", kb) == 1.0

    def test_loudness_rule_out_of_range(self, kb):
        rule = Rule(rule_id="loudness", fact_type="has_loudness", target=(-20.0, -15.0))
        # All fixture songs are -5.8 to -12
        assert evaluate_rule(rule, "test-mbid-001", kb) == 0.0
        assert evaluate_rule(rule, "test-mbid-003", kb) == 0.0


class TestGetDefaultWeights:
    """Test default weight vector."""

    def test_equal_weights_normalized(self):
        rules = [
            Rule("genre", "has_genre", ["rock"]),
            Rule("mood", "has_mood", ["happy"]),
        ]
        w = get_default_weights(rules, normalize=True)
        assert w["genre"] == 0.5
        assert w["mood"] == 0.5
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_equal_weights_not_normalized(self):
        rules = [Rule("genre", "has_genre", ["rock"])]
        w = get_default_weights(rules, normalize=False)
        assert w["genre"] == 1.0

    def test_empty_rules(self):
        w = get_default_weights([], normalize=True)
        assert w == {}
