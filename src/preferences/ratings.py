"""
Song Rating System for Module 2

Collects user ratings on sampled songs and stores them for weight refinement.
Provides refine_weights_from_ratings() to update rule weights from user feedback.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from preferences.rules import Rule, evaluate_rule

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase

# Weight refinement constants
RULE_SATISFIED_THRESHOLD = 0.5  # Rule score >= this counts as "satisfied" for refinement
DEFAULT_ALPHA = 0.1  # Learning rate for weight updates
DEFAULT_WEIGHT_FLOOR = 1e-6  # Minimum weight after update

class Rating(Enum):
    """User rating levels (1–4 scale with a neutral middle option)."""
    DISLIKE = 1
    NEUTRAL = 2   # In between: okay, so-so, no strong opinion
    LIKE = 3
    REALLY_LIKE = 4

    def to_numeric(self) -> int:
        """Convert rating to numeric value (1–4)."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "Rating":
        """Convert string to Rating enum."""
        value_lower = value.lower().strip()
        rating = _STRING_TO_RATING.get(value_lower)
        if rating is not None:
            return rating
        raise ValueError(
            f"Invalid rating: {value}. Must be 'dislike', 'neutral', 'like', or 'really_like'"
        )
    
    def __str__(self) -> str:
        """Human-readable string."""
        return {
            Rating.DISLIKE: "Dislike",
            Rating.NEUTRAL: "Neutral",
            Rating.LIKE: "Like",
            Rating.REALLY_LIKE: "Really Like"
        }[self]


# Module-level map for Rating.from_string (avoids Enum metaclass issues)
_STRING_TO_RATING: Dict[str, Rating] = {
    "dislike": Rating.DISLIKE,
    "1": Rating.DISLIKE,
    "neutral": Rating.NEUTRAL,
    "okay": Rating.NEUTRAL,
    "ok": Rating.NEUTRAL,
    "so-so": Rating.NEUTRAL,
    "soso": Rating.NEUTRAL,
    "meh": Rating.NEUTRAL,
    "indifferent": Rating.NEUTRAL,
    "2": Rating.NEUTRAL,
    "like": Rating.LIKE,
    "3": Rating.LIKE,
    "really like": Rating.REALLY_LIKE,
    "really_like": Rating.REALLY_LIKE,
    "4": Rating.REALLY_LIKE,
}


@dataclass
class SongRating:
    """A single song rating."""
    mbid: str
    rating: Rating
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "mbid": self.mbid,
            "rating": self.rating.name
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SongRating':
        """Create from dictionary."""
        return cls(
            mbid=data["mbid"],
            rating=Rating[data["rating"]]
        )


class UserRatings:
    """Collection of user ratings for songs."""
    
    def __init__(self):
        self.ratings: Dict[str, Rating] = {}  # mbid -> Rating
    
    def add_rating(self, mbid: str, rating: Rating) -> None:
        """Add or update a rating for a song."""
        self.ratings[mbid] = rating
    
    def get_rating(self, mbid: str) -> Optional[Rating]:
        """Get rating for a song, or None if not rated."""
        return self.ratings.get(mbid)
    
    def has_rating(self, mbid: str) -> bool:
        """Check if a song has been rated."""
        return mbid in self.ratings
    
    def get_all_ratings(self) -> List[Tuple[str, Rating]]:
        """Get all ratings as list of (mbid, rating) tuples."""
        return [(mbid, rating) for mbid, rating in self.ratings.items()]
    
    def get_highly_rated(self, min_rating: Rating = Rating.LIKE) -> List[str]:
        """Get MBIDs of songs rated at or above min_rating."""
        return [
            mbid for mbid, rating in self.ratings.items()
            if rating.value >= min_rating.value
        ]
    
    def get_low_rated(self, max_rating: Rating = Rating.DISLIKE) -> List[str]:
        """Get MBIDs of songs rated at or below max_rating."""
        return [
            mbid for mbid, rating in self.ratings.items()
            if rating.value <= max_rating.value
        ]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ratings": [
                {"mbid": mbid, "rating": rating.name}
                for mbid, rating in self.ratings.items()
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserRatings':
        """Create from dictionary."""
        ratings_obj = cls()
        for item in data.get("ratings", []):
            ratings_obj.add_rating(
                item["mbid"],
                Rating[item["rating"]]
            )
        return ratings_obj
    
    def save(self, filepath: str) -> None:
        """Save ratings to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "UserRatings":
        """Load ratings from JSON file."""
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """Number of rated songs."""
        return len(self.ratings)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"UserRatings({len(self.ratings)} songs)"


def refine_weights_from_ratings(
    kb: "KnowledgeBase",
    rules: List[Rule],
    current_weights: Dict[str, float],
    user_ratings: Union[UserRatings, List[Tuple[str, Rating]]],
    alpha: float = DEFAULT_ALPHA,
    weight_floor: float = DEFAULT_WEIGHT_FLOOR,
    normalize: bool = True,
) -> Dict[str, float]:
    """
    Refine the rule weight vector from user ratings (hill-climbing step).

    For each rule, computes the average rating of songs that satisfy it vs. the
    overall average; increases the rule's weight if satisfied songs were rated
    higher, decreases if lower. Keeps weights non-negative.

    Args:
        kb: KnowledgeBase instance (to evaluate rules per song).
        rules: List of Rule objects (e.g. from build_rules(profile)).
        current_weights: Current weight per rule_id (e.g. from get_default_weights).
        user_ratings: UserRatings instance or list of (mbid, Rating) tuples.
        alpha: Learning rate for weight updates (default DEFAULT_ALPHA).
        weight_floor: Minimum weight after update (default DEFAULT_WEIGHT_FLOOR).
        normalize: If True, scale refined weights to sum to 1.0 (default True).

    Returns:
        New dict mapping rule_id -> refined weight (non-negative).
    """
    if isinstance(user_ratings, UserRatings):
        rating_list = [(mbid, r.value) for mbid, r in user_ratings.get_all_ratings()]
    else:
        rating_list = [(mbid, r.value if hasattr(r, "value") else r) for mbid, r in user_ratings]

    if not rating_list:
        return dict(current_weights)

    avg_overall = sum(n for _, n in rating_list) / len(rating_list)
    refined: Dict[str, float] = {}

    for rule in rules:
        satisfied_numerics = [
            n for mbid, n in rating_list
            if evaluate_rule(rule, mbid, kb) >= RULE_SATISFIED_THRESHOLD
        ]
        avg_satisfied = (
            sum(satisfied_numerics) / len(satisfied_numerics)
            if satisfied_numerics
            else 0.0
        )
        delta = alpha * (avg_satisfied - avg_overall)
        new_w = current_weights.get(rule.rule_id, 0.0) + delta
        refined[rule.rule_id] = max(weight_floor, new_w)

    if normalize and refined:
        total = sum(refined.values())
        if total > 0:
            refined = {rid: w / total for rid, w in refined.items()}

    return refined


INPUT_TO_RATING = {"1": Rating.DISLIKE, "2": Rating.NEUTRAL, "3": Rating.LIKE, "4": Rating.REALLY_LIKE}


def _format_song_display(mbid: str, kb: "KnowledgeBase", index: int, total: int) -> Optional[str]:
    """Format song info and KB facts for display. Returns None if song not in KB."""
    song = kb.get_song(mbid)
    if not song:
        return None
    lines = [
        f"\nSong {index}/{total}:",
        f"  Artist: {song.get('artist', 'Unknown')}",
        f"  Track: {song.get('track', 'Unknown')}",
    ]
    album = song.get("album", "")
    if album:
        lines.append(f"  Album: {album}")
    genre = kb.get_fact("has_genre", mbid)
    mood = kb.get_fact("has_mood", mbid)
    danceable = kb.get_fact("has_danceable", mbid)
    facts = []
    if genre:
        genre_str = ", ".join(genre[:2]) if isinstance(genre, list) else str(genre)
        facts.append(f"Genre: {genre_str}")
    if mood:
        mood_str = ", ".join(mood[:2]) if isinstance(mood, list) else str(mood)
        facts.append(f"Mood: {mood_str}")
    if danceable:
        facts.append(f"Danceable: {danceable}")
    if facts:
        lines.append(f"  {' | '.join(facts)}")
    return "\n".join(lines)


def _prompt_single_rating() -> Optional[Rating]:
    """Prompt user for one rating (1-4). Returns None on KeyboardInterrupt."""
    try:
        while True:
            rating_input = input("\nYour rating (1-4): ").strip()
            rating = INPUT_TO_RATING.get(rating_input)
            if rating is not None:
                return rating
            print("Invalid input. Please enter 1, 2, 3, or 4.")
    except KeyboardInterrupt:
        return None


def collect_ratings_interactive(song_mbids: List[str], kb: "KnowledgeBase") -> UserRatings:
    """
    Collect ratings interactively from user for a list of songs.

    Args:
        song_mbids: List of MBIDs to rate
        kb: KnowledgeBase instance to get song info

    Returns:
        UserRatings object with collected ratings
    """
    ratings = UserRatings()
    total = len(song_mbids)

    print("\n" + "=" * 70)
    print("  SONG RATING")
    print("=" * 70)
    print("\nRate each song using:")
    print("  [1] Dislike")
    print("  [2] Neutral  (okay / no strong opinion)")
    print("  [3] Like")
    print("  [4] Really Like")
    print("\n" + "-" * 70)

    for index, mbid in enumerate(song_mbids, 1):
        display = _format_song_display(mbid, kb, index, total)
        if display is None:
            print(f"\nSong {index}/{total}: MBID {mbid} not found in KB, skipping...")
            continue
        print(display)
        rating = _prompt_single_rating()
        if rating is None:
            print("\n\nRating collection cancelled.")
            return ratings
        ratings.add_rating(mbid, rating)
        print(f"  ✓ Rated as: {rating}")

    print("\n" + "=" * 70)
    print(f"  Rating Complete! Rated {len(ratings)} songs.")
    print("=" * 70 + "\n")
    return ratings
