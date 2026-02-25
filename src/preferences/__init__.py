"""
Module 2: Rule-Based Preference Encoding

This package provides survey collection, preference profiles, rules, and scoring
for the music recommendation system.
"""

from .survey import (
    SurveySchema,
    SurveyQuestion,
    PreferenceProfile,
    LoudnessLevel,
    collect_survey_from_dict,
    collect_survey_cli,
)
from .ratings import (
    Rating,
    SongRating,
    UserRatings,
    collect_ratings_interactive,
)
from .sampling import (
    sample_songs,
    sample_random,
    sample_stratified,
    sample_by_preferences,
    sample_by_initial_score,
)

__all__ = [
    "SurveySchema",
    "SurveyQuestion",
    "PreferenceProfile",
    "LoudnessLevel",
    "collect_survey_from_dict",
    "collect_survey_cli",
    "Rating",
    "SongRating",
    "UserRatings",
    "collect_ratings_interactive",
    "sample_songs",
    "sample_random",
    "sample_stratified",
    "sample_by_preferences",
    "sample_by_initial_score",
]
