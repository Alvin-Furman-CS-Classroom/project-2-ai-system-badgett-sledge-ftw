"""
End-to-end train -> save -> load -> recommend flow for Module 4.

Uses the fixture KB, a tiny playlists/ratings setup, and the real
train_module4_scorer() function to produce artifacts, then builds a
LearnedPreferenceScorer and calls find_similar.
"""

import json
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

from knowledge_base_wrapper import KnowledgeBase  # type: ignore  # noqa: E402
from ml.artifacts import load_scorer_artifact  # type: ignore  # noqa: E402
from ml.learned_scorer import LearnedPreferenceScorer  # type: ignore  # noqa: E402
from ml.train_module4 import train_module4_scorer  # type: ignore  # noqa: E402
from preferences.rules import build_rules, get_default_weights  # type: ignore  # noqa: E402
from preferences.scorer import PreferenceScorer  # type: ignore  # noqa: E402
from preferences.survey import PreferenceProfile  # type: ignore  # noqa: E402
from search.pipeline import SearchResult, find_similar  # type: ignore  # noqa: E402


def _fixture_kb_path() -> Path:
    return _project_root / "unit_tests" / "fixtures" / "test_knowledge_base.json"


@pytest.mark.parametrize("blend_weight", [0.0, 0.5, 1.0])
def test_train_then_recommend_with_learned_scorer(tmp_path: Path, blend_weight: float):
    kb_path = _fixture_kb_path()
    if not kb_path.exists():
        pytest.skip(f"Fixture KB not found: {kb_path}")

    # Small synthetic playlists/ratings pointing at known MBIDs in the fixture KB.
    playlists_path = tmp_path / "user_playlists.json"
    ratings_path = tmp_path / "user_ratings.json"
    scorer_artifact_path = tmp_path / "module4_scorer.json"
    reranker_artifact_path = tmp_path / "module4_reranker.json"

    playlists = {
        "playlists": [
            {
                "name": "fav",
                "mbids": ["test-mbid-002"],
            }
        ]
    }
    ratings = {
        "ratings": [
            {"mbid": "test-mbid-002", "rating": "REALLY_LIKE"},
            {"mbid": "test-mbid-003", "rating": "DISLIKE"},
        ]
    }

    playlists_path.write_text(json.dumps(playlists), encoding="utf-8")
    ratings_path.write_text(json.dumps(ratings), encoding="utf-8")

    train_module4_scorer(
        kb_path=str(kb_path),
        playlists_path=str(playlists_path),
        ratings_path=str(ratings_path),
        artifact_path=str(scorer_artifact_path),
        reranker_artifact_path=str(reranker_artifact_path),
    )

    assert scorer_artifact_path.exists()

    kb = KnowledgeBase(str(kb_path))

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
    weights = get_default_weights(rules)
    base_scorer = PreferenceScorer(rules, weights)

    artifact = load_scorer_artifact(str(scorer_artifact_path))
    scorer = LearnedPreferenceScorer(
        base_scorer=base_scorer,
        artifact=artifact,
        blend_weight=blend_weight,
    )

    results = find_similar(
        kb,
        "test-mbid-001",
        scorer,
        k=3,
        alpha=0.0,
        beta=1.0,
    )

    assert isinstance(results, list)
    assert all(isinstance(r, SearchResult) for r in results)
