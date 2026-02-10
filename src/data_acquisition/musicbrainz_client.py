"""
MusicBrainz API client for searching recordings and fetching credits/metadata by MBID.
"""

import logging
import time
from typing import List, Optional, Tuple

import musicbrainzngs

logger = logging.getLogger(__name__)

REQUEST_DELAY = 1.0  # MusicBrainz requires 1 request per second

# Required: identify your application (MusicBrainz policy)
musicbrainzngs.set_useragent(
    "project-2-ai-system",
    "0.1",
    "https://github.com/",
)
musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)


def search_recording(artist: str, track: str) -> Optional[str]:
    """
    Search MusicBrainz for a recording by artist and track name.

    Args:
        artist: Artist name
        track: Track/recording title

    Returns:
        MBID of best matching recording, or None if not found.
    """
    time.sleep(REQUEST_DELAY)

    try:
        result = musicbrainzngs.search_recordings(
            query=track,
            artist=artist,
            limit=5,
        )
        recordings = result.get("recording-list", [])
        if not recordings:
            return None
        # Return first (best) match
        return recordings[0].get("id")
    except musicbrainzngs.ResponseError as e:
        logger.warning("MusicBrainz search failed for %s - %s: %s", artist, track, e)
        return None
    except musicbrainzngs.NetworkError as e:
        logger.warning("MusicBrainz network error for %s - %s: %s", artist, track, e)
        return None


def _extract_artist_credits(recording: dict) -> Tuple[List[str], List[str]]:
    """
    Extract main artist and featured artists from artist-credit.
    Returns (main_artist, featured_artists).
    """
    main_artist = ""
    featured = []
    credits = recording.get("artist-credit", [])
    if not credits:
        return ("", [])

    # artist-credit can be a list of dicts with artist, name, joinphrase
    credit_list = credits if isinstance(credits, list) else [credits]
    for i, entry in enumerate(credit_list):
        if isinstance(entry, dict):
            artist = entry.get("artist", {})
            name = artist.get("name", entry.get("name", ""))
            if name:
                if i == 0:
                    main_artist = name
                else:
                    featured.append(name)
        elif isinstance(entry, str):
            if i == 0:
                main_artist = entry
            else:
                featured.append(entry)
    return (main_artist, featured)


def _extract_relations(recording: dict) -> Tuple[List[str], List[str]]:
    """
    Extract writers and producers from recording relations.
    Returns (writers, producers).
    """
    writers = []
    producers = []
    relations = recording.get("relation-list", [])

    for rel_group in relations:
        if not isinstance(rel_group, dict):
            continue
        rel_type = rel_group.get("type", "").lower()
        target_type = rel_group.get("target-type", "").lower()
        rel_list = rel_group.get("relation", [])
        if not isinstance(rel_list, list):
            rel_list = [rel_list] if rel_list else []

        for rel in rel_list:
            if not isinstance(rel, dict):
                continue
            artist = rel.get("artist", {})
            if isinstance(artist, dict):
                name = artist.get("name", "")
            else:
                name = str(artist) if artist else ""
            if not name:
                continue

            attr_type = (rel.get("type", "") or rel.get("type-id", "")).lower()
            if "producer" in rel_type or "producer" in attr_type:
                producers.append(name)
            elif "writer" in rel_type or "composer" in rel_type or "lyricist" in rel_type:
                writers.append(name)
            elif "composer" in attr_type or "lyricist" in attr_type or "writer" in attr_type:
                writers.append(name)

    return (list(dict.fromkeys(writers)), list(dict.fromkeys(producers)))


def _extract_language(recording: dict) -> Optional[str]:
    """Extract language from release or work relations."""
    # Try release-list (if included)
    releases = recording.get("release-list", [])
    if releases and isinstance(releases, list):
        for r in releases:
            if isinstance(r, dict):
                lang = r.get("text-representation", {}).get("language")
                if lang:
                    return lang
    return None


def get_recording_details(mbid: str) -> Optional[dict]:
    """
    Fetch full recording details including artist credits, writers, producers.

    Args:
        mbid: MusicBrainz recording ID (UUID format)

    Returns:
        Dict with mbid, title, artist, featured_artists, writers, producers, language,
        or None if not found or request fails.
    """
    time.sleep(REQUEST_DELAY)

    try:
        result = musicbrainzngs.get_recording_by_id(
            mbid,
            includes=["artist-credits", "releases", "recording-rels", "work-rels"],
        )
        recording = result.get("recording")
        if not recording:
            return None

        main_artist, featured = _extract_artist_credits(recording)
        writers, producers = _extract_relations(recording)
        language = _extract_language(recording)

        return {
            "mbid": mbid,
            "title": recording.get("title", ""),
            "artist": main_artist,
            "featured_artists": featured,
            "writers": writers,
            "producers": producers,
            "language": language,
        }
    except musicbrainzngs.ResponseError as e:
        logger.warning("MusicBrainz get_recording failed for %s: %s", mbid, e)
        return None
    except musicbrainzngs.NetworkError as e:
        logger.warning("MusicBrainz network error for %s: %s", mbid, e)
        return None


if __name__ == "__main__":
    # Test search and details
    mbid = search_recording("The Beatles", "Hey Jude")
    print("Search result MBID:", mbid)
    if mbid:
        details = get_recording_details(mbid)
        print("Recording details:", details)
