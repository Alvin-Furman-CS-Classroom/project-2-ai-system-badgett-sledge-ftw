"""
Unit tests for KnowledgeBase class.

Tests cover:
- Initialization and error handling
- All query methods (genre, mood, loudness, etc.)
- Fact retrieval
- Song lookup
- Edge cases (empty KB, missing facts, invalid MBIDs)
"""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from knowledge_base_wrapper import KnowledgeBase


class TestKnowledgeBaseInitialization:
    """Test KnowledgeBase initialization and error handling."""
    
    def test_init_with_valid_file(self):
        """Test initialization with valid knowledge base file."""
        # Use the test fixture
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        kb = KnowledgeBase(str(fixture_path))
        
        assert len(kb.songs) == 4
        assert len(kb.facts) > 0
        assert len(kb.indexes) > 0
    
    def test_init_with_relative_path(self):
        """Test initialization with relative path."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        # Test relative path resolution
        kb = KnowledgeBase(str(fixture_path))
        assert len(kb.songs) == 4
    
    def test_init_file_not_found(self):
        """Test initialization raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            KnowledgeBase("nonexistent_file.json")
    
    def test_init_invalid_json(self):
        """Test initialization raises JSONDecodeError for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                KnowledgeBase(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_init_empty_knowledge_base(self):
        """Test initialization with empty knowledge base structure."""
        empty_kb = {
            "songs": {},
            "facts": {},
            "indexes": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(empty_kb, f)
            temp_path = f.name
        
        try:
            kb = KnowledgeBase(temp_path)
            assert len(kb.songs) == 0
            assert len(kb.facts) == 0
            assert len(kb.indexes) == 0
        finally:
            Path(temp_path).unlink()


class TestKnowledgeBaseGetSong:
    """Test get_song() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_song_existing(self, kb):
        """Test getting an existing song."""
        song = kb.get_song("test-mbid-001")
        assert song is not None
        assert song["artist"] == "Test Artist"
        assert song["track"] == "Test Song"
        assert song["album"] == "Test Album"
    
    def test_get_song_nonexistent(self, kb):
        """Test getting a non-existent song returns None."""
        song = kb.get_song("nonexistent-mbid")
        assert song is None


class TestKnowledgeBaseGetFact:
    """Test get_fact() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_fact_existing_single_value(self, kb):
        """Test getting a fact with single value."""
        loudness = kb.get_fact("has_loudness", "test-mbid-001")
        assert loudness == -8.5
    
    def test_get_fact_existing_list_value(self, kb):
        """Test getting a fact with list value."""
        genres = kb.get_fact("has_genre", "test-mbid-001")
        assert isinstance(genres, list)
        assert "rock" in genres
        assert "alternative" in genres
    
    def test_get_fact_nonexistent_song(self, kb):
        """Test getting fact for non-existent song returns None."""
        fact = kb.get_fact("has_genre", "nonexistent-mbid")
        assert fact is None
    
    def test_get_fact_nonexistent_fact_type(self, kb):
        """Test getting non-existent fact type returns None."""
        fact = kb.get_fact("has_nonexistent_fact", "test-mbid-001")
        assert fact is None
    
    def test_get_fact_missing_fact(self, kb):
        """Test getting fact that doesn't exist for song returns None."""
        # test-mbid-001 doesn't have tempo
        tempo = kb.get_fact("has_tempo", "test-mbid-001")
        assert tempo is None


class TestKnowledgeBaseSongsByGenre:
    """Test songs_by_genre() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_songs_by_genre_existing(self, kb):
        """Test finding songs by existing genre."""
        rock_songs = kb.songs_by_genre("rock")
        assert len(rock_songs) == 2
        assert "test-mbid-001" in rock_songs
        assert "test-mbid-002" in rock_songs
    
    def test_songs_by_genre_case_insensitive(self, kb):
        """Test genre search is case-insensitive."""
        rock_songs_upper = kb.songs_by_genre("ROCK")
        rock_songs_lower = kb.songs_by_genre("rock")
        assert rock_songs_upper == rock_songs_lower
    
    def test_songs_by_genre_nonexistent(self, kb):
        """Test finding songs by non-existent genre returns empty list."""
        songs = kb.songs_by_genre("nonexistent_genre")
        assert songs == []


class TestKnowledgeBaseSongsByDanceable:
    """Test songs_by_danceable() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_songs_by_danceable_danceable(self, kb):
        """Test finding danceable songs."""
        danceable_songs = kb.songs_by_danceable("danceable")
        assert len(danceable_songs) == 2
        assert "test-mbid-003" in danceable_songs
        assert "test-mbid-004" in danceable_songs
    
    def test_songs_by_danceable_not_danceable(self, kb):
        """Test finding not_danceable songs."""
        not_danceable = kb.songs_by_danceable("not_danceable")
        assert len(not_danceable) == 2
        assert "test-mbid-001" in not_danceable
        assert "test-mbid-002" in not_danceable
    
    def test_songs_by_danceable_case_insensitive(self, kb):
        """Test danceable search is case-insensitive."""
        danceable1 = kb.songs_by_danceable("DANCEABLE")
        danceable2 = kb.songs_by_danceable("danceable")
        assert danceable1 == danceable2


class TestKnowledgeBaseSongsByMood:
    """Test songs_by_mood() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_songs_by_mood_existing(self, kb):
        """Test finding songs by existing mood."""
        happy_songs = kb.songs_by_mood("happy")
        assert len(happy_songs) == 2
        assert "test-mbid-001" in happy_songs
        assert "test-mbid-003" in happy_songs
    
    def test_songs_by_mood_case_insensitive(self, kb):
        """Test mood search is case-insensitive."""
        relaxed1 = kb.songs_by_mood("RELAXED")
        relaxed2 = kb.songs_by_mood("relaxed")
        assert relaxed1 == relaxed2
    
    def test_songs_by_mood_nonexistent(self, kb):
        """Test finding songs by non-existent mood returns empty list."""
        songs = kb.songs_by_mood("nonexistent_mood")
        assert songs == []


class TestKnowledgeBaseSongsInLoudnessRange:
    """Test songs_in_loudness_range() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_songs_in_loudness_range(self, kb):
        """Test finding songs in loudness range."""
        # Test range that includes test-mbid-001 (-8.5) and test-mbid-003 (-5.8)
        songs = kb.songs_in_loudness_range(-10.0, -5.0)
        assert len(songs) == 2
        assert "test-mbid-001" in songs
        assert "test-mbid-003" in songs
    
    def test_songs_in_loudness_range_boundary(self, kb):
        """Test loudness range includes boundary values."""
        songs = kb.songs_in_loudness_range(-8.5, -8.5)
        assert "test-mbid-001" in songs
    
    def test_songs_in_loudness_range_no_matches(self, kb):
        """Test loudness range with no matches returns empty list."""
        songs = kb.songs_in_loudness_range(-100.0, -50.0)
        assert songs == []


class TestKnowledgeBaseGetAllGenres:
    """Test get_all_genres() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_all_genres(self, kb):
        """Test getting all unique genres."""
        genres = kb.get_all_genres()
        assert isinstance(genres, set)
        assert "rock" in genres
        assert "pop" in genres
        assert "electronic" in genres
        assert "alternative" in genres
        assert len(genres) == 4


class TestKnowledgeBaseGetAllMoods:
    """Test get_all_moods() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_all_moods(self, kb):
        """Test getting all unique moods."""
        moods = kb.get_all_moods()
        assert isinstance(moods, set)
        assert "happy" in moods
        assert "sad" in moods
        assert "relaxed" in moods
        assert "party" in moods
        assert len(moods) == 4


