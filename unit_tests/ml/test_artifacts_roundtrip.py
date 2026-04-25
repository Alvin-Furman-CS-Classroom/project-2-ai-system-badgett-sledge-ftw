from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ml.artifacts import (  # type: ignore
    RerankerArtifact,
    ScorerArtifact,
    load_reranker_artifact,
    load_scorer_artifact,
    save_reranker_artifact,
    save_scorer_artifact,
)


def test_scorer_artifact_roundtrip(tmp_path: Path):
    path = tmp_path / "scorer.json"
    original = ScorerArtifact(
        version=1,
        trained_at="2026-04-02T00:00:00Z",
        source={"kb_snapshot": "kb.json"},
        config={"model_type": "x"},
        weights={"genre:rock": 0.3},
    )
    save_scorer_artifact(original, str(path))
    loaded = load_scorer_artifact(str(path))

    assert loaded.version == original.version
    assert loaded.source == original.source
    assert loaded.config == original.config
    assert loaded.weights == original.weights


def test_reranker_artifact_roundtrip(tmp_path: Path):
    path = tmp_path / "reranker.json"
    original = RerankerArtifact(
        version=2,
        trained_at="2026-04-03T00:00:00Z",
        source={"kb_snapshot": "kb.json"},
        config={"model_type": "y"},
        weights={"genre:pop": -0.1},
    )
    save_reranker_artifact(original, str(path))
    loaded = load_reranker_artifact(str(path))

    assert loaded.version == original.version
    assert loaded.source == original.source
    assert loaded.config == original.config
    assert loaded.weights == original.weights

