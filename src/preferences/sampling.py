"""
Song Sampling for Module 2

Sample songs from the knowledge base for user rating.
Supports random, stratified, preference-based, and score-based sampling.
"""

import random
from typing import List, Optional
from collections import defaultdict
from .survey import PreferenceProfile


def sample_random(kb, n: int, seed: Optional[int] = None) -> List[str]:
    """
    Randomly sample N songs from the knowledge base.
    
    Args:
        kb: KnowledgeBase instance
        n: Number of songs to sample
        seed: Optional random seed for reproducibility
        
    Returns:
        List of MBIDs
    """
    if seed is not None:
        random.seed(seed)
    
    all_songs = kb.get_all_songs()
    if len(all_songs) <= n:
        return all_songs
    
    return random.sample(all_songs, n)


def sample_stratified(kb, n: int, seed: Optional[int] = None) -> List[str]:
    """
    Stratified sampling: ensure diversity across genres and moods.
    
    Tries to sample songs from different genres/moods to give user variety.
    
    Args:
        kb: KnowledgeBase instance
        n: Number of songs to sample
        seed: Optional random seed for reproducibility
        
    Returns:
        List of MBIDs
    """
    if seed is not None:
        random.seed(seed)
    
    all_songs = kb.get_all_songs()
    if len(all_songs) <= n:
        return all_songs
    
    # Group songs by genre and mood
    by_genre = defaultdict(list)
    by_mood = defaultdict(list)
    
    for mbid in all_songs:
        genres = kb.get_fact('has_genre', mbid)
        if genres:
            if isinstance(genres, list):
                for genre in genres[:1]:  # Use first genre
                    by_genre[genre.lower()].append(mbid)
            else:
                by_genre[str(genres).lower()].append(mbid)
        
        moods = kb.get_fact('has_mood', mbid)
        if moods:
            if isinstance(moods, list):
                for mood in moods[:1]:  # Use first mood
                    by_mood[mood.lower()].append(mbid)
            else:
                by_mood[str(moods).lower()].append(mbid)
    
    # Sample from different groups
    sampled = []
    genres_list = list(by_genre.keys())
    moods_list = list(by_mood.keys())
    
    # Try to get at least one song from different genres/moods
    songs_per_group = max(1, n // max(len(genres_list), len(moods_list), 1))
    
    # Sample from genres
    for genre in genres_list[:n]:
        if len(sampled) >= n:
            break
        genre_songs = by_genre[genre]
        if genre_songs:
            sampled.extend(random.sample(genre_songs, min(songs_per_group, len(genre_songs))))
    
    # Sample from moods if we need more
    if len(sampled) < n:
        for mood in moods_list:
            if len(sampled) >= n:
                break
            mood_songs = [s for s in by_mood[mood] if s not in sampled]
            if mood_songs:
                sampled.append(random.choice(mood_songs))
    
    # Fill remaining slots randomly
    if len(sampled) < n:
        remaining = [s for s in all_songs if s not in sampled]
        needed = n - len(sampled)
        sampled.extend(random.sample(remaining, min(needed, len(remaining))))
    
    # Shuffle and return exactly n
    random.shuffle(sampled)
    return sampled[:n]


def sample_by_preferences(kb, profile: PreferenceProfile, n: int, seed: Optional[int] = None) -> List[str]:
    """
    Sample songs that match user preferences from the survey profile.
    
    Prioritizes songs that match the user's preferred genres, moods, and other
    preferences. Ensures variety while still being relevant to preferences.
    
    Args:
        kb: KnowledgeBase instance
        profile: PreferenceProfile from survey
        n: Number of songs to sample
        seed: Optional random seed for reproducibility
        
    Returns:
        List of MBIDs matching preferences
    """
    if seed is not None:
        random.seed(seed)
    
    all_songs = kb.get_all_songs()
    if len(all_songs) <= n:
        return all_songs
    
    # Score songs by how many preferences they match
    scored_songs = []
    
    for mbid in all_songs:
        match_score = 0
        matches = []
        
        # Check genre match
        if profile.preferred_genres:
            song_genres = kb.get_fact('has_genre', mbid)
            if song_genres:
                song_genres_list = song_genres if isinstance(song_genres, list) else [song_genres]
                song_genres_lower = [g.lower() for g in song_genres_list]
                preferred_lower = [g.lower() for g in profile.preferred_genres]
                if any(g in preferred_lower for g in song_genres_lower):
                    match_score += 2  # Genre match is important
                    matches.append("genre")
        
        # Check mood match
        if profile.preferred_moods:
            song_moods = kb.get_fact('has_mood', mbid)
            if song_moods:
                song_moods_list = song_moods if isinstance(song_moods, list) else [song_moods]
                song_moods_lower = [m.lower() for m in song_moods_list]
                preferred_lower = [m.lower() for m in profile.preferred_moods]
                if any(m in preferred_lower for m in song_moods_lower):
                    match_score += 2  # Mood match is important
                    matches.append("mood")
        
        # Check danceability match
        if profile.danceable:
            song_danceable = kb.get_fact('has_danceable', mbid)
            if song_danceable and song_danceable.lower() == profile.danceable.lower():
                match_score += 1
                matches.append("danceable")
        
        # Check voice/instrumental match
        if profile.voice_instrumental:
            song_vi = kb.get_fact('has_voice_instrumental', mbid)
            if song_vi and song_vi.lower() == profile.voice_instrumental.lower():
                match_score += 1
                matches.append("voice_instrumental")
        
        # Check timbre match
        if profile.timbre:
            song_timbre = kb.get_fact('has_timbre', mbid)
            if song_timbre and song_timbre.lower() == profile.timbre.lower():
                match_score += 1
                matches.append("timbre")
        
        # Check loudness match
        if profile.has_loudness_preference():
            song_loudness = kb.get_fact('has_loudness', mbid)
            if song_loudness is not None:
                if profile.loudness_min <= song_loudness <= profile.loudness_max:
                    match_score += 1
                    matches.append("loudness")
        
        scored_songs.append((mbid, match_score, matches))
    
    # Sort by match score (descending)
    scored_songs.sort(key=lambda x: x[1], reverse=True)
    
    # Take top matches, but ensure variety
    # Strategy: take top-scoring songs, but try to get variety across genres/moods
    sampled = []
    seen_genres = set()
    seen_moods = set()
    
    # First pass: prioritize high-scoring songs with variety
    for mbid, score, matches in scored_songs:
        if len(sampled) >= n:
            break
        
        # Check if this adds variety
        song_genres = kb.get_fact('has_genre', mbid)
        song_moods = kb.get_fact('has_mood', mbid)
        
        adds_variety = False
        if song_genres:
            genres_list = song_genres if isinstance(song_genres, list) else [song_genres]
            if not any(g.lower() in seen_genres for g in genres_list):
                adds_variety = True
                seen_genres.update(g.lower() for g in genres_list)
        
        if song_moods:
            moods_list = song_moods if isinstance(song_moods, list) else [song_moods]
            if not any(m.lower() in seen_moods for m in moods_list):
                adds_variety = True
                seen_moods.update(m.lower() for m in moods_list)
        
        # Prefer songs with at least some match (score > 0) or that add variety
        if score > 0 or adds_variety or len(sampled) < n // 2:
            sampled.append(mbid)
    
    # Second pass: fill remaining slots with best matches
    if len(sampled) < n:
        remaining = [mbid for mbid, _, _ in scored_songs if mbid not in sampled]
        needed = n - len(sampled)
        sampled.extend(remaining[:needed])
    
    # Shuffle to avoid always showing same order
    random.shuffle(sampled)
    return sampled[:n]


def sample_by_initial_score(kb, n: int, scorer, seed: Optional[int] = None) -> List[str]:
    """
    Sample top-N songs by initial rule-based score.
    
    This requires a scorer object that can score songs. Use this after
    building initial rules from the preference profile.
    
    Args:
        kb: KnowledgeBase instance
        n: Number of songs to sample
        scorer: Scorer object with score(mbid, kb) method
        seed: Optional random seed (for tie-breaking)
        
    Returns:
        List of MBIDs (top-N by score)
    """
    if seed is not None:
        random.seed(seed)
    
    all_songs = kb.get_all_songs()
    if len(all_songs) <= n:
        return all_songs
    
    # Score all songs
    scored = []
    for mbid in all_songs:
        try:
            score = scorer.score(mbid, kb)
            scored.append((mbid, score))
        except Exception:
            # Skip songs that can't be scored
            continue
    
    # Sort by score (descending) and take top N
    scored.sort(key=lambda x: x[1], reverse=True)
    return [mbid for mbid, _ in scored[:n]]


def sample_songs(kb, n: int = 15, method: str = "stratified", 
                scorer=None, profile: Optional[PreferenceProfile] = None, 
                seed: Optional[int] = None) -> List[str]:
    """
    Sample songs from knowledge base using specified method.
    
    Args:
        kb: KnowledgeBase instance
        n: Number of songs to sample (default: 15)
        method: Sampling method - 'random', 'stratified', 'preference_based', or 'score_based'
        scorer: Scorer object (required for 'score_based' method)
        profile: PreferenceProfile (required for 'preference_based' method)
        seed: Optional random seed
        
    Returns:
        List of MBIDs
        
    Raises:
        ValueError: If method is invalid or required parameters missing
    """
    if method == "random":
        return sample_random(kb, n, seed)
    elif method == "stratified":
        return sample_stratified(kb, n, seed)
    elif method == "preference_based":
        if profile is None:
            raise ValueError("profile is required for preference_based sampling")
        return sample_by_preferences(kb, profile, n, seed)
    elif method == "score_based":
        if scorer is None:
            raise ValueError("scorer is required for score_based sampling")
        return sample_by_initial_score(kb, n, scorer, seed)
    else:
        raise ValueError(f"Invalid sampling method: {method}. Must be 'random', 'stratified', 'preference_based', or 'score_based'")
