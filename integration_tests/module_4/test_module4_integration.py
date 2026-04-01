"""
Integration tests for Module 4: LearnedPreferenceScorer + Module 3 pipeline.

Uses the existing KB fixture to show that:
- baseline PreferenceScorer ranking matches Module 3 expectations
- attaching a learned scorer artifact can change the ranking among candidates
"""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

from knowledge_base_wrapper import KnowledgeBase  # type: ignore  # noqa: E402
from ml.artifacts import ScorerArtifact  # type: ignore  # noqa: E402
from ml.learned_scorer import LearnedPreferenceScorer  # type: ignore  # noqa: E402
from preferences.rules import build_rules, get_default_weights  # type: ignore  # noqa: E402
from preferences.scorer import PreferenceScorer  # type: ignore  # noqa: E402
from preferences.survey import PreferenceProfile  # type: ignore  # noqa: E402
from search.pipeline import find_similar  # type: ignore  # noqa: E402


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
    """Same profile as Module 3 tests: prefers rock genre."""
    return PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=[],
        danceable=None,
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )


def test_learned_scorer_can_flip_ranking_vs_rule_only(kb, profile_genre_rock_only):
    """
    Baseline: with alpha=0 and rule-based scorer, rock (002) ranks above pop (003).
    With a learned scorer that strongly prefers pop, the order can flip.
    """
    rules = build_rules(profile_genre_rock_only)
    base_scorer = PreferenceScorer(rules, get_default_weights(rules))

    # Baseline ranking driven purely by rule-based preference.
    base_results = find_similar(
        kb,
        "test-mbid-001",
        base_scorer,
        k=4,
        alpha=0.0,
        beta=1.0,
    )
    base_mbids = [r.mbid for r in base_results]

    if "test-mbid-002" in base_mbids and "test-mbid-003" in base_mbids:
        assert base_mbids.index("test-mbid-002") < base_mbids.index("test-mbid-003")

    # Learned artifact that prefers pop over rock.
    artifact = ScorerArtifact(
        version=1,
        trained_at="2026-04-02T00:00:00Z",
        source={},
        config={},
        weights={
            "genre:rock": -0.5,
            "genre:pop": 0.5,
            "bias": 0.0,
        },
    )
    learned_scorer = LearnedPreferenceScorer(
        base_scorer=base_scorer,
        artifact=artifact,
        blend_weight=1.0,  # rely on learned score only for this test
    )

    learned_results = find_similar(
        kb,
        "test-mbid-001",
        learned_scorer,
        k=4,
        alpha=0.0,
        beta=1.0,
    )
    learned_mbids = [r.mbid for r in learned_results]

    if "test-mbid-002" in learned_mbids and "test-mbid-003" in learned_mbids:
        assert learned_mbids.index("test-mbid-003") < learned_mbids.index("test-mbid-002")

