"""
Offline training entrypoint for Module 4 (ML).

This script:
- loads the knowledge base, user playlists, and user ratings
- builds training examples using playlists + ratings
- extracts a small feature set from the KB for each song
- fits simple linear-style weights per feature
- saves the learned weights to data/module4_scorer.json

It is designed to be:
- deterministic (no randomization needed)
- easy to inspect (artifacts are JSON; features are simple strings)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set

from knowledge_base_wrapper import KnowledgeBase
from ml.artifacts import make_scorer_artifact, save_scorer_artifact
from ml.dataset import TrainingExample, build_training_examples
from preferences import UserRatings


PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KB_PATH = DATA_DIR / "knowledge_base.json"
PLAYLISTS_PATH = DATA_DIR / "user_playlists.json"
RATINGS_PATH = DATA_DIR / "user_ratings.json"
SCORER_ARTIFACT_PATH = DATA_DIR / "module4_scorer.json"


def _load_playlists() -> Dict:
    """Load playlists JSON if present; return empty structure if missing."""
    if not PLAYLISTS_PATH.exists():
        # No playlists yet; treat as empty.
        return {"playlists": []}
    with PLAYLISTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_ratings() -> UserRatings:
    """Load user ratings if present; otherwise return an empty UserRatings."""
    if not RATINGS_PATH.exists():
        return UserRatings()
    return UserRatings.load(str(RATINGS_PATH))


def _feature_keys_for_mbid(kb: KnowledgeBase, mbid: str) -> Set[str]:
    """
    Extract a small, interpretable feature set for a song from the KB.

    Features are simple string keys; their numeric weights are learned from
    playlists + ratings. Examples:
        genre:rock
        genre:pop
        mood:happy
        danceable:danceable
        vi:voice
        timbre:bright
        loudness_bucket:quiet|medium|loud
    """
    features: Set[str] = set()

    # Genres (can be list or single value)
    genres = kb.get_fact("has_genre", mbid)
    if isinstance(genres, list):
        for g in genres:
            features.add(f"genre:{str(g).strip().lower()}")
    elif genres is not None:
        features.add(f"genre:{str(genres).strip().lower()}")

    # Moods
    moods = kb.get_fact("has_mood", mbid)
    if isinstance(moods, list):
        for m in moods:
            features.add(f"mood:{str(m).strip().lower()}")
    elif moods is not None:
        features.add(f"mood:{str(moods).strip().lower()}")

    # Danceable
    danceable = kb.get_fact("has_danceable", mbid)
    if danceable is not None:
        features.add(f"danceable:{str(danceable).strip().lower()}")

    # Voice / instrumental
    vi = kb.get_fact("has_voice_instrumental", mbid)
    if vi is not None:
        features.add(f"vi:{str(vi).strip().lower()}")

    # Timbre
    timbre = kb.get_fact("has_timbre", mbid)
    if timbre is not None:
        features.add(f"timbre:{str(timbre).strip().lower()}")

    # Loudness bucket
    loudness = kb.get_fact("has_loudness", mbid)
    if isinstance(loudness, (int, float)):
        if loudness <= -20:
            bucket = "quiet"
        elif loudness >= -8:
            bucket = "loud"
        else:
            bucket = "medium"
        features.add(f"loudness_bucket:{bucket}")

    # Always include a bias term so songs can have a baseline score.
    features.add("bias")

    return features


def _collect_feature_stats(
    kb: KnowledgeBase,
    examples: Iterable[TrainingExample],
) -> Dict[str, float]:
    """
    Compute a simple linear-style weight for each feature.

    For each feature f:
        weight[f] = avg(label | f present) - global_avg_label

    This gives positive weights to features that appear mostly in high-label
    songs (liked / playlist-heavy) and negative weights to features that appear
    mostly in low-label songs (disliked).
    """
    # Accumulate label sums/counts per feature and global stats.
    global_sum = 0.0
    global_count = 0
    feat_sum: Dict[str, float] = defaultdict(float)
    feat_count: Dict[str, int] = defaultdict(int)

    for ex in examples:
        global_sum += ex.label
        global_count += 1
        feature_keys = _feature_keys_for_mbid(kb, ex.mbid)
        for fk in feature_keys:
            feat_sum[fk] += ex.label
            feat_count[fk] += 1

    if global_count == 0:
        return {}

    global_avg = global_sum / global_count

    weights: Dict[str, float] = {}
    for fk, count in feat_count.items():
        avg_for_feature = feat_sum[fk] / float(count)
        weights[fk] = avg_for_feature - global_avg

    return weights


def train_module4_scorer(
    kb_path: str | Path = KB_PATH,
    playlists_path: str | Path = PLAYLISTS_PATH,
    ratings_path: str | Path = RATINGS_PATH,
    artifact_path: str | Path = SCORER_ARTIFACT_PATH,
) -> None:
    """
    Train a simple linear-style scorer from playlists + ratings and save it.

    This function is intended to be called from a small CLI (see __main__).
    """
    kb = KnowledgeBase(str(kb_path))

    # Load inputs.
    if Path(playlists_path).exists():
        with Path(playlists_path).open("r", encoding="utf-8") as f:
            playlists_json = json.load(f)
    else:
        playlists_json = {"playlists": []}

    if Path(ratings_path).exists():
        user_ratings = UserRatings.load(str(ratings_path))
    else:
        user_ratings = UserRatings()

    # Build supervision examples (labels, playlist membership, etc.).
    examples: List[TrainingExample] = build_training_examples(
        playlists_json,
        user_ratings,
        candidate_mbids=kb.get_all_songs(),
    )

    if not examples:
        print("Module 4 training: no training examples found (no playlists/ratings).")
        return

    # Compute simple feature weights.
    weights = _collect_feature_stats(kb, examples)
    if not weights:
        print("Module 4 training: no usable features found; not writing artifact.")
        return

    # Prepare artifact metadata.
    source = {
        "playlists_file": str(playlists_path),
        "ratings_file": str(ratings_path),
        "kb_snapshot": str(kb_path),
    }
    config = {
        "model_type": "feature_mean_difference",
        "label_scheme": "playlist+ratings",
        "feature_family": ["genre", "mood", "danceable", "voice_instrumental", "timbre", "loudness_bucket", "bias"],
    }

    artifact = make_scorer_artifact(
        source=source,
        config=config,
        weights=weights,
    )
    save_scorer_artifact(artifact, str(artifact_path))

    print(f"Module 4 training complete. Learned {len(weights)} feature weights.")
    print(f"Scorer artifact written to: {artifact_path}")


if __name__ == "__main__":
    train_module4_scorer()

