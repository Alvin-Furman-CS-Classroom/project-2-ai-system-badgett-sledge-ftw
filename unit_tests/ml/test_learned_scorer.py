from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import sys

# Ensure src/ is on sys.path so we can import project packages consistently.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ml.artifacts import ScorerArtifact  # type: ignore
from ml.learned_scorer import LearnedPreferenceScorer  # type: ignore
from preferences import PreferenceScorer, Rule  # type: ignore


@dataclass
class FakeKB:
    """Minimal KB stub exposing get_fact used by LearnedPreferenceScorer."""

    facts: Dict[str, Dict[str, Any]]

    def get_fact(self, fact_type: str, mbid: str) -> Any:
        return self.facts.get(fact_type, {}).get(mbid)


def make_base_scorer(constant_score: float = 0.5) -> PreferenceScorer:
    """
    Build a PreferenceScorer that returns a constant score for any song.

    This keeps tests focused on the learned contribution and blend behavior.
    """
    rule = Rule(rule_id="bias_rule", fact_type="has_genre", target=["rock"])
    # We don't care about real evaluation here; just one rule with weight 1.0.
    return PreferenceScorer(rules=[rule], weights={"bias_rule": constant_score})


def test_learned_scorer_falls_back_to_rule_score_when_no_artifact():
    kb = FakeKB(facts={})
    base = make_base_scorer(constant_score=0.7)
    learned = LearnedPreferenceScorer(base_scorer=base, artifact=None, blend_weight=0.5)

    assert learned.score("any-mbid", kb) == base.score("any-mbid", kb)


def test_learned_scorer_uses_feature_weights_and_blend():
    # Two songs: one "rock loud", one "pop quiet".
    kb = FakeKB(
        facts={
            "has_genre": {
                "song_rock": ["rock"],
                "song_pop": ["pop"],
            },
            "has_loudness": {
                "song_rock": -5.0,   # loud bucket
                "song_pop": -25.0,   # quiet bucket
            },
        }
    )

    # Base scorer gives both songs the same rule-based score.
    base = make_base_scorer(constant_score=0.5)

    # Learned weights prefer rock and loud songs.
    artifact = ScorerArtifact(
        version=1,
        trained_at="2026-04-02T00:00:00Z",
        source={},
        config={},
        weights={
            "genre:rock": 0.3,
            "genre:pop": -0.1,
            "loudness_bucket:loud": 0.2,
            "loudness_bucket:quiet": -0.2,
            "bias": 0.0,
        },
    )

    learned = LearnedPreferenceScorer(base_scorer=base, artifact=artifact, blend_weight=0.5)

    rock_score = learned.score("song_rock", kb)
    pop_score = learned.score("song_pop", kb)

    # Sanity: both scores should start near the base score but rock should be higher.
    assert rock_score > pop_score
    # And learned scores should not explode to huge magnitudes.
    assert -5.0 <= rock_score <= 5.0
    assert -5.0 <= pop_score <= 5.0

