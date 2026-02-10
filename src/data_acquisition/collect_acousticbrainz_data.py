"""
Collect song data from MusicBrainz and AcousticBrainz APIs.
Loads song_list_flat.json, resolves MBIDs, fetches features and credits, saves to raw_songs.json.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from musicbrainz_client import search_recording, get_recording_details
from acousticbrainz_client import get_all_features

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

SONG_LIST_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "song_list_flat.json"
RAW_SONGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw_songs.json"


def load_song_list(path: Path, limit: Optional[int] = None) -> list:
    """Load song list from JSON."""
    with open(path, encoding="utf-8") as f:
        songs = json.load(f)
    if limit:
        songs = songs[:limit]
    return songs


def build_audio_features(ab_data: Optional[dict]) -> dict:
    """Extract audio_features dict from AcousticBrainz response."""
    if not ab_data:
        return {}
    return {
        "tempo": ab_data.get("tempo"),
        "key": ab_data.get("key"),
        "mode": ab_data.get("mode"),
        "time_signature": ab_data.get("time_signature"),
        "loudness": ab_data.get("loudness"),
        "duration": ab_data.get("duration"),
    }


def build_credits(mb_data: Optional[dict]) -> dict:
    """Extract credits dict from MusicBrainz response."""
    if not mb_data:
        return {
            "main_artist": "",
            "featured_artists": [],
            "writers": [],
            "producers": [],
        }
    return {
        "main_artist": mb_data.get("artist", ""),
        "featured_artists": mb_data.get("featured_artists", []),
        "writers": mb_data.get("writers", []),
        "producers": mb_data.get("producers", []),
    }


def collect_status(mbid: bool, ab_data: Optional[dict], mb_data: Optional[dict]) -> str:
    """Determine collection_status: complete, partial, or failed."""
    if not mbid:
        return "failed"
    if ab_data and mb_data:
        return "complete"
    if ab_data or mb_data:
        return "partial"
    return "partial"  # MBID found but neither API returned data


def collect_for_song(song: dict) -> dict:
    """Collect MusicBrainz + AcousticBrainz data for one song."""
    artist = song.get("artist", "")
    track = song.get("track", "")

    mbid = search_recording(artist, track)
    if not mbid:
        return {
            **song,
            "mbid": None,
            "audio_features": {},
            "genres": [],
            "credits": {"main_artist": "", "featured_artists": [], "writers": [], "producers": []},
            "language": None,
            "collection_status": "failed",
        }

    ab_data = get_all_features(mbid)
    mb_data = get_recording_details(mbid)

    audio_features = build_audio_features(ab_data)
    genres = ab_data.get("genres", []) if ab_data else []
    credits = build_credits(mb_data)
    language = mb_data.get("language") if mb_data else None

    status = collect_status(True, ab_data, mb_data)

    return {
        **song,
        "mbid": mbid,
        "audio_features": audio_features,
        "genres": genres,
        "credits": credits,
        "language": language,
        "collection_status": status,
    }


def run(song_list_path: Path, output_path: Path, limit: Optional[int] = None) -> dict:
    """Run the full collection pipeline."""
    logger.info("Loading song list from %s", song_list_path)
    songs = load_song_list(song_list_path, limit=limit)
    logger.info("Processing %d songs", len(songs))

    results = []
    failed = 0
    partial = 0

    for i, song in enumerate(songs):
        if (i + 1) % 10 == 0:
            logger.info("Progress: %d / %d", i + 1, len(songs))
        row = collect_for_song(song)
        results.append(row)
        if row["collection_status"] == "failed":
            failed += 1
        elif row["collection_status"] == "partial":
            partial += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    complete = len(results) - failed - partial
    report = {
        "total": len(results),
        "complete": complete,
        "partial": partial,
        "failed": failed,
        "output_path": str(output_path),
    }
    logger.info(
        "Collection complete: %d total, %d complete, %d partial, %d failed. Saved to %s",
        report["total"],
        report["complete"],
        report["partial"],
        report["failed"],
        output_path,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect MusicBrainz + AcousticBrainz data")
    parser.add_argument(
        "--song-list",
        type=Path,
        default=SONG_LIST_PATH,
        help="Path to song_list_flat.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RAW_SONGS_PATH,
        help="Path for raw_songs.json output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of songs (for testing)",
    )
    args = parser.parse_args()
    run(args.song_list, args.output, limit=args.limit)


if __name__ == "__main__":
    main()
