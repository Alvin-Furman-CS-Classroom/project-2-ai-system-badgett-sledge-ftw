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
    refine_weights_from_ratings,
)
from .sampling import (
    sample_songs,
    sample_random,
    sample_stratified,
    sample_by_preferences,
    sample_by_initial_score,
    sample_next_batch,
)
from .rules import (
    Rule,
    build_rules,
    evaluate_rule,
    get_default_weights,
)
from .scorer import PreferenceScorer

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
    "refine_weights_from_ratings",
    "sample_songs",
    "sample_random",
    "sample_stratified",
    "sample_by_preferences",
    "sample_by_initial_score",
    "sample_next_batch",
    "Rule",
    "build_rules",
    "evaluate_rule",
    "get_default_weights",
    "PreferenceScorer",
]
