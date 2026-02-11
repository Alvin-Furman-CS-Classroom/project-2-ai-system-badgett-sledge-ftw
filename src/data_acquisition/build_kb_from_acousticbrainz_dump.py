"""
Build a knowledge base from an AcousticBrainz data dump (folder of folders with JSON files).
Walks the dump, parses low-level and high-level JSON per recording, builds facts and indexes.
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Filename pattern: mbid-0.json or mbid.json (MBID = UUID). Allow leading zeros before UUID.
MBID_FROM_FNAME = re.compile(
    r"(?:[0-9a-f]+)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.I,
)


def _get_nested(data: dict, *keys: str) -> Any:
    for key in keys:
        if data is None or not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def parse_lowlevel_json(data: dict) -> dict:
    """Extract audio_features from AcousticBrainz low-level JSON (same shape as API)."""
    bpm = _get_nested(data, "rhythm", "bpm")
    key_key = _get_nested(data, "tonal", "key_key")
    key_scale = _get_nested(data, "tonal", "key_scale")
    loudness = _get_nested(data, "lowlevel", "average_loudness") or _get_nested(data, "metadata", "audio_properties", "replay_gain")
    duration = _get_nested(data, "metadata", "audio_properties", "length")
    time_sig = _get_nested(data, "rhythm", "beats_count") or _get_nested(data, "rhythm", "time_signature")
    key_str = None
    if key_key:
        scale = (key_scale or "major").lower()
        key_str = f"{key_key} {scale}"
    return {
        "tempo": float(bpm) if bpm is not None else None,
        "key": key_str,
        "mode": (key_scale or "major").lower() if key_scale else None,
        "time_signature": int(time_sig) if time_sig is not None else None,
        "loudness": float(loudness) if loudness is not None else None,
        "duration": float(duration) if duration is not None else None,
    }


def parse_highlevel_json(data: dict) -> List[str]:
    """Extract genre list from AcousticBrainz high-level JSON."""
    genres = []
    for field in ("genre_rosamerica", "genre_electronic", "genre_dortmund", "genre_tzanetakis"):
        genre_obj = data.get(field)
        if isinstance(genre_obj, dict):
            value = genre_obj.get("value")
            prob = genre_obj.get("probability", 0)
            if value and prob and float(prob) > 0.3:
                genres.append(str(value).lower())
    return list(dict.fromkeys(genres))


def parse_metadata_from_dump(root: dict) -> dict:
    """Extract artist, title, album from dump JSON metadata.tags (tags are often lists)."""
    out = {"artist": "", "track": "", "album": ""}
    meta = root.get("metadata", {})
    tags = meta.get("tags", {}) if isinstance(meta, dict) else {}
    if not isinstance(tags, dict):
        return out
    for key, dest in (("artist", "artist"), ("title", "track"), ("album", "album")):
        val = tags.get(key)
        if isinstance(val, list) and val:
            out[dest] = str(val[0]).strip()
        elif isinstance(val, str):
            out[dest] = val.strip()
    return out


def _value_if_confident(obj: dict, min_prob: float = 0.5) -> Optional[str]:
    """Return value if object has value and probability >= min_prob."""
    if not isinstance(obj, dict):
        return None
    val = obj.get("value")
    prob = obj.get("probability", 0)
    try:
        if val is not None and float(prob) >= min_prob:
            return str(val).strip().lower()
    except (TypeError, ValueError):
        pass
    return None


def parse_highlevel_extra(root: dict, high_data: dict) -> dict:
    """
    Extract mood, danceability, voice_instrumental, timbre, and metadata duration/loudness
    from AcousticBrainz high-level JSON for recommendation/similarity.
    """
    out = {
        "danceable": None,
        "voice_instrumental": None,
        "timbre": None,
        "moods": [],
        "duration": None,
        "loudness": None,
    }
    # Duration and loudness from metadata.audio_properties (when no low-level)
    meta = root.get("metadata", {})
    ap = meta.get("audio_properties", {}) if isinstance(meta, dict) else {}
    if isinstance(ap, dict):
        if ap.get("length") is not None:
            try:
                out["duration"] = float(ap["length"])
            except (TypeError, ValueError):
                pass
        if ap.get("replay_gain") is not None:
            try:
                out["loudness"] = float(ap["replay_gain"])
            except (TypeError, ValueError):
                pass
    # Single-value high-level features
    for field, key in (
        ("danceability", "danceable"),
        ("voice_instrumental", "voice_instrumental"),
        ("timbre", "timbre"),
    ):
        obj = high_data.get(field)
        val = _value_if_confident(obj)
        if val:
            out[key] = val
    # Moods: collect positive labels where probability > 0.5
    mood_fields = (
        ("mood_relaxed", "relaxed"),
        ("mood_sad", "sad"),
        ("mood_happy", "happy"),
        ("mood_party", "party"),
        ("mood_acoustic", "acoustic"),
        ("mood_electronic", "electronic"),
    )
    for field, label in mood_fields:
        obj = high_data.get(field)
        val = _value_if_confident(obj)
        if val == label:
            out["moods"].append(label)
    return out


def discover_dump_files(dump_root: Path) -> Dict[str, Dict[str, Path]]:
    """
    Walk dump_root and find all JSON files. Group by MBID.
    Returns: { mbid: { "lowlevel": Path, "highlevel": Path } }
    """
    by_mbid: Dict[str, Dict[str, Path]] = {}
    for jpath in dump_root.rglob("*.json"):
        match = MBID_FROM_FNAME.search(jpath.name)
        if not match:
            continue
        mbid = match.group(1).lower()
        if mbid not in by_mbid:
            by_mbid[mbid] = {}
        # Infer type from path or filename (e.g. lowlevel/... or highlevel/... or .../low_level/...)
        path_lower = str(jpath).lower()
        if "highlevel" in path_lower or "high_level" in path_lower:
            by_mbid[mbid]["highlevel"] = jpath
        else:
            by_mbid[mbid]["lowlevel"] = jpath
    return by_mbid


def load_song_from_dump(mbid: str, paths: Dict[str, Path]) -> Optional[dict]:
    """Load one recording's low-level and high-level JSON into a single song record."""
    audio_features = {}
    genres = []
    if "lowlevel" in paths:
        try:
            with open(paths["lowlevel"], encoding="utf-8") as f:
                low = json.load(f)
            audio_features = parse_lowlevel_json(low)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Skip lowlevel for %s: %s", mbid, e)
    metadata_song = {}
    highlevel_extra = {}
    if "highlevel" in paths:
        try:
            with open(paths["highlevel"], encoding="utf-8") as f:
                high = json.load(f)
            high_data = high.get("highlevel", high)
            genres = parse_highlevel_json(high_data)
            metadata_song = parse_metadata_from_dump(high)
            highlevel_extra = parse_highlevel_extra(high, high_data)
            # Fill duration/loudness from metadata when no low-level
            if highlevel_extra.get("duration") is not None and audio_features.get("duration") is None:
                audio_features["duration"] = highlevel_extra["duration"]
            if highlevel_extra.get("loudness") is not None and audio_features.get("loudness") is None:
                audio_features["loudness"] = highlevel_extra["loudness"]
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Skip highlevel for %s: %s", mbid, e)
    if not audio_features and not genres:
        return None
    return {
        "mbid": mbid,
        "artist": metadata_song.get("artist", ""),
        "track": metadata_song.get("track", ""),
        "album": metadata_song.get("album", ""),
        "audio_features": audio_features,
        "genres": genres,
        "danceable": highlevel_extra.get("danceable"),
        "voice_instrumental": highlevel_extra.get("voice_instrumental"),
        "timbre": highlevel_extra.get("timbre"),
        "moods": highlevel_extra.get("moods", []),
    }


