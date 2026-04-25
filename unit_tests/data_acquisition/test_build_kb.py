"""
Unit tests for knowledge base builder.

Tests cover:
- Fact extraction from raw song data
- Index construction
- Data validation
- Edge cases (missing data, empty lists, etc.)
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "data_acquisition"))
from build_kb_from_acousticbrainz_dump import (
    build_knowledge_base,
    parse_lowlevel_json,
    parse_highlevel_json,
    parse_metadata_from_dump,
    parse_highlevel_extra,
    tempo_bucket,
    _get_nested,
    _value_if_confident,
    MIN_GENRE_PROBABILITY,
    MIN_CONFIDENCE_PROBABILITY
)


class TestParseLowlevelJson:
    """Test parse_lowlevel_json() function."""
    
    def test_parse_lowlevel_complete_data(self):
        """Test parsing low-level JSON with complete data."""
        data = {
            "rhythm": {"bpm": 120.5},
            "tonal": {"key_key": "C", "key_scale": "major"},
            "lowlevel": {"average_loudness": -8.5},
            "metadata": {
                "audio_properties": {
                    "length": 240.0,
                    "replay_gain": -8.5
                }
            }
        }
        
        result = parse_lowlevel_json(data)
        assert result["tempo"] == 120.5
        assert result["key"] == "C major"
        assert result["mode"] == "major"
        assert result["loudness"] == -8.5
        assert result["duration"] == 240.0
    
    def test_parse_lowlevel_missing_data(self):
        """Test parsing low-level JSON with missing fields."""
        data = {
            "rhythm": {},
            "tonal": {},
            "lowlevel": {}
        }
        
        result = parse_lowlevel_json(data)
        assert result["tempo"] is None
        assert result["key"] is None
        assert result["mode"] is None
    
    def test_parse_lowlevel_alternative_loudness(self):
        """Test parsing uses replay_gain when average_loudness missing."""
        data = {
            "metadata": {
                "audio_properties": {
                    "replay_gain": -10.0
                }
            }
        }
        
        result = parse_lowlevel_json(data)
        assert result["loudness"] == -10.0


class TestParseHighlevelJson:
    """Test parse_highlevel_json() function."""
    
    def test_parse_highlevel_with_valid_genres(self):
        """Test parsing high-level JSON with valid genre classifications."""
        data = {
            "genre_rosamerica": {"value": "Rock", "probability": 0.8},
            "genre_electronic": {"value": "Electronic", "probability": 0.4},
            "genre_dortmund": {"value": "Pop", "probability": 0.35}
        }
        
        genres = parse_highlevel_json(data)
        assert "rock" in genres
        assert "electronic" in genres
        assert "pop" in genres
    
    def test_parse_highlevel_below_threshold(self):
        """Test genres below probability threshold are excluded."""
        data = {
            "genre_rosamerica": {"value": "Rock", "probability": 0.2}  # Below 0.3
        }
        
        genres = parse_highlevel_json(data)
        assert "rock" not in genres
    
    def test_parse_highlevel_no_duplicates(self):
        """Test duplicate genres are removed."""
        data = {
            "genre_rosamerica": {"value": "Rock", "probability": 0.8},
            "genre_electronic": {"value": "Rock", "probability": 0.7}
        }
        
        genres = parse_highlevel_json(data)
        assert genres.count("rock") == 1


class TestParseMetadataFromDump:
    """Test parse_metadata_from_dump() function."""
    
    def test_parse_metadata_with_list_tags(self):
        """Test parsing metadata with list tags."""
        root = {
            "metadata": {
                "tags": {
                    "artist": ["Test Artist"],
                    "title": ["Test Track"],
                    "album": ["Test Album"]
                }
            }
        }
        
        result = parse_metadata_from_dump(root)
        assert result["artist"] == "Test Artist"
        assert result["track"] == "Test Track"
        assert result["album"] == "Test Album"
    
    def test_parse_metadata_with_string_tags(self):
        """Test parsing metadata with string tags."""
        root = {
            "metadata": {
                "tags": {
                    "artist": "Test Artist",
                    "title": "Test Track",
                    "album": "Test Album"
                }
            }
        }
        
        result = parse_metadata_from_dump(root)
        assert result["artist"] == "Test Artist"
        assert result["track"] == "Test Track"
        assert result["album"] == "Test Album"
    
    def test_parse_metadata_missing_tags(self):
        """Test parsing metadata with missing tags."""
        root = {
            "metadata": {}
        }
        
        result = parse_metadata_from_dump(root)
        assert result["artist"] == ""
        assert result["track"] == ""
        assert result["album"] == ""


class TestParseHighlevelExtra:
    """Test parse_highlevel_extra() function."""
    
    def test_parse_highlevel_extra_complete(self):
        """Test parsing high-level extra features."""
        root = {
            "metadata": {
                "audio_properties": {
                    "length": 240.0,
                    "replay_gain": -8.5
                }
            }
        }
        high_data = {
            "danceability": {"value": "danceable", "probability": 0.8},
            "voice_instrumental": {"value": "voice", "probability": 0.9},
            "timbre": {"value": "bright", "probability": 0.7},
            "mood_happy": {"value": "happy", "probability": 0.6},
            "mood_relaxed": {"value": "relaxed", "probability": 0.8}
        }
        
        result = parse_highlevel_extra(root, high_data)
        assert result["danceable"] == "danceable"
        assert result["voice_instrumental"] == "voice"
        assert result["timbre"] == "bright"
        assert "happy" in result["moods"]
        assert "relaxed" in result["moods"]
        assert result["duration"] == 240.0
        assert result["loudness"] == -8.5
    
    def test_parse_highlevel_extra_below_threshold(self):
        """Test features below confidence threshold are excluded."""
        high_data = {
            "danceability": {"value": "danceable", "probability": 0.3}  # Below 0.5
        }
        
        result = parse_highlevel_extra({}, high_data)
        assert result["danceable"] is None


class TestTempoBucket:
    """Test tempo_bucket() function."""
    
    def test_tempo_bucket_normal(self):
        """Test tempo bucketing for normal values."""
        assert tempo_bucket(120.5) == "120-130"
        assert tempo_bucket(125.0) == "120-130"
        assert tempo_bucket(130.0) == "130-140"
    
    def test_tempo_bucket_none(self):
        """Test tempo_bucket returns None for None input."""
        assert tempo_bucket(None) is None
    
    def test_tempo_bucket_edge_cases(self):
        """Test tempo bucketing for edge cases."""
        assert tempo_bucket(0.0) == "0-10"
        assert tempo_bucket(9.9) == "0-10"
        assert tempo_bucket(10.0) == "10-20"


class TestGetNested:
    """Test _get_nested() helper function."""
    
    def test_get_nested_existing_path(self):
        """Test getting nested value with existing path."""
        data = {"a": {"b": {"c": "value"}}}
        result = _get_nested(data, "a", "b", "c")
        assert result == "value"
    
    def test_get_nested_missing_key(self):
        """Test getting nested value with missing key."""
        data = {"a": {"b": {}}}
        result = _get_nested(data, "a", "b", "c")
        assert result is None
    
    def test_get_nested_none_data(self):
        """Test getting nested value from None data."""
        result = _get_nested(None, "a", "b")
        assert result is None
    
    def test_get_nested_non_dict(self):
        """Test getting nested value when intermediate is not dict."""
        data = {"a": "not_a_dict"}
        result = _get_nested(data, "a", "b")
        assert result is None


class TestValueIfConfident:
    """Test _value_if_confident() function."""
    
    def test_value_if_confident_above_threshold(self):
        """Test value returned when probability above threshold."""
        obj = {"value": "test", "probability": 0.8}
        result = _value_if_confident(obj)
        assert result == "test"
    
    def test_value_if_confident_below_threshold(self):
        """Test None returned when probability below threshold."""
        obj = {"value": "test", "probability": 0.3}
        result = _value_if_confident(obj, min_prob=0.5)
        assert result is None
    
    def test_value_if_confident_custom_threshold(self):
        """Test custom probability threshold."""
        obj = {"value": "test", "probability": 0.4}
        result = _value_if_confident(obj, min_prob=0.3)
        assert result == "test"
    
    def test_value_if_confident_invalid_object(self):
        """Test None returned for invalid object."""
        assert _value_if_confident(None) is None
        assert _value_if_confident("not_a_dict") is None


class TestBuildKnowledgeBase:
    """Test build_knowledge_base() function."""
    
    def test_build_kb_complete_song(self):
        """Test building KB with complete song data."""
        songs = [
            {
                "mbid": "test-001",
                "artist": "Test Artist",
                "track": "Test Song",
                "album": "Test Album",
                "audio_features": {
                    "tempo": 120.0,
                    "loudness": -8.5,
                    "duration": 240.0
                },
                "genres": ["rock", "alternative"],
                "danceable": "danceable",
                "voice_instrumental": "voice",
                "timbre": "bright",
                "moods": ["happy", "relaxed"]
            }
        ]
        
        kb = build_knowledge_base(songs)
        
        # Check songs
        assert "test-001" in kb["songs"]
        assert kb["songs"]["test-001"]["artist"] == "Test Artist"
        
        # Check facts
        assert kb["facts"]["has_tempo"]["test-001"] == 120.0
        assert kb["facts"]["has_loudness"]["test-001"] == -8.5
        assert "rock" in kb["facts"]["has_genre"]["test-001"]
        assert "alternative" in kb["facts"]["has_genre"]["test-001"]
        assert kb["facts"]["has_danceable"]["test-001"] == "danceable"
        assert "happy" in kb["facts"]["has_mood"]["test-001"]
        
        # Check indexes
        assert "test-001" in kb["indexes"]["by_genre"]["rock"]
        assert "test-001" in kb["indexes"]["by_danceable"]["danceable"]
        assert "test-001" in kb["indexes"]["by_mood"]["happy"]
    
    def test_build_kb_missing_mbid(self):
        """Test building KB skips songs without MBID."""
        songs = [
            {"artist": "Test", "track": "Song"},  # No MBID
            {"mbid": "test-001", "artist": "Test", "track": "Song"}
        ]
        
        kb = build_knowledge_base(songs)
        assert len(kb["songs"]) == 1
        assert "test-001" in kb["songs"]
    
    def test_build_kb_empty_songs(self):
        """Test building KB with empty song list."""
        kb = build_knowledge_base([])
        assert len(kb["songs"]) == 0
        assert len(kb["facts"]["has_genre"]) == 0
    
    def test_build_kb_duplicate_genres_removed(self):
        """Test duplicate genres are removed from facts."""
        songs = [
            {
                "mbid": "test-001",
                "genres": ["rock", "rock", "alternative"]
            }
        ]
        
        kb = build_knowledge_base(songs)
        genres = kb["facts"]["has_genre"]["test-001"]
        assert genres.count("rock") == 1
        assert len(genres) == 2
    
    def test_build_kb_tempo_bucketing(self):
        """Test tempo is bucketed in index."""
        songs = [
            {
                "mbid": "test-001",
                "audio_features": {"tempo": 125.0}
            }
        ]
        
        kb = build_knowledge_base(songs)
        assert "test-001" in kb["indexes"]["by_tempo_range"]["120-130"]
    
    def test_build_kb_missing_audio_features(self):
        """Test building KB handles missing audio features."""
        songs = [
            {
                "mbid": "test-001",
                "genres": ["rock"]
            }
        ]
        
        kb = build_knowledge_base(songs)
        assert "test-001" in kb["songs"]
        assert "test-001" not in kb["facts"]["has_tempo"]
        assert "test-001" in kb["facts"]["has_genre"]
        assert "rock" in kb["facts"]["has_genre"]["test-001"]


class TestBuildKnowledgeBaseEdgeCases:
    """Test edge cases for build_knowledge_base()."""
    
    def test_build_kb_partial_data(self):
        """Test building KB with partial data."""
        songs = [
            {
                "mbid": "test-001",
                "artist": "Test",
                "track": "Song",
                "genres": ["rock"]
                # Missing audio_features, danceable, etc.
            }
        ]
        
        kb = build_knowledge_base(songs)
        assert "test-001" in kb["songs"]
        assert "test-001" in kb["facts"]["has_genre"]
        assert "rock" in kb["facts"]["has_genre"]["test-001"]
        assert "test-001" not in kb["facts"]["has_danceable"]
    
    def test_build_kb_empty_genres(self):
        """Test building KB with empty genres list."""
        songs = [
            {
                "mbid": "test-001",
                "genres": []
            }
        ]
        
        kb = build_knowledge_base(songs)
        assert "test-001" in kb["songs"]
        assert "test-001" not in kb["facts"]["has_genre"]
    
    def test_build_kb_multiple_moods(self):
        """Test building KB with multiple moods."""
        songs = [
            {
                "mbid": "test-001",
                "moods": ["happy", "relaxed", "party"]
            }
        ]
        
        kb = build_knowledge_base(songs)
        moods = kb["facts"]["has_mood"]["test-001"]
        assert len(moods) == 3
        assert "happy" in moods
        assert "relaxed" in moods
        assert "party" in moods
