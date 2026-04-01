"""
Module 4: Machine Learning helpers.

This package provides:
- Dataset utilities for turning playlists + ratings into training examples.
- Artifact I/O helpers for saving/loading trained model parameters.
- A learned-scorer wrapper that is compatible with ``score(mbid, kb)``.

Training logic and search-pipeline integration are implemented in later phases;
for now, this module focuses on clean, testable interfaces.
"""

from .dataset import TrainingExample, build_training_examples
from .artifacts import ScorerArtifact, RerankerArtifact, load_scorer_artifact, load_reranker_artifact
from .learned_scorer import LearnedPreferenceScorer
from .util import build_scorer_with_optional_ml

__all__ = [
    "TrainingExample",
    "build_training_examples",
    "ScorerArtifact",
    "RerankerArtifact",
    "load_scorer_artifact",
    "load_reranker_artifact",
    "LearnedPreferenceScorer",
    "build_scorer_with_optional_ml",
]

