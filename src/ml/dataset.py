from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from preferences import UserRatings, Rating


@dataclass(frozen=True)
class TrainingExample:
    """
    One supervised training example for Module 4.

    For now this captures supervision signal only (playlist/ratings). Feature
    extraction from the KB is layered on later so this stays simple and
    testable.
    """

    mbid: str
    label: float  # numeric target derived from playlists + ratings
    in_any_playlist: bool
    playlist_names: Tuple[str, ...]
    rating: Optional[Rating]


def _index_playlists(playlists_json: Dict) -> Tuple[Dict[str, Set[str]], Dict[str, List[str]]]:
    """
    Build lookup structures from the playlists JSON blob.

    Args:
        playlists_json: Parsed contents of data/user_playlists.json.

    Returns:
        - mbid_to_playlists: mbid -> set of playlist names it appears in
        - playlists_to_mbids: playlist name -> list of mbids (order preserved)
    """
    mbid_to_playlists: Dict[str, Set[str]] = {}
    playlists_to_mbids: Dict[str, List[str]] = {}

    for pl in playlists_json.get("playlists", []):
        name = str(pl.get("name", "")).strip() or "unnamed"
        mbids = [m for m in pl.get("mbids", []) if isinstance(m, str)]
        playlists_to_mbids[name] = mbids
        for mbid in mbids:
            mbid_to_playlists.setdefault(mbid, set()).add(name)

    return mbid_to_playlists, playlists_to_mbids


def _ratings_to_index(user_ratings: UserRatings) -> Dict[str, Rating]:
    """Return a simple mbid -> Rating mapping from a UserRatings object."""
    return {mbid: rating for mbid, rating in user_ratings.get_all_ratings()}


def _rating_to_numeric(rating: Optional[Rating]) -> float:
    """
    Map Rating enum to a numeric scale suitable for supervised learning.

    This is intentionally simple; later we can experiment with different
    encodings without changing the dataset shape:
        DISLIKE      -> 0.0
        NEUTRAL      -> 0.5
        LIKE         -> 0.8
        REALLY_LIKE  -> 1.0
    """
    if rating is None:
        return 0.5
    if rating == Rating.DISLIKE:
        return 0.0
    if rating == Rating.NEUTRAL:
        return 0.5
    if rating == Rating.LIKE:
        return 0.8
    if rating == Rating.REALLY_LIKE:
        return 1.0
    return 0.5


def build_training_examples(
    playlists_json: Dict,
    user_ratings: UserRatings,
    *,
    candidate_mbids: Optional[Iterable[str]] = None,
) -> List[TrainingExample]:
    """
    Build supervised training examples from playlists + ratings.

    This function does not touch the KB; it only encodes which songs are
    in playlists and how they were rated. Feature extraction from the KB
    happens later in the training pipeline.

    Label semantics:
        - Any song that appears in at least one playlist is treated as a
          base positive example.
        - Ratings refine that signal:
            DISLIKE      -> strong negative (overrides playlist membership)
            NEUTRAL      -> weak mid-level value
            LIKE/REALLY_LIKE -> stronger positives
        - Songs that never appear in any playlist but have ratings are still
          valid examples (e.g., explicitly disliked tracks).

    Args:
        playlists_json: Parsed JSON dict from data/user_playlists.json.
        user_ratings: UserRatings object (e.g., loaded from data/user_ratings.json).
        candidate_mbids: Optional iterable restricting which MBIDs to include.
            If None, all MBIDs seen in playlists or ratings are used.

    Returns:
        List of TrainingExample objects.
    """
    mbid_to_playlists, _ = _index_playlists(playlists_json)
    ratings_index = _ratings_to_index(user_ratings)

    if candidate_mbids is None:
        mbid_universe: Set[str] = set(mbid_to_playlists.keys()) | set(ratings_index.keys())
    else:
        mbid_universe = set(candidate_mbids) & (set(mbid_to_playlists.keys()) | set(ratings_index.keys()))

    examples: List[TrainingExample] = []
    for mbid in sorted(mbid_universe):
        rating = ratings_index.get(mbid)
        in_any_playlist = mbid in mbid_to_playlists
        playlist_names = tuple(sorted(mbid_to_playlists.get(mbid, ())))

        # Start from rating-based numeric encoding.
        label = _rating_to_numeric(rating)

        # If the song is in any playlist but unrated, treat it as a mild positive.
        if rating is None and in_any_playlist:
            label = 0.7

        examples.append(
            TrainingExample(
                mbid=mbid,
                label=label,
                in_any_playlist=in_any_playlist,
                playlist_names=playlist_names,
                rating=rating,
            )
        )

    return examples

