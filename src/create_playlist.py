from knowledge_base_wrapper import KnowledgeBase

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def print_candidates(kb, candidates, limit=10):
    for i, mbid in enumerate(candidates[:limit], 1):
        song = kb.get_song(mbid) or {}
        # Some KB entries have empty strings for tags; treat "" as missing.
        artist = (song.get("artist") or "Unknown").strip()
        track = (song.get("track") or "Unknown").strip()
        print(f"[{i}] {artist} - {track} ({mbid})")


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_profile_shape(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ensure dict has the same keys as PreferenceProfile JSON.
    (We keep this local to avoid import issues when running as a script.)
    """
    base = {
        "preferred_genres": [],
        "preferred_moods": [],
        "danceable": None,
        "voice_instrumental": None,
        "timbre": None,
        "loudness_min": None,
        "loudness_max": None,
    }
    if not data:
        return base
    out = dict(base)
    out.update({k: data.get(k, base[k]) for k in base.keys()})
    # Normalize list fields
    for k in ("preferred_genres", "preferred_moods"):
        v = out.get(k)
        if v is None:
            out[k] = []
        elif not isinstance(v, list):
            out[k] = [v]
    return out


def _top_n(counter: Counter, n: int) -> List[str]:
    return [k for k, _ in counter.most_common(n)]


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 == 1 else float((s[mid - 1] + s[mid]) / 2)


def derive_profile_from_playlist(
    kb: KnowledgeBase,
    playlist_mbids: List[str],
    *,
    top_genres: int = 5,
    top_moods: int = 5,
) -> Dict[str, Any]:
    """
    Convert a playlist (MBID list) into a PreferenceProfile-shaped dict.

    - Genres/moods: top-N by frequency
    - Categorical facts: majority vote
    - Loudness: median +/- 2.0 dB (simple, robust band)
    """
    genre_counts: Counter = Counter()
    mood_counts: Counter = Counter()
    danceable_counts: Counter = Counter()
    vi_counts: Counter = Counter()
    timbre_counts: Counter = Counter()
    loudness_values: List[float] = []

    for mbid in playlist_mbids:
        genres = kb.get_fact("has_genre", mbid)
        if genres:
            for g in (genres if isinstance(genres, list) else [genres]):
                if g:
                    genre_counts[str(g).strip().lower()] += 1

        moods = kb.get_fact("has_mood", mbid)
        if moods:
            for m in (moods if isinstance(moods, list) else [moods]):
                if m:
                    mood_counts[str(m).strip().lower()] += 1

        d = kb.get_fact("has_danceable", mbid)
        if d:
            danceable_counts[str(d).strip().lower()] += 1

        vi = kb.get_fact("has_voice_instrumental", mbid)
        if vi:
            vi_counts[str(vi).strip().lower()] += 1

        t = kb.get_fact("has_timbre", mbid)
        if t:
            timbre_counts[str(t).strip().lower()] += 1

        loud = kb.get_fact("has_loudness", mbid)
        if loud is not None:
            try:
                loudness_values.append(float(loud))
            except (TypeError, ValueError):
                pass

    derived: Dict[str, Any] = {
        "preferred_genres": _top_n(genre_counts, top_genres),
        "preferred_moods": _top_n(mood_counts, top_moods),
        "danceable": _top_n(danceable_counts, 1)[0] if danceable_counts else None,
        "voice_instrumental": _top_n(vi_counts, 1)[0] if vi_counts else None,
        "timbre": _top_n(timbre_counts, 1)[0] if timbre_counts else None,
        "loudness_min": None,
        "loudness_max": None,
    }

    med = _median(loudness_values)
    if med is not None:
        derived["loudness_min"] = med - 2.0
        derived["loudness_max"] = med + 2.0

    return derived


def merge_profile(existing: Dict[str, Any], derived: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge strategy:
    - Keep explicit existing single-choice fields if set; otherwise fill from derived.
    - For genres/moods: union, preserving existing order first.
    - For loudness: keep existing if both bounds set; else fill from derived if available.
    """
    ex = _ensure_profile_shape(existing)
    out = dict(ex)

    # Lists: keep existing first, then add derived uniques
    for key in ("preferred_genres", "preferred_moods"):
        seen = set()
        merged: List[str] = []
        for v in (ex.get(key) or []) + (derived.get(key) or []):
            if not v:
                continue
            v2 = str(v).strip()
            if not v2:
                continue
            k = v2.lower()
            if k in seen:
                continue
            seen.add(k)
            merged.append(v2)
        out[key] = merged

    # Single-choice fields
    for key in ("danceable", "voice_instrumental", "timbre"):
        if out.get(key) in (None, "", "any"):
            out[key] = derived.get(key) or None

    # Loudness range
    if out.get("loudness_min") is None or out.get("loudness_max") is None:
        out["loudness_min"] = derived.get("loudness_min")
        out["loudness_max"] = derived.get("loudness_max")

    return out


def save_playlist(
    playlist_mbids: List[str],
    *,
    filepath: str = "data/playlists/user_playlist_v1.json",
    name: str = "user_playlist_v1",
) -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"name": name, "mbids": playlist_mbids}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def upsert_user_playlists_file(
    playlist_mbids: List[str],
    *,
    filepath: str = "data/user_playlists.json",
    name: str = "user_playlist_v1",
) -> Path:
    """
    Write/update the Module 4 training input file `data/user_playlists.json`.

    Schema expected by `ml.train_module4`:
      { "playlists": [ { "name": str, "mbids": [str, ...] }, ... ] }
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_json_if_exists(path) or {}
    playlists = existing.get("playlists")
    if not isinstance(playlists, list):
        playlists = []

    # Replace playlist of same name if present; otherwise append.
    new_entry = {"name": name, "mbids": playlist_mbids}
    replaced = False
    for i, pl in enumerate(playlists):
        if isinstance(pl, dict) and str(pl.get("name", "")).strip() == name:
            playlists[i] = new_entry
            replaced = True
            break
    if not replaced:
        playlists.append(new_entry)

    payload = {"playlists": playlists}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def save_user_profile(profile_dict: Dict[str, Any], *, filepath: str = "data/user_profile.json") -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_ensure_profile_shape(profile_dict), f, indent=2)
    return path


def interactive_playlist_picker(kb):
    playlist_mbids = []

    print("Build playlist (press Enter on track to finish)\n")
    while True:
        track = input("Track name: ").strip()
        if not track:
            break
        artist = input("Artist (optional): ").strip() or None

        candidates = kb.find_songs_by_name(track, artist)
        if not candidates:
            print("No matches found.\n")
            continue

        # Rank candidates so exact matches appear first.
        track_q = track.strip().lower()
        artist_q = (artist or "").strip().lower()

        def _rank_candidate(mbid: str) -> tuple[int, int, str, str, str]:
            song = kb.get_song(mbid) or {}
            t = (song.get("track") or "").strip().lower()
            a = (song.get("artist") or "").strip().lower()

            exact_track = (t == track_q)
            exact_artist = (artist_q != "" and a == artist_q)
            partial_track = (track_q in t or t in track_q)
            partial_artist = (artist_q == "" or artist_q in a or a in artist_q)

            # Smaller bucket = better candidate.
            if exact_track and (artist_q == "" or exact_artist):
                bucket = 0
            elif exact_track:
                bucket = 1
            elif partial_track and partial_artist:
                bucket = 2
            else:
                bucket = 3

            # Prefer candidates with known tags (non-empty artist/track) over unknown-tag items.
            has_known_tags = bool(a) and bool(t)
            unknown_penalty = 0 if has_known_tags else 1

            return (bucket, unknown_penalty, a, t, mbid)

        candidates.sort(key=_rank_candidate)
        print_candidates(kb, candidates, limit=10)

        while True:
            choice = input("Pick number (or Enter to cancel this song): ").strip()
            if not choice:
                print("Skipped.\n")
                break
            try:
                idx = int(choice)
            except ValueError:
                print("Enter a number.")
                continue

            if 1 <= idx <= min(10, len(candidates)):
                mbid = candidates[idx - 1]
                if mbid not in playlist_mbids:
                    playlist_mbids.append(mbid)
                    song = kb.get_song(mbid) or {}
                    artist_tag = (song.get("artist") or "Unknown").strip()
                    track_tag = (song.get("track") or "Unknown").strip()
                    print(f"Added: {artist_tag} - {track_tag}\n")
                else:
                    print("Already in playlist.\n")
                break
            else:
                print("Out of range.")

    return playlist_mbids


def _persist_playlist_outputs(kb: KnowledgeBase, playlist: List[str]) -> None:
    """
    Save playlist artifacts and merge/update user profile from playlist features.
    """
    playlist_path = save_playlist(playlist)
    print(f"Playlist saved to: {playlist_path}")
    user_playlists_path = upsert_user_playlists_file(playlist, name="user_playlist_v1")
    print(f"Module 4 playlists file updated: {user_playlists_path}")

    derived = derive_profile_from_playlist(kb, playlist)
    existing_profile = _load_json_if_exists(Path("data/user_profile.json"))
    merged_profile = merge_profile(existing_profile or {}, derived)
    profile_path = save_user_profile(merged_profile)
    print(f"Updated profile saved to: {profile_path}")


def main() -> None:
    kb = KnowledgeBase("data/knowledge_base.json")
    playlist = interactive_playlist_picker(kb)
    print(f"Final playlist size: {len(playlist)}")

    # Recommended flow (Module 4): save playlist and update/merge user profile from it.
    _persist_playlist_outputs(kb, playlist)


if __name__ == "__main__":
    main()