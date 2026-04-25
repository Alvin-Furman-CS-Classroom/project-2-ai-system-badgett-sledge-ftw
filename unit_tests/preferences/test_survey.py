"""
Unit tests for survey and preference profile (Module 2).

Covers: build profile from dict (collect_survey_from_dict), validation of
allowed categories (danceable, voice_instrumental, timbre) and optional
genre/mood validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from preferences.survey import (
    PreferenceProfile,
    collect_survey_from_dict,
)


class TestBuildProfileFromDict:
    """Build PreferenceProfile from a dictionary of answers."""

    def test_minimal_dict_produces_profile(self):
        answers = {"genres": [], "moods": [], "danceable": "any", "voice_instrumental": "any", "timbre": "any", "loudness": "any"}
        profile = collect_survey_from_dict(answers)
        assert isinstance(profile, PreferenceProfile)
        assert profile.preferred_genres == []
        assert profile.preferred_moods == []
        assert profile.danceable is None
        assert profile.voice_instrumental is None
        assert profile.timbre is None
        assert profile.loudness_min is None
        assert profile.loudness_max is None

    def test_full_dict_produces_profile_with_values(self):
        answers = {
            "genres": ["rock", "pop"],
            "moods": ["happy"],
            "danceable": "danceable",
            "voice_instrumental": "voice",
            "timbre": "bright",
            "loudness": "moderate",
        }
        profile = collect_survey_from_dict(answers)
        assert profile.preferred_genres == ["rock", "pop"]
        assert profile.preferred_moods == ["happy"]
        assert profile.danceable == "danceable"
        assert profile.voice_instrumental == "voice"
        assert profile.timbre == "bright"
        assert profile.loudness_min == -12.0
        assert profile.loudness_max == -8.0
        assert profile.has_loudness_preference() is True

    def test_loudness_quiet_sets_range(self):
        answers = {"genres": [], "moods": [], "danceable": "any", "voice_instrumental": "any", "timbre": "any", "loudness": "quiet"}
        profile = collect_survey_from_dict(answers)
        assert profile.loudness_min == -15.0
        assert profile.loudness_max == -12.0


class TestProfileValidation:
    """Validation of allowed categories (danceable, voice_instrumental, timbre)."""

    def test_invalid_danceable_raises(self):
        answers = {"genres": [], "moods": [], "danceable": "invalid", "voice_instrumental": "any", "timbre": "any", "loudness": "any"}
        with pytest.raises(ValueError, match="Invalid danceable"):
            collect_survey_from_dict(answers)

    def test_invalid_voice_instrumental_raises(self):
        answers = {"genres": [], "moods": [], "danceable": "any", "voice_instrumental": "both", "timbre": "any", "loudness": "any"}
        with pytest.raises(ValueError, match="Invalid voice_instrumental"):
            collect_survey_from_dict(answers)

    def test_invalid_timbre_raises(self):
        answers = {"genres": [], "moods": [], "danceable": "any", "voice_instrumental": "any", "timbre": "medium", "loudness": "any"}
        with pytest.raises(ValueError, match="Invalid timbre"):
            collect_survey_from_dict(answers)

    def test_valid_categories_accepted(self):
        answers = {"genres": [], "moods": [], "danceable": "not_danceable", "voice_instrumental": "instrumental", "timbre": "dark", "loudness": "any"}
        profile = collect_survey_from_dict(answers)
        assert profile.danceable == "not_danceable"
        assert profile.voice_instrumental == "instrumental"
        assert profile.timbre == "dark"

    def test_optional_genre_validation_raises_for_invalid(self):
        answers = {"genres": ["unknown_genre"], "moods": [], "danceable": "any", "voice_instrumental": "any", "timbre": "any", "loudness": "any"}
        with pytest.raises(ValueError, match="Invalid genres"):
            collect_survey_from_dict(answers, kb_genres=["rock", "pop"])

    def test_optional_genre_validation_accepts_valid(self):
        answers = {"genres": ["rock"], "moods": [], "danceable": "any", "voice_instrumental": "any", "timbre": "any", "loudness": "any"}
        profile = collect_survey_from_dict(answers, kb_genres=["rock", "pop"])
        assert profile.preferred_genres == ["rock"]
