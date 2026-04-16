"""
Song Sampling for Module 2

Sample songs from the knowledge base for user rating.
Supports random, stratified, preference-based, and score-based sampling.
"""

import logging
import random
from collections import defaultdict
from typing import List, Optional, Set, Tuple, TYPE_CHECKING

from .survey import PreferenceProfile

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase

logger = logging.getLogger(__name__)

# Preference-based sampling: score weight for genre/mood match vs single-feature match
GENRE_MATCH_WEIGHT = 2
MOOD_MATCH_WEIGHT = 2
SINGLE_FEATURE_MATCH_WEIGHT = 1
DEFAULT_EXPLOIT_RATIO = 0.6


def sample_random(kb: "KnowledgeBase", n: int, seed: Optional[int] = None) -> List[str]:
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


def sample_stratified(kb: "KnowledgeBase", n: int, seed: Optional[int] = None) -> List[str]:
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
        genres = kb.get_fact("has_genre", mbid)
        if genres:
            if isinstance(genres, list):
                for genre in genres[:1]:  # Use first genre
                    by_genre[genre.lower()].append(mbid)
            else:
                by_genre[str(genres).lower()].append(mbid)
        
        moods = kb.get_fact("has_mood", mbid)
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


def _score_song_for_profile(
    kb: "KnowledgeBase", mbid: str, profile: PreferenceProfile
) -> Tuple[str, int, List[str]]:
    """Score one song by how well it matches the profile. Returns (mbid, match_score, match_labels)."""
    match_score = 0
    matches: List[str] = []

    if profile.preferred_genres:
        song_genres = kb.get_fact("has_genre", mbid)
        if song_genres:
            song_list = song_genres if isinstance(song_genres, list) else [song_genres]
            preferred_lower = [g.lower() for g in profile.preferred_genres]
            if any(g.lower() in preferred_lower for g in song_list):
                match_score += GENRE_MATCH_WEIGHT
                matches.append("genre")

    if profile.preferred_moods:
        song_moods = kb.get_fact("has_mood", mbid)
        if song_moods:
            song_list = song_moods if isinstance(song_moods, list) else [song_moods]
            preferred_lower = [m.lower() for m in profile.preferred_moods]
            if any(m.lower() in preferred_lower for m in song_list):
                match_score += MOOD_MATCH_WEIGHT
                matches.append("mood")

    if profile.danceable:
        val = kb.get_fact("has_danceable", mbid)
        if val and str(val).lower() == profile.danceable.lower():
            match_score += SINGLE_FEATURE_MATCH_WEIGHT
            matches.append("danceable")

    if profile.voice_instrumental:
        val = kb.get_fact("has_voice_instrumental", mbid)
        if val and str(val).lower() == profile.voice_instrumental.lower():
            match_score += SINGLE_FEATURE_MATCH_WEIGHT
            matches.append("voice_instrumental")

    if profile.timbre:
        val = kb.get_fact("has_timbre", mbid)
        if val and str(val).lower() == profile.timbre.lower():
            match_score += SINGLE_FEATURE_MATCH_WEIGHT
            matches.append("timbre")

    if profile.has_loudness_preference():
        song_loudness = kb.get_fact("has_loudness", mbid)
        if song_loudness is not None and profile.loudness_min is not None and profile.loudness_max is not None:
            if profile.loudness_min <= song_loudness <= profile.loudness_max:
                match_score += SINGLE_FEATURE_MATCH_WEIGHT
                matches.append("loudness")

    return (mbid, match_score, matches)


def _select_with_variety(
    kb: "KnowledgeBase",
    scored_songs: List[Tuple[str, int, List[str]]],
    n: int,
) -> List[str]:
    """Select up to n MBIDs from scored_songs, favoring variety in genre/mood."""
    sampled: List[str] = []
    seen_genres: Set[str] = set()
    seen_moods: Set[str] = set()
    half_n = n // 2

    for mbid, score, _ in scored_songs:
        if len(sampled) >= n:
            break
        song_genres = kb.get_fact("has_genre", mbid)
        song_moods = kb.get_fact("has_mood", mbid)
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
        if score > 0 or adds_variety or len(sampled) < half_n:
            sampled.append(mbid)

    if len(sampled) < n:
        remaining = [mbid for mbid, _, _ in scored_songs if mbid not in sampled]
        sampled.extend(remaining[: n - len(sampled)])
    random.shuffle(sampled)
    return sampled[:n]