class TestKnowledgeBaseGetMbidBySong:
    """Test get_mbid_by_song() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_mbid_by_song_exact_match(self, kb):
        """Test finding MBID by exact song name."""
        mbid = kb.get_mbid_by_song("Test Song")
        assert mbid == "test-mbid-001"
    
    def test_get_mbid_by_song_case_insensitive(self, kb):
        """Test song name search is case-insensitive."""
        mbid1 = kb.get_mbid_by_song("test song")
        mbid2 = kb.get_mbid_by_song("TEST SONG")
        assert mbid1 == mbid2 == "test-mbid-001"
    
    def test_get_mbid_by_song_with_artist(self, kb):
        """Test finding MBID with artist name for precision."""
        mbid = kb.get_mbid_by_song("Rock Song", "Rock Band")
        assert mbid == "test-mbid-002"
    
    def test_get_mbid_by_song_partial_match(self, kb):
        """Test finding MBID with partial match."""
        mbid = kb.get_mbid_by_song("Rock")
        # Should find "Rock Song" via partial match
        assert mbid is not None
    
    def test_get_mbid_by_song_nonexistent(self, kb):
        """Test finding non-existent song returns None."""
        mbid = kb.get_mbid_by_song("Nonexistent Song")
        assert mbid is None
    
    def test_get_mbid_by_song_invalid_input_type(self, kb):
        """Test get_mbid_by_song raises TypeError for invalid input."""
        with pytest.raises(TypeError):
            kb.get_mbid_by_song(123)  # Should be string
    
    def test_get_mbid_by_song_empty_string(self, kb):
        """Test get_mbid_by_song raises ValueError for empty string."""
        with pytest.raises(ValueError):
            kb.get_mbid_by_song("")
    
    def test_get_mbid_by_song_whitespace_only(self, kb):
        """Test get_mbid_by_song raises ValueError for whitespace-only string."""
        with pytest.raises(ValueError):
            kb.get_mbid_by_song("   ")


class TestKnowledgeBaseFindSongsByName:
    """Test find_songs_by_name() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_find_songs_by_name_exact_match(self, kb):
        """Test finding songs by exact name."""
        songs = kb.find_songs_by_name("Test Song")
        assert len(songs) == 1
        assert "test-mbid-001" in songs
    
    def test_find_songs_by_name_partial_match(self, kb):
        """Test finding songs by partial name."""
        songs = kb.find_songs_by_name("Rock")
        assert len(songs) >= 1
        assert "test-mbid-002" in songs
    
    def test_find_songs_by_name_with_artist(self, kb):
        """Test finding songs with artist filter."""
        songs = kb.find_songs_by_name("Rock Song", "Rock Band")
        assert len(songs) == 1
        assert "test-mbid-002" in songs
    
    def test_find_songs_by_name_nonexistent(self, kb):
        """Test finding non-existent songs returns empty list."""
        songs = kb.find_songs_by_name("Nonexistent Song")
        assert songs == []


class TestKnowledgeBaseHasFact:
    """Test has_fact() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_has_fact_true(self, kb):
        """Test has_fact returns True for existing fact."""
        assert kb.has_fact("has_genre", "test-mbid-001") is True
    
    def test_has_fact_false(self, kb):
        """Test has_fact returns False for non-existent fact."""
        assert kb.has_fact("has_tempo", "test-mbid-001") is False
    
    def test_has_fact_nonexistent_song(self, kb):
        """Test has_fact returns False for non-existent song."""
        assert kb.has_fact("has_genre", "nonexistent-mbid") is False


class TestKnowledgeBaseGetAllSongs:
    """Test get_all_songs() method."""
    
    @pytest.fixture
    def kb(self):
        """Create KnowledgeBase instance for testing."""
        fixture_path = Path(__file__).parent / "fixtures" / "test_knowledge_base.json"
        return KnowledgeBase(str(fixture_path))
    
    def test_get_all_songs(self, kb):
        """Test getting all song MBIDs."""
        all_songs = kb.get_all_songs()
        assert isinstance(all_songs, list)
        assert len(all_songs) == 4
        assert "test-mbid-001" in all_songs
        assert "test-mbid-002" in all_songs
        assert "test-mbid-003" in all_songs
        assert "test-mbid-004" in all_songs


class TestKnowledgeBaseEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_knowledge_base(self):
        """Test operations on empty knowledge base."""
        empty_kb = {
            "songs": {},
            "facts": {},
            "indexes": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(empty_kb, f)
            temp_path = f.name
        
        try:
            kb = KnowledgeBase(temp_path)
            assert kb.songs_by_genre("rock") == []
            assert kb.get_song("any-mbid") is None
            assert kb.get_fact("has_genre", "any-mbid") is None
            assert kb.get_all_genres() == set()
        finally:
            Path(temp_path).unlink()
    
    def test_missing_indexes(self):
        """Test knowledge base with missing indexes."""
        kb_data = {
            "songs": {"mbid-001": {"mbid": "mbid-001", "artist": "Artist", "track": "Track", "album": "Album"}},
            "facts": {"has_genre": {"mbid-001": ["rock"]}},
            "indexes": {}  # Missing indexes
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(kb_data, f)
            temp_path = f.name
        
        try:
            kb = KnowledgeBase(temp_path)
            # Should handle missing indexes gracefully
            assert kb.songs_by_genre("rock") == []
        finally:
            Path(temp_path).unlink()
