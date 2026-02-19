"""
MusicBrainz API client for searching recordings and fetching credits/metadata by MBID.
"""

import logging
import time
from typing import List, Optional, Tuple

import musicbrainzngs

logger = logging.getLogger(__name__)

REQUEST_DELAY = 1.0  # MusicBrainz requires 1 request per second
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

# Required: identify your application (MusicBrainz policy)
musicbrainzngs.set_useragent(
    "project-2-ai-system",
    "0.1",
    "https://github.com/",
)
musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)


def _normalize_artist(name: str) -> str:
    """Normalize artist name for comparison (lowercase, strip, remove leading 'The')."""
    if not name:
        return ""
    s = name.strip().lower()
    if s.startswith("the "):
        s = s[4:].strip()
    return s


def _get_main_artist_from_recording(recording: dict) -> str:
    """Extract main artist name from a recording in search results."""
    credits = recording.get("artist-credit")
    if not credits:
        return ""
    # Handle name-credit wrapper: artist-credit -> name-credit -> [ { artist: {...} } ]
    if isinstance(credits, dict) and "name-credit" in credits:
        nc = credits["name-credit"]
        nc_list = nc if isinstance(nc, list) else [nc]
        first = nc_list[0] if nc_list else {}
    else:
        nc_list = credits if isinstance(credits, list) else [credits]
        first = nc_list[0] if nc_list else {}
    if isinstance(first, dict):
        artist = first.get("artist", {})
        if isinstance(artist, dict):
            return artist.get("name", "")
        return ""
    return str(first)


def _artist_matches(requested: str, actual: str) -> bool:
    """Check if the actual artist matches the requested artist (handles 'The Beatles' vs 'Beatles')."""
    r = _normalize_artist(requested)
    a = _normalize_artist(actual)
    if not r or not a:
        return False
    return r == a or r in a or a in r


def search_recording(artist: str, track: str) -> Optional[str]:
    """
    Search MusicBrainz for a recording by artist and track name.
    Prefers the original artist's recording over covers.
    Retries on connection reset / network errors.
    """
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY)
        try:
            result = musicbrainzngs.search_recordings(
                query=track,
                artist=artist,
                limit=25,
            )
            recordings = result.get("recording-list", [])
            if not recordings:
                return None
            for rec in recordings:
                main_artist = _get_main_artist_from_recording(rec)
                if _artist_matches(artist, main_artist):
                    return rec.get("id")
            return recordings[0].get("id")
        except musicbrainzngs.ResponseError as e:
            logger.warning("MusicBrainz search failed for %s - %s: %s", artist, track, e)
            return None
        except musicbrainzngs.NetworkError as e:
            err_str = str(e).lower()
            if ("connection reset" in err_str or "errno 54" in err_str) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF * (2**attempt)
                logger.warning("MusicBrainz connection error for %s - %s, retrying in %.1fs (attempt %d/%d)", artist, track, wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
            else:
                logger.warning("MusicBrainz network error for %s - %s: %s", artist, track, e)
                return None
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


def _get_artist_name_from_relation(rel: dict) -> str:
    """Extract artist name from a relation dict."""
    artist = rel.get("artist", {})
    if isinstance(artist, dict):
        return artist.get("name", "")
    return str(artist) if artist else ""


def _extract_relations(recording: dict) -> Tuple[List[str], List[str]]:
    """
    Extract writers and producers from recording relations.
    - Producers: from artist-rels (recording-artist, type=producer)
    - Writers: from work-rels -> work's artist relations (composer, lyricist)
    Returns (writers, producers).
    """
    writers = []
    producers = []
    relation_list = recording.get("relation-list", [])
    if not isinstance(relation_list, list):
        relation_list = [relation_list] if relation_list else []

    for rel_group in relation_list:
        if not isinstance(rel_group, dict):
            continue
        # rel_group has target-type ("artist" or "work") and relation(s)
        target_type = (rel_group.get("target-type") or "").lower()
        rel_items = rel_group.get("relation") or rel_group.get("relation-list")
        if rel_items is None:
            continue
        if not isinstance(rel_items, list):
            rel_items = [rel_items]

        for rel in rel_items:
            if not isinstance(rel, dict):
                continue

            # Recording-Artist relations: producer, engineer, etc.
            if target_type == "artist":
                rel_type = (rel.get("type") or "")
                if isinstance(rel_type, list):
                    rel_type = " ".join(str(x) for x in rel_type)
                rel_type = str(rel_type).lower()
                name = _get_artist_name_from_relation(rel)
                if name and "producer" in rel_type:
                    producers.append(name)

            # Recording-Work relations: traverse to work's composer/lyricist
            elif target_type == "work":
                work = rel.get("work", {})
                if isinstance(work, dict):
                    work_rels = work.get("relation-list", [])
                    if not isinstance(work_rels, list):
                        work_rels = [work_rels] if work_rels else []
                    for wr in work_rels:
                        if not isinstance(wr, dict):
                            continue
                        wt = (wr.get("target-type") or "").lower()
                        if wt != "artist":
                            continue
                        w_rel_items = wr.get("relation") or wr.get("relation-list")
                        if w_rel_items is None:
                            continue
                        if not isinstance(w_rel_items, list):
                            w_rel_items = [w_rel_items]
                        for wrel in w_rel_items:
                            if not isinstance(wrel, dict):
                                continue
                            wrel_type = (wrel.get("type") or "").lower()
                            name = _get_artist_name_from_relation(wrel)
                            if name and wrel_type in ("composer", "lyricist", "writer", "librettist"):
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
            includes=["artist-credits", "releases", "artist-rels", "work-rels"],
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