def sample_by_preferences(
    kb: "KnowledgeBase", profile: PreferenceProfile, n: int, seed: Optional[int] = None
) -> List[str]:
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
    scored_songs = [_score_song_for_profile(kb, mbid, profile) for mbid in all_songs]
    scored_songs.sort(key=lambda x: x[1], reverse=True)
    return _select_with_variety(kb, scored_songs, n)


def sample_by_initial_score(
    kb: "KnowledgeBase", n: int, scorer, seed: Optional[int] = None
) -> List[str]:
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
    
    scored = []
    for mbid in all_songs:
        try:
            score = scorer.score(mbid, kb)
            scored.append((mbid, score))
        except (TypeError, AttributeError, KeyError) as e:
            logger.debug("Skip scoring %s: %s", mbid, e)
            continue

    # Sort by score (descending) and take top N
    scored.sort(key=lambda x: x[1], reverse=True)
    return [mbid for mbid, _ in scored[:n]]


def sample_next_batch(
    kb: "KnowledgeBase",
    n: int,
    scorer,
    already_rated_mbids: List[str],
    seed: Optional[int] = None,
    exploit_ratio: float = DEFAULT_EXPLOIT_RATIO,
) -> List[str]:
    """
    Adaptive (hill-climbing) batch: select next N songs to rate using current scorer.
    Excludes already-rated songs. Picks a mix of high-scoring (exploit) and
    mid-scoring / boundary (explore) songs for active learning.

    Args:
        kb: KnowledgeBase instance
        n: Number of songs to sample
        scorer: Scorer with score(mbid, kb) method (e.g. PreferenceScorer)
        already_rated_mbids: MBIDs the user has already rated (will be excluded)
        seed: Optional random seed for reproducibility
        exploit_ratio: Fraction of batch from top-scoring songs (0–1); rest from boundary

    Returns:
        List of N (or fewer) MBIDs, excluding already_rated_mbids
    """
    if seed is not None:
        random.seed(seed)

    rated_set = set(already_rated_mbids)
    all_songs = kb.get_all_songs()
    unrated = [m for m in all_songs if m not in rated_set]

    if len(unrated) <= n:
        return unrated

    scored = []
    for mbid in unrated:
        try:
            s = scorer.score(mbid, kb)
            scored.append((mbid, s))
        except (TypeError, AttributeError, KeyError) as e:
            logger.debug("Skip scoring %s: %s", mbid, e)
            continue

    if not scored:
        return random.sample(unrated, min(n, len(unrated)))

    scored.sort(key=lambda x: x[1], reverse=True)
    num_exploit = max(1, int(n * exploit_ratio))
    num_explore = n - num_exploit

    exploit_batch = [mbid for mbid, _ in scored[:num_exploit]]
    mid_start = max(0, len(scored) // 2 - num_explore // 2)
    mid_end = min(len(scored), mid_start + num_explore)
    explore_candidates = [mbid for mbid, _ in scored[mid_start:mid_end] if mbid not in exploit_batch]
    explore_batch = explore_candidates[:num_explore]

    result = list(exploit_batch)
    for m in explore_batch:
        if m not in result:
            result.append(m)
    if len(result) < n:
        remaining = [mbid for mbid, _ in scored if mbid not in result]
        result.extend(remaining[: n - len(result)])
    random.shuffle(result)
    return result[:n]


def sample_songs(
    kb: "KnowledgeBase",
    n: int = 15,
    method: str = "stratified",
    scorer=None,
    profile: Optional[PreferenceProfile] = None,
    seed: Optional[int] = None,
) -> List[str]:
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
    if method == "stratified":
        return sample_stratified(kb, n, seed)
    if method == "preference_based":
        if profile is None:
            raise ValueError("profile is required for preference_based sampling")
        return sample_by_preferences(kb, profile, n, seed)
    if method == "score_based":
        if scorer is None:
            raise ValueError("scorer is required for score_based sampling")
        return sample_by_initial_score(kb, n, scorer, seed)

    raise ValueError(
        f"Invalid sampling method: {method}. Must be 'random', 'stratified', "
        "'preference_based', or 'score_based'"
    )
