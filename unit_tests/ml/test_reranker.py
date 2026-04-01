from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ml.artifacts import RerankerArtifact  # type: ignore
from ml.reranker import rerank_results_with_artifact  # type: ignore
from search.pipeline import SearchResult  # type: ignore


@dataclass
class FakeKB:
    facts: Dict[str, Dict[str, Any]]

    def get_fact(self, fact_type: str, mbid: str) -> Any:
        return self.facts.get(fact_type, {}).get(mbid)


def test_reranker_changes_order_when_weights_prefer_second_song():
    kb = FakeKB(
        facts={
            "has_genre": {
                "s1": ["rock"],
                "s2": ["pop"],
            }
        }
    )

    results = [
        SearchResult(mbid="s1", path_cost=1.0, preference_score=0.9, combined_score=0.9),
        SearchResult(mbid="s2", path_cost=1.0, preference_score=0.8, combined_score=0.8),
    ]

    artifact = RerankerArtifact(
        version=1,
        trained_at="2026-04-02T00:00:00Z",
        source={},
        config={},
        weights={
            "genre:rock": -1.0,
            "genre:pop": 1.0,
            "bias": 0.0,
        },
    )

    reranked = rerank_results_with_artifact(kb, results, artifact)
    mbids = [r.mbid for r in reranked]

    assert mbids[0] == "s2"
