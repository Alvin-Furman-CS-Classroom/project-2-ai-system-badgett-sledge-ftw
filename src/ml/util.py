from pathlib import Path
from typing import Optional

from preferences import PreferenceScorer

from .artifacts import load_scorer_artifact
from .learned_scorer import LearnedPreferenceScorer


def build_scorer_with_optional_ml(
    base_scorer: PreferenceScorer,
    artifact_path: str = "data/module4_scorer.json",
    *,
    blend_weight: float = 0.5,
) -> PreferenceScorer:
    """
    Return a scorer that uses Module 4 ML if an artifact exists, otherwise the base scorer.

    This is a convenience helper for wiring Module 4 into demos or CLIs without
    changing call sites that expect a PreferenceScorer-like object.
    """
    path = Path(artifact_path)
    if not path.exists():
        return base_scorer

    try:
        artifact = load_scorer_artifact(str(path))
    except Exception:
        # If the artifact is corrupt or incompatible, fall back safely.
        return base_scorer

    if not artifact.weights:
        return base_scorer

    return LearnedPreferenceScorer(
        base_scorer=base_scorer,
        artifact=artifact,
        blend_weight=blend_weight,
    )