def tempo_bucket(tempo: Optional[float]) -> Optional[str]:
    """Bucket tempo for index (e.g. 120 -> '120-130')."""
    if tempo is None:
        return None
    t = int(tempo)
    base = (t // 10) * 10
    return f"{base}-{base + 10}"


def build_knowledge_base(songs: List[dict]) -> dict:
    """Build KB with songs, facts, and indexes (song_id = mbid)."""
    kb_songs = {}
    facts = {
        "has_tempo": {},
        "has_key": {},
        "has_mode": {},
        "has_loudness": {},
        "has_duration": {},
        "has_genre": {},
        "has_danceable": {},
        "has_voice_instrumental": {},
        "has_timbre": {},
        "has_mood": {},
    }
    indexes = {
        "by_tempo_range": {},
        "by_genre": {},
        "by_danceable": {},
        "by_voice_instrumental": {},
        "by_timbre": {},
        "by_mood": {},
    }
    for song in songs:
        mbid = song.get("mbid")
        if not mbid:
            continue
        sid = mbid
        kb_songs[sid] = {
            "mbid": mbid,
            "artist": song.get("artist", ""),
            "track": song.get("track", ""),
            "album": song.get("album", ""),
        }
        af = song.get("audio_features", {})
        if af.get("tempo") is not None:
            facts["has_tempo"][sid] = af["tempo"]
            bucket = tempo_bucket(af["tempo"])
            if bucket:
                indexes["by_tempo_range"].setdefault(bucket, []).append(sid)
        if af.get("key"):
            facts["has_key"][sid] = af["key"]
        if af.get("mode"):
            facts["has_mode"][sid] = af["mode"]
        if af.get("loudness") is not None:
            facts["has_loudness"][sid] = af["loudness"]
        if af.get("duration") is not None:
            facts["has_duration"][sid] = af["duration"]
        for g in song.get("genres", []):
            facts["has_genre"].setdefault(sid, []).append(g)
            gn = g.lower().strip()
            if gn:
                indexes["by_genre"].setdefault(gn, []).append(sid)
        # High-level: danceability, voice_instrumental, timbre, moods
        danceable = song.get("danceable")
        if danceable:
            facts["has_danceable"][sid] = danceable
            indexes["by_danceable"].setdefault(danceable, []).append(sid)
        vi = song.get("voice_instrumental")
        if vi:
            facts["has_voice_instrumental"][sid] = vi
            indexes["by_voice_instrumental"].setdefault(vi, []).append(sid)
        timbre = song.get("timbre")
        if timbre:
            facts["has_timbre"][sid] = timbre
            indexes["by_timbre"].setdefault(timbre, []).append(sid)
        for mood in song.get("moods", []):
            facts["has_mood"].setdefault(sid, []).append(mood)
            mn = mood.lower().strip()
            if mn:
                indexes["by_mood"].setdefault(mn, []).append(sid)
    for sid in list(facts["has_genre"].keys()):
        facts["has_genre"][sid] = list(dict.fromkeys(facts["has_genre"][sid]))
    for sid in list(facts["has_mood"].keys()):
        facts["has_mood"][sid] = list(dict.fromkeys(facts["has_mood"][sid]))
    return {"songs": kb_songs, "facts": facts, "indexes": indexes}


def run(dump_root: Path, output_path: Path, limit: Optional[int] = None) -> dict:
    """Discover dump files, load songs, build KB, save."""
    logger.info("Scanning dump at %s", dump_root)
    by_mbid = discover_dump_files(dump_root)
    logger.info("Found %d recordings", len(by_mbid))
    mbids = list(by_mbid.keys())
    if limit:
        mbids = mbids[:limit]
    songs = []
    for i, mbid in enumerate(mbids):
        if (i + 1) % 5000 == 0:
            logger.info("Processed %d / %d", i + 1, len(mbids))
        rec = load_song_from_dump(mbid, by_mbid[mbid])
        if rec:
            songs.append(rec)
    logger.info("Loaded %d songs with data", len(songs))
    kb = build_knowledge_base(songs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2)
    logger.info("Saved knowledge base to %s (%d songs)", output_path, len(kb["songs"]))
    return {"songs": len(kb["songs"]), "output_path": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build knowledge base from AcousticBrainz data dump")
    parser.add_argument("dump_root", type=Path, help="Root folder of the AcousticBrainz dump")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output knowledge_base.json path (default: data/knowledge_base.json)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only first N recordings (for testing)")
    args = parser.parse_args()
    out = args.output or (args.dump_root.parent.parent / "data" / "knowledge_base.json")
    if not out.is_absolute():
        out = (Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base.json") if args.output is None else args.output
    run(args.dump_root, out, limit=args.limit)


if __name__ == "__main__":
    main()
