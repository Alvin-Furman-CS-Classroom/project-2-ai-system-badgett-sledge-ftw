"""
Knowledge Base Query Interface

This module provides a wrapper class for querying the knowledge base.
The KnowledgeBase class will be used by all modules (Search, ML, Clustering, etc.)
to access structured facts and relations about songs.
"""

import json
from typing import Dict, List, Set, Optional
from pathlib import Path


class KnowledgeBase:
    """Wrapper for querying the knowledge base."""
    
    def __init__(self, kb_path: str = "data/knowledge_base.json"):
        """
        Load the knowledge base from JSON file.
        
        Args:
            kb_path: Path to the knowledge_base.json file (relative to project root or absolute)
            
        Raises:
            FileNotFoundError: If the knowledge base file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            IOError: If there's an error reading the file
        """
        # Handle both relative and absolute paths
        kb_file = Path(kb_path)
        if not kb_file.is_absolute():
            # If relative, assume it's relative to project root
            project_root = Path(__file__).parent.parent
            kb_file = project_root / kb_path
        
        try:
            with open(kb_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Knowledge base file not found: {kb_file}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in knowledge base file {kb_file}: {e.msg}", e.doc, e.pos)
        except IOError as e:
            raise IOError(f"Error reading knowledge base file {kb_file}: {e}")
        
        self.songs = self.data.get('songs', {})
        self.facts = self.data.get('facts', {})
        self.indexes = self.data.get('indexes', {})
    
    def get_song(self, mbid: str) -> Optional[Dict]:
        """
        Get song metadata by MBID.
        
        Args:
            mbid: MusicBrainz ID of the song
            
        Returns:
            Dictionary with song metadata (artist, track, album) or None
        """
        return self.songs.get(mbid)
    
    def get_fact(self, fact_type: str, mbid: str):
        """
        Get a fact value for a song (e.g., genre, loudness).
        
        Args:
            fact_type: Type of fact (e.g., 'has_genre', 'has_loudness')
            mbid: MusicBrainz ID of the song
            
        Returns:
            Fact value (can be a single value, list, or None)
        """
        fact_dict = self.facts.get(fact_type, {})
        return fact_dict.get(mbid)
    
    def songs_by_genre(self, genre: str) -> List[str]:
        """
        Find songs in a specific genre.
        
        Args:
            genre: Genre name (case-insensitive)
            
        Returns:
            List of MBIDs for songs in that genre
        """
        genre_index = self.indexes.get('by_genre', {})
        return genre_index.get(genre.lower(), [])
    
    def songs_by_danceable(self, danceable: str) -> List[str]:
        """
        Find songs by danceability (danceable/not_danceable).
        
        Args:
            danceable: 'danceable' or 'not_danceable'
            
        Returns:
            List of MBIDs for songs matching the danceability
        """
        danceable_index = self.indexes.get('by_danceable', {})
        return danceable_index.get(danceable.lower(), [])
    
    def songs_by_voice_instrumental(self, voice_type: str) -> List[str]:
        """
        Find songs by voice/instrumental classification.
        
        Args:
            voice_type: 'voice' or 'instrumental'
            
        Returns:
            List of MBIDs for songs matching the type
        """
        vi_index = self.indexes.get('by_voice_instrumental', {})
        return vi_index.get(voice_type.lower(), [])
    
    def songs_by_timbre(self, timbre: str) -> List[str]:
        """
        Find songs by timbre classification.
        
        Args:
            timbre: Timbre classification (e.g., 'bright', 'dark')
            
        Returns:
            List of MBIDs for songs matching the timbre
        """
        timbre_index = self.indexes.get('by_timbre', {})
        return timbre_index.get(timbre.lower(), [])
    
    def songs_by_mood(self, mood: str) -> List[str]:
        """
        Find songs with a specific mood.
        
        Args:
            mood: Mood classification (e.g., 'happy', 'sad', 'relaxed')
            
        Returns:
            List of MBIDs for songs with that mood
        """
        mood_index = self.indexes.get('by_mood', {})
        return mood_index.get(mood.lower(), [])
    
    def songs_in_loudness_range(self, min_loudness: float, max_loudness: float) -> List[str]:
        """
        Find songs with loudness in a specific range.
        
        Args:
            min_loudness: Minimum loudness in dB
            max_loudness: Maximum loudness in dB
            
        Returns:
            List of MBIDs for songs in the loudness range
        """
        loudness_facts = self.facts.get('has_loudness', {})
        return [
            mbid for mbid, loudness in loudness_facts.items()
            if loudness is not None and min_loudness <= loudness <= max_loudness
        ]
    
    def get_all_genres(self) -> Set[str]:
        """
        Get all unique genres in the knowledge base.
        
        Returns:
            Set of all genre names
        """
        genre_index = self.indexes.get('by_genre', {})
        return set(genre_index.keys())
    
    def get_all_moods(self) -> Set[str]:
        """
        Get all unique moods in the knowledge base.
        
        Returns:
            Set of all mood names
        """
        mood_index = self.indexes.get('by_mood', {})
        return set(mood_index.keys())
    
    def get_all_songs(self) -> List[str]:
        """
        Get all song MBIDs in the knowledge base.
        
        Returns:
            List of all MBIDs
        """
        return list(self.songs.keys())
    
    def has_fact(self, fact_type: str, mbid: str) -> bool:
        """
        Check if a song has a specific fact.
        
        Args:
            fact_type: Type of fact to check
            mbid: MusicBrainz ID of the song
            
        Returns:
            True if the song has this fact, False otherwise
        """
        fact_dict = self.facts.get(fact_type, {})
        return mbid in fact_dict
    
    def _exact_match_search(self, track_lower: str, artist_lower: Optional[str]) -> Optional[str]:
        """
        Search for exact match of track and artist.
        
        Args:
            track_lower: Lowercase track name
            artist_lower: Lowercase artist name or None
            
        Returns:
            MBID if exact match found, None otherwise
        """
        for mbid, song in self.songs.items():
            song_track = song.get('track', '').strip().lower()
            song_artist = song.get('artist', '').strip().lower()
            
            if song_track == track_lower:
                if artist_lower is None:
                    return mbid
                if song_artist == artist_lower:
                    return mbid
        return None
    
    def _partial_match_search(self, track_lower: str, artist_lower: Optional[str]) -> Optional[str]:
        """
        Search for partial match of track name (contains or is contained by).
        
        Args:
            track_lower: Lowercase track name
            artist_lower: Lowercase artist name or None
            
        Returns:
            MBID if partial match found, None otherwise
        """
        for mbid, song in self.songs.items():
            song_track = song.get('track', '').strip().lower()
            
            if track_lower in song_track or song_track in track_lower:
                if artist_lower is None:
                    return mbid
                song_artist = song.get('artist', '').strip().lower()
                if artist_lower in song_artist or song_artist in artist_lower:
                    return mbid
        return None
    
    def get_mbid_by_song(self, track_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        Find MBID by song name (and optionally artist name).
        
        Args:
            track_name: Name of the track/song (case-insensitive, partial match supported)
            artist_name: Optional artist name for more precise matching (case-insensitive)
            
        Returns:
            MBID string if found, None otherwise. If multiple matches and artist is not provided,
            returns the first match. If artist is provided, returns exact match or None.
            
        Raises:
            TypeError: If track_name is not a string
            ValueError: If track_name is empty after stripping
        """
        if not isinstance(track_name, str):
            raise TypeError(f"track_name must be a string, got {type(track_name)}")
        if not track_name.strip():
            raise ValueError("track_name cannot be empty")
        if artist_name is not None and not isinstance(artist_name, str):
            raise TypeError(f"artist_name must be a string or None, got {type(artist_name)}")
        
        track_lower = track_name.strip().lower()
        artist_lower = artist_name.strip().lower() if artist_name else None
        
        # Try exact match first
        result = self._exact_match_search(track_lower, artist_lower)
        if result:
            return result
        
        # Fall back to partial match
        return self._partial_match_search(track_lower, artist_lower)
    
    def find_songs_by_name(self, track_name: str, artist_name: Optional[str] = None) -> List[str]:
        """
        Find all MBIDs matching a song name (and optionally artist name).
        
        Args:
            track_name: Name of the track/song (case-insensitive, partial match)
            artist_name: Optional artist name for filtering (case-insensitive)
            
        Returns:
            List of MBIDs matching the criteria
        """
        track_lower = track_name.strip().lower()
        artist_lower = artist_name.strip().lower() if artist_name else None
        
        matches = []
        
        for mbid, song in self.songs.items():
            song_track = song.get('track', '').strip().lower()
            song_artist = song.get('artist', '').strip().lower()
            
            # Check if track matches
            track_matches = (track_lower == song_track or 
                           track_lower in song_track or 
                           song_track in track_lower)
            
            if not track_matches:
                continue
            
            # If artist specified, check if it matches too
            if artist_lower:
                artist_matches = (artist_lower == song_artist or 
                                artist_lower in song_artist or 
                                song_artist in artist_lower)
                if artist_matches:
                    matches.append(mbid)
            else:
                matches.append(mbid)
        
        return matches