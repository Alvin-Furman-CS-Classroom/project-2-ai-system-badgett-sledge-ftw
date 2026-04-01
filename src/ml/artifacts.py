import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass
class ScorerArtifact:
    """
    Serialized parameters for the learned preference scorer.

    The exact contents of ``weights`` are model-dependent; tests and callers
    should treat them as opaque.
    """

    version: int
    trained_at: str
    source: Dict[str, str]
    config: Dict[str, Any]
    weights: Dict[str, float]


@dataclass
class RerankerArtifact:
    """
    Serialized parameters for the optional reranker model.
    """

    version: int
    trained_at: str
    source: Dict[str, str]
    config: Dict[str, Any]
    weights: Dict[str, float]


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_scorer_artifact(
    *,
    source: Dict[str, str],
    config: Dict[str, Any],
    weights: Dict[str, float],
    version: int = 1,
) -> ScorerArtifact:
    """Convenience helper to construct a ScorerArtifact with a timestamp."""
    return ScorerArtifact(
        version=version,
        trained_at=_now_iso(),
        source=source,
        config=config,
        weights=weights,
    )


def make_reranker_artifact(
    *,
    source: Dict[str, str],
    config: Dict[str, Any],
    weights: Dict[str, float],
    version: int = 1,
) -> RerankerArtifact:
    """Convenience helper to construct a RerankerArtifact with a timestamp."""
    return RerankerArtifact(
        version=version,
        trained_at=_now_iso(),
        source=source,
        config=config,
        weights=weights,
    )


def save_scorer_artifact(artifact: ScorerArtifact, path: str) -> None:
    """Save a ScorerArtifact to JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(asdict(artifact), f, indent=2, sort_keys=True)


def save_reranker_artifact(artifact: RerankerArtifact, path: str) -> None:
    """Save a RerankerArtifact to JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(asdict(artifact), f, indent=2, sort_keys=True)


def load_scorer_artifact(path: str) -> ScorerArtifact:
    """Load a ScorerArtifact from JSON."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return ScorerArtifact(
        version=int(data.get("version", 1)),
        trained_at=str(data.get("trained_at", "")),
        source=dict(data.get("source", {})),
        config=dict(data.get("config", {})),
        weights=dict(data.get("weights", {})),
    )


def load_reranker_artifact(path: str) -> RerankerArtifact:
    """Load a RerankerArtifact from JSON."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return RerankerArtifact(
        version=int(data.get("version", 1)),
        trained_at=str(data.get("trained_at", "")),
        source=dict(data.get("source", {})),
        config=dict(data.get("config", {})),
        weights=dict(data.get("weights", {})),
    )

