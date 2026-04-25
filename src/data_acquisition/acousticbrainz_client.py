"""
AcousticBrainz API client for fetching low-level and high-level audio features by MBID.
"""

import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://acousticbrainz.org/api/v1"
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


def _get_nested(data: dict, *keys: str) -> Any:
    """Safely get a nested value from a dict."""
    for key in keys:
        if data is None or not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _get_recording_data(response: dict, mbid: str) -> Optional[dict]:
    """
    Extract recording data from API response.
    Response format: { "mbid": { "0": { ... } } } or { "mbid": { ... } }
    """
    mbid_data = response.get(mbid)
    if mbid_data is None:
        # Try lowercase MBID (API normalizes to lowercase)
        mbid_lower = mbid.lower()
        mbid_data = response.get(mbid_lower)
    if mbid_data is None:
        return None
    # May be nested under "0" (segment offset)
    if isinstance(mbid_data, dict) and "0" in mbid_data and len(mbid_data) == 1:
        return mbid_data["0"]
    return mbid_data if isinstance(mbid_data, dict) else None


def get_low_level_features(mbid: str) -> Optional[dict]:
    """
    Fetch low-level audio features for a recording.
    Retries on connection reset / network errors.
    """
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY)
        try:
            resp = requests.get(
                f"{BASE_URL}/low-level",
                params={"recording_ids": mbid},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return None

            recording = _get_recording_data(data, mbid)
            if recording is None:
                return None

            bpm = _get_nested(recording, "rhythm", "bpm")
            key_key = _get_nested(recording, "tonal", "key_key")
            key_scale = _get_nested(recording, "tonal", "key_scale")
            loudness = _get_nested(recording, "lowlevel", "average_loudness")
            if loudness is None:
                loudness = _get_nested(recording, "metadata", "audio_properties", "replay_gain")
            duration = _get_nested(recording, "metadata", "audio_properties", "length")
            time_sig = _get_nested(recording, "rhythm", "beats_count")
            if time_sig is None:
                time_sig = _get_nested(recording, "rhythm", "time_signature")

            key_str = None
            if key_key:
                scale = (key_scale or "major").lower()
                key_str = f"{key_key} {scale}"

            return {
                "mbid": mbid,
                "tempo": float(bpm) if bpm is not None else None,
                "key": key_str,
                "mode": (key_scale or "major").lower() if key_scale else None,
                "time_signature": int(time_sig) if time_sig is not None else None,
                "loudness": float(loudness) if loudness is not None else None,
                "duration": float(duration) if duration is not None else None,
                "tonal": _get_nested(recording, "tonal"),
                "rhythm": _get_nested(recording, "rhythm"),
                "lowlevel": _get_nested(recording, "lowlevel"),
            }

        except requests.RequestException as e:
            err_str = str(e).lower()
            if ("connection reset" in err_str or "errno 54" in err_str) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF * (2**attempt)
                logger.warning("AcousticBrainz low-level connection error for %s, retrying in %.1fs (attempt %d/%d)", mbid, wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
            else:
                logger.warning("AcousticBrainz low-level request failed for %s: %s", mbid, e)
                return None
        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse AcousticBrainz low-level response for %s: %s", mbid, e)
            return None
    return None


def get_high_level_features(mbid: str) -> Optional[dict]:
    """
    Fetch high-level audio features for a recording (genre, mood, etc.).
    Retries on connection reset / network errors.
    """
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY)
        try:
            resp = requests.get(
                f"{BASE_URL}/high-level",
                params={"recording_ids": mbid, "map_classes": "true"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return None

            recording = _get_recording_data(data, mbid)
            if recording is None:
                return None

            genres = []
            genre_fields = [
                "genre_rosamerica",
                "genre_electronic",
                "genre_dortmund",
                "genre_tzanetakis",
            ]
            for field in genre_fields:
                genre_obj = recording.get(field)
                if isinstance(genre_obj, dict):
                    value = genre_obj.get("value")
                    prob = genre_obj.get("probability", 0)
                    if value and prob and float(prob) > 0.3:
                        genres.append(str(value).lower())

            genres = list(dict.fromkeys(genres))  # deduplicate, preserve order

            return {
                "mbid": mbid,
                "genres": genres,
                "high_level": recording,
            }

        except requests.RequestException as e:
            err_str = str(e).lower()
            if ("connection reset" in err_str or "errno 54" in err_str) and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF * (2**attempt)
                logger.warning("AcousticBrainz high-level connection error for %s, retrying in %.1fs (attempt %d/%d)", mbid, wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
            else:
                logger.warning("AcousticBrainz high-level request failed for %s: %s", mbid, e)
                return None
        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse AcousticBrainz high-level response for %s: %s", mbid, e)
            return None
    return None


def get_all_features(mbid: str) -> Optional[dict]:
    """
    Fetch and merge low-level and high-level features for a recording.

    Args:
        mbid: MusicBrainz recording ID (UUID format)

    Returns:
        Merged dict with tempo, key, mode, loudness, duration, genres, etc.
        or None if no data is available from either endpoint.
    """
    low = get_low_level_features(mbid)
    high = get_high_level_features(mbid)

    if low is None and high is None:
        return None

    result = low.copy() if low else {"mbid": mbid}
    if high:
        result["genres"] = high.get("genres", [])
        result["high_level"] = high.get("high_level", {})

    return result


if __name__ == "__main__":
    result = get_all_features("36bb7edb-5de3-4c52-87b3-80849e703014")
    print(result)