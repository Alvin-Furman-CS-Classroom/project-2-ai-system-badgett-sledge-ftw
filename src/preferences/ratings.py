"""
Song Rating System for Module 2

Collects user ratings on sampled songs and stores them for weight refinement.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
from pathlib import Path


class Rating(Enum):
    """User rating levels."""
    DISLIKE = 1
    LIKE = 2
    REALLY_LIKE = 3
    
    @classmethod
    def from_string(cls, value: str) -> 'Rating':
        """Convert string to Rating enum."""
        value_lower = value.lower().strip()
        if value_lower in ["dislike", "1"]:
            return cls.DISLIKE
        elif value_lower in ["like", "2"]:
            return cls.LIKE
        elif value_lower in ["really like", "really_like", "3"]:
            return cls.REALLY_LIKE
        else:
            raise ValueError(f"Invalid rating: {value}. Must be 'dislike', 'like', or 'really_like'")
    
    def to_numeric(self) -> int:
        """Convert rating to numeric value (1-3)."""
        return self.value
    
    def __str__(self) -> str:
        """Human-readable string."""
        return {
            Rating.DISLIKE: "Dislike",
            Rating.LIKE: "Like",
            Rating.REALLY_LIKE: "Really Like"
        }[self]


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
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'UserRatings':
        """Load ratings from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """Number of rated songs."""
        return len(self.ratings)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"UserRatings({len(self.ratings)} songs)"


def collect_ratings_interactive(song_mbids: List[str], kb) -> UserRatings:
    """
    Collect ratings interactively from user for a list of songs.
    
    Args:
        song_mbids: List of MBIDs to rate
        kb: KnowledgeBase instance to get song info
        
    Returns:
        UserRatings object with collected ratings
    """
    ratings = UserRatings()
    
    print("\n" + "=" * 70)
    print("  SONG RATING")
    print("=" * 70)
    print("\nRate each song using:")
    print("  [1] Dislike")
    print("  [2] Like")
    print("  [3] Really Like")
    print("\n" + "-" * 70)
    
    for i, mbid in enumerate(song_mbids, 1):
        song = kb.get_song(mbid)
        if not song:
            print(f"\nSong {i}/{len(song_mbids)}: MBID {mbid} not found in KB, skipping...")
            continue
        
        artist = song.get('artist', 'Unknown')
        track = song.get('track', 'Unknown')
        album = song.get('album', '')
        
        # Show some KB facts for context
        genre = kb.get_fact('has_genre', mbid)
        mood = kb.get_fact('has_mood', mbid)
        danceable = kb.get_fact('has_danceable', mbid)
        
        print(f"\nSong {i}/{len(song_mbids)}:")
        print(f"  Artist: {artist}")
        print(f"  Track: {track}")
        if album:
            print(f"  Album: {album}")
        
        # Show facts if available
        facts = []
        if genre:
            genre_str = ', '.join(genre[:2]) if isinstance(genre, list) else str(genre)
            facts.append(f"Genre: {genre_str}")
        if mood:
            mood_str = ', '.join(mood[:2]) if isinstance(mood, list) else str(mood)
            facts.append(f"Mood: {mood_str}")
        if danceable:
            facts.append(f"Danceable: {danceable}")
        
        if facts:
            print(f"  {' | '.join(facts)}")
        
        # Get rating
        while True:
            try:
                rating_input = input(f"\nYour rating (1-3): ").strip()
                if rating_input == "1":
                    rating = Rating.DISLIKE
                    break
                elif rating_input == "2":
                    rating = Rating.LIKE
                    break
                elif rating_input == "3":
                    rating = Rating.REALLY_LIKE
                    break
                else:
                    print("Invalid input. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                print("\n\nRating collection cancelled.")
                return ratings
        
        ratings.add_rating(mbid, rating)
        print(f"  ✓ Rated as: {rating}")
    
    print("\n" + "=" * 70)
    print(f"  Rating Complete! Rated {len(ratings)} songs.")
    print("=" * 70 + "\n")
    
    return ratings
