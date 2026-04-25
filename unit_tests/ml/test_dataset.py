from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ml.dataset import TrainingExample, build_training_examples  # type: ignore
from preferences import Rating, UserRatings  # type: ignore


def test_build_training_examples_labels_and_flags():
    playlists_json = {
        "playlists": [
            {"name": "fav", "mbids": ["a", "b"]},
        ]
    }

    ratings = UserRatings()
    ratings.add_rating("a", Rating.REALLY_LIKE)
    ratings.add_rating("c", Rating.DISLIKE)

    examples = build_training_examples(playlists_json, ratings)
    by_mbid = {ex.mbid: ex for ex in examples}

    # Song A: in playlist + REALLY_LIKE.
    ex_a = by_mbid["a"]
    assert ex_a.in_any_playlist is True
    assert "fav" in ex_a.playlist_names
    assert ex_a.rating == Rating.REALLY_LIKE

    # Song B: in playlist only, no rating.
    ex_b = by_mbid["b"]
    assert ex_b.in_any_playlist is True
    assert ex_b.rating is None

    # Song C: rated only (DISLIKE), not in playlist.
    ex_c = by_mbid["c"]
    assert ex_c.in_any_playlist is False
    assert ex_c.rating == Rating.DISLIKE

