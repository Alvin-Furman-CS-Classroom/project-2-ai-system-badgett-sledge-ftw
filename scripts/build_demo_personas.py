#!/usr/bin/env python3
"""
One-time / maintenance generator for demo persona bundles under data/personas/<slug>/:
  user_profile.json, user_playlists.json, user_ratings.json,
  module4_scorer.json, module4_reranker.json, PERSONA.md

**Normal testing and demos:** use the committed files in data/personas/ as fixed
fixtures (paths in data/personas/README.md). Do not run this script each time.

**Regenerate only when:** you change persona definitions here, or you need new
MBIDs after a KB rebuild — then run with --force.

  python scripts/build_demo_personas.py --force

Requires: data/knowledge_base.json; adds src/ to path for Module 4 training.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KB_PATH = DATA_DIR / "knowledge_base.json"
PERSONAS_ROOT = DATA_DIR / "personas"
SRC = PROJECT_ROOT / "src"


def _load_kb() -> Dict[str, Any]:
    with KB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _pick(
    pool: Sequence[str],
    k: int,
    rng,
    exclude: Optional[set] = None,
) -> List[str]:
    ex = exclude or set()
    shuffled = [m for m in pool if m not in ex]
    rng.shuffle(shuffled)
    return shuffled[:k]


def _mix_playlist(
    by_genre: Dict[str, List[str]],
    parts: List[Tuple[str, int]],
    rng,
) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for genre, count in parts:
        pool = by_genre.get(genre) or []
        picked = _pick(pool, count, rng, exclude=seen)
        for m in picked:
            seen.add(m)
            out.append(m)
    return out


def _profile(
    genres: List[str],
    moods: List[str],
    *,
    danceable: Optional[str] = None,
    voice_instrumental: Optional[str] = None,
    timbre: Optional[str] = None,
    loudness_min: Optional[float] = None,
    loudness_max: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "preferred_genres": genres,
        "preferred_moods": moods,
        "danceable": danceable,
        "voice_instrumental": voice_instrumental,
        "timbre": timbre,
        "loudness_min": loudness_min,
        "loudness_max": loudness_max,
    }


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def _ratings_dict(entries: List[Tuple[str, str]]) -> Dict[str, Any]:
    return {"ratings": [{"mbid": m, "rating": r} for m, r in entries]}


@dataclass(frozen=True)
class PersonaSpec:
    slug: str
    seed: int
    profile: Dict[str, Any]
    playlist_parts: List[Tuple[str, int]]
    # (genre, k) for negative samples — DISLIKE
    negative_genres: List[Tuple[str, int]]
    # (genre, k) for neutral adjunct ratings
    neutral_genres: List[Tuple[str, int]]
    rating_plan: str  # 'diverse' | 'accuracy'


def _build_ratings(
    playlist_mbids: List[str],
    by_genre: Dict[str, List[str]],
    rng,
    plan: str,
    negative: List[Tuple[str, int]],
    neutral: List[Tuple[str, int]],
) -> List[Tuple[str, str]]:
    ratings: List[Tuple[str, str]] = []
    pl_set = set(playlist_mbids)

    if plan == "diverse":
        # Positives: mix REALLY_LIKE, LIKE, NEUTRAL on playlist
        for i, mbid in enumerate(playlist_mbids):
            if i % 5 == 0:
                ratings.append((mbid, "NEUTRAL"))
            elif i % 3 == 0:
                ratings.append((mbid, "REALLY_LIKE"))
            else:
                ratings.append((mbid, "LIKE"))
        for genre, k in neutral:
            for m in _pick(by_genre.get(genre, []), k, rng, exclude=pl_set):
                ratings.append((m, "NEUTRAL"))
        for genre, k in negative:
            for m in _pick(by_genre.get(genre, []), k, rng, exclude=pl_set):
                ratings.append((m, "DISLIKE"))
    else:
        # accuracy: decisive
        for i, mbid in enumerate(playlist_mbids):
            if i % 4 == 0:
                ratings.append((mbid, "LIKE"))
            else:
                ratings.append((mbid, "REALLY_LIKE"))
        for genre, k in neutral:
            for m in _pick(by_genre.get(genre, []), k, rng, exclude=pl_set):
                ratings.append((m, "NEUTRAL"))
        for genre, k in negative:
            for m in _pick(by_genre.get(genre, []), k, rng, exclude=pl_set):
                ratings.append((m, "DISLIKE"))

    # Dedupe by mbid (last wins — prefer keeps positives; iterate negatives last)
    by_m: Dict[str, str] = {}
    for mbid, r in ratings:
        by_m[mbid] = r
    return sorted(by_m.items(), key=lambda x: x[0])


def persona_specs() -> List[PersonaSpec]:
    return [
        PersonaSpec(
            slug="persona_01_college_commuter",
            seed=101,
            profile=_profile(
                ["hip", "rhy", "pop"],
                ["happy", "party", "relaxed"],
                danceable=None,
                voice_instrumental=None,
                timbre=None,
                loudness_min=-12.0,
                loudness_max=-8.0,
            ),
            playlist_parts=[
                ("hip", 12),
                ("rhy", 10),
                ("pop", 8),
            ],
            negative_genres=[("cla", 2), ("jaz", 2)],
            neutral_genres=[("electronic", 3)],
            rating_plan="diverse",
        ),
        PersonaSpec(
            slug="persona_02_classic_rock_dad",
            seed=102,
            profile=_profile(
                ["roc", "blues", "folkcountry"],
                ["happy", "relaxed", "acoustic"],
                danceable=None,
                voice_instrumental=None,
                timbre=None,
                loudness_min=-12.0,
                loudness_max=-8.0,
            ),
            playlist_parts=[
                ("roc", 12),
                ("blues", 8),
                ("folkcountry", 8),
            ],
            negative_genres=[("hip", 3), ("techno", 2)],
            neutral_genres=[("pop", 2)],
            rating_plan="diverse",
        ),
        PersonaSpec(
            slug="persona_03_omnivore_indie",
            seed=103,
            profile=_profile(
                ["alternative", "electronic", "jaz", "folkcountry"],
                ["relaxed", "electronic", "happy"],
                danceable=None,
                voice_instrumental=None,
                timbre=None,
                loudness_min=-12.0,
                loudness_max=-8.0,
            ),
            playlist_parts=[
                ("alternative", 8),
                ("electronic", 8),
                ("jaz", 8),
                ("folkcountry", 8),
            ],
            negative_genres=[("met", 1), ("spe", 1)],
            neutral_genres=[("pop", 4)],
            rating_plan="diverse",
        ),
        PersonaSpec(
            slug="persona_04_trap_maximalist",
            seed=104,
            profile=_profile(
                ["hip", "electronic"],
                ["party", "happy"],
                danceable="danceable",
                voice_instrumental="voice",
                timbre="bright",
                loudness_min=-8.0,
                loudness_max=-5.0,
            ),
            playlist_parts=[
                ("hip", 22),
                ("electronic", 8),
            ],
            negative_genres=[("cla", 4), ("jaz", 4)],
            neutral_genres=[("pop", 2)],
            rating_plan="accuracy",
        ),
        PersonaSpec(
            slug="persona_05_classical_choral",
            seed=105,
            profile=_profile(
                ["cla"],
                ["relaxed", "acoustic"],
                danceable="not_danceable",
                voice_instrumental=None,
                timbre=None,
                loudness_min=-15.0,
                loudness_max=-12.0,
            ),
            playlist_parts=[("cla", 28)],
            negative_genres=[("hip", 5), ("met", 2)],
            neutral_genres=[("pop", 2)],
            rating_plan="accuracy",
        ),
        PersonaSpec(
            slug="persona_06_mainstream_pop",
            seed=106,
            profile=_profile(
                ["pop"],
                ["happy", "party", "relaxed"],
                danceable="danceable",
                voice_instrumental="voice",
                timbre="bright",
                loudness_min=-12.0,
                loudness_max=-8.0,
            ),
            playlist_parts=[("pop", 30)],
            negative_genres=[("cla", 4), ("hip", 4), ("roc", 3)],
            neutral_genres=[("rhy", 2)],
            rating_plan="accuracy",
        ),
    ]


PERSONA_DOCS: Dict[str, str] = {
    "persona_01_college_commuter": """# Persona: College commuter (diversity demo)

## Intent

Represents a listener whose **day splits between high-energy and chill**:
chart-adjacent hip-hop, R&B, and pop crossover tracks. The goal is a **broad
but coherent** taste profile so retrieval—and later Module 5 clustering—can
surface **multiple lanes** (party vs relaxed, rap vs melodic) instead of one
compact cluster.

## How the files encode this

- **`user_profile.json`**: `hip`, `rhy`, and `pop` with moods `happy`, `party`,
  and `relaxed`. Loudness in the **moderate** survey band. Open-ended fields
  (`danceable`, `voice_instrumental`, `timbre` left null) so both upbeat and
  smoother tracks can match.
- **`user_playlists.json`**: Deliberate **split**—more hip-hop, substantial R&B,
  and a pop slice—so positive supervision is visibly multi-genre.
- **`user_ratings.json`**: **Mixed** `LIKE`, `REALLY_LIKE`, and `NEUTRAL` on
  playlist tracks; a few **explicit dislikes** on classical/jazz and some
  **neutral** electronic tracks outside the core blend—signals breadth without
  collapsing onto one feature.
- **`module4_*.json`**: Trained from this persona’s playlist + ratings; weights
  should tilt toward their genres/moods while still reflecting mixed labels.

## Demo tips

Try **two different seed songs** (one “party”, one “chill”) to show how the
same user still gets coherent but varied candidate pools.
""",
    "persona_02_classic_rock_dad": """# Persona: Classic rock / dad-rock (diversity demo)

## Intent

Represents a **Gen X “radio rock”** listener: rock, blues-based tracks, and a
little country/folk-adjacent material—one ecosystem, but **enough genre spread**
that clustering and graph neighbors can differ (anthem rock vs ballads vs
twang).

## How the files encode this

- **`user_profile.json`**: `roc`, `blues`, `folkcountry` with `happy`,
  `relaxed`, `acoustic` moods; moderate loudness; open categorical prefs.
- **`user_playlists.json`**: Weighted toward **rock**, with **blues** and
  **folk/country** representation—not a single-subgenre list.
- **`user_ratings.json`**: Diverse-style mix on the playlist; dislikes on
  hip-hop and techno outliers; a little neutral pop—keeps the model from
  pretending taste is only guitar rock.
- **`module4_*.json`**: Learns feature weights aligned with that multi-genre
  classic-radio palette.

## Demo tips

Good contrast with **hip-hop** or **EDM-heavy** personas; diversity shows up as
rock vs blues vs folk **clusters** in ranked pools.
""",
    "persona_03_omnivore_indie": """# Persona: Omnivore indie (flagship diversity demo)

## Intent

A **deliberately wide** but still curated listener: alternative, electronic,
jazz, and folk/country flavors in one profile. Maximizes **spread in KB
features** so Module 5-style diversification has multiple natural groups.

## How the files encode this

- **`user_profile.json`**: Four **distinct** genre codes plus mixed moods
  (`relaxed`, `electronic`, `happy`).
- **`user_playlists.json`**: Roughly **equal quarters** from four genres—by
  construction, the playlist is multi-modal.
- **`user_ratings.json`**: Mostly positive labels across lanes; light negatives
  on rare/unwanted buckets; extra neutrals on pop—avoids a single-cluster
  collapse.
- **`module4_*.json`**: Should assign positive mass across several genre/mood
  features.

## Demo tips

Best persona to show **“same user, visibly different recommendation clusters”**
after Module 5. Before that, still shows varied top-K under search + ML.
""",
    "persona_04_trap_maximalist": """# Persona: Trap / club rap maximalist (accuracy demo)

## Intent

**Narrow, loud, dance-forward** hip-hop + electronic. Recommendations should
**stay in the lane**—great for showing precision and strong dislikes of
“wrong-world” tracks (e.g. classical/jazz).

## How the files encode this

- **`user_profile.json`**: `hip` + `electronic`, `party`/`happy`, **danceable**,
  **voice**, **bright** timbre, **loud** dB range.
- **`user_playlists.json`**: Dominated by **hip-hop** with an electronic boost.
- **`user_ratings.json`**: **Accuracy-style**—most playlist tracks
  `REALLY_LIKE`/`LIKE`; **hard dislikes** on classical and jazz samples.
- **`module4_*.json`**: Reinforces dance/party/loud feature family for this user.

## Demo tips

Use a **single seed** from the playlist; top results should look like the same
aisle every time.
""",
    "persona_05_classical_choral": """# Persona: Classical + choral (accuracy demo)

## Intent

Older / long-form listener centered on **classical** (`cla`), including
**choral** repertoire. Vocal vs instrumental is **not** fixed so both
orchestral and choral music can score.

## How the files encode this

- **`user_profile.json`**: **Only** `cla` as preferred genre; `relaxed` and
  `acoustic` moods; **not danceable**; **`voice_instrumental` explicitly null**
  so choir/orchestra both match; **quiet** loudness band.
- **`user_playlists.json`**: Long playlist sampled from the classical index.
- **`user_ratings.json`**: Strong positives on playlist; dislikes on hip-hop,
  metal, etc.—sharp boundary for demos.
- **`module4_*.json`**: Should emphasize classical/quiet/acoustic-style features.

## Note

The KB tags **genre**, not “choral” as its own label; null
`voice_instrumental` is what allows **choral and instrumental** classical in
the same persona.
""",
    "persona_06_mainstream_pop": """# Persona: Mainstream pop purist (accuracy demo)

## Intent

**Chart- and radio-style pop** listener: vocal, upbeat, hooks-first. Like the
old metal slot, this is a **narrow-lane accuracy** persona—but the KB has
**thousands** of `pop` tracks, so search and learning behave reliably.

## How the files encode this

- **`user_profile.json`**: **Only** `pop` as preferred genre; moods `happy`,
  `party`, `relaxed`; **danceable**, **voice**, **bright** timbre; **moderate**
  loudness band—roughly “Top 40 energy without the trap-maximalist extreme.”
- **`user_playlists.json`**: Long playlist drawn **entirely** from the `pop`
  genre index for strong positive supervision.
- **`user_ratings.json`**: **Accuracy-style**—mostly `REALLY_LIKE`/`LIKE` on
  playlist tracks; **dislikes** on classical, hip-hop, and rock samples to
  sharpen boundaries vs other demos; a couple **neutral** R&B tracks (often
  overlaps radio pop) so labels are not cartoonishly pure.
- **`module4_*.json`**: Should emphasize `genre:pop` and party/happy-adjacent
  features for this user.

## Demo tips

Contrast with **persona 4** (hip-hop + electronic party) and **persona 1**
(multi-genre commuter): same “mainstream” aisle, different genre centers.
""",
}


def _train_m4(persona_dir: Path) -> None:
    sys.path.insert(0, str(SRC))
    from ml.train_module4 import train_module4_scorer  # noqa: E402

    train_module4_scorer(
        kb_path=str(KB_PATH),
        playlists_path=str(persona_dir / "user_playlists.json"),
        ratings_path=str(persona_dir / "user_ratings.json"),
        artifact_path=str(persona_dir / "module4_scorer.json"),
        reranker_artifact_path=str(persona_dir / "module4_reranker.json"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or refresh demo persona fixtures under data/personas/.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing persona JSON/MD and retrain Module 4 artifacts (default: skip if fixtures exist).",
    )
    args = parser.parse_args()

    specs = persona_specs()
    if not args.force and all((PERSONAS_ROOT / s.slug / "user_profile.json").exists() for s in specs):
        print(
            "Demo persona fixtures already exist under data/personas/.\n"
            "Use those paths for tests and CLI demos; run with --force only to regenerate."
        )
        return

    if not KB_PATH.exists():
        print(f"Missing knowledge base: {KB_PATH}", file=sys.stderr)
        sys.exit(1)

    kb = _load_kb()
    by_genre = kb["indexes"]["by_genre"]
    for spec in specs:
        parts = spec.playlist_parts

        rng = __import__("random").Random(spec.seed)
        playlist = _mix_playlist(by_genre, parts, rng)
        playlist_name = spec.slug
        _save_json(
            PERSONAS_ROOT / spec.slug / "user_playlists.json",
            {"playlists": [{"name": playlist_name, "mbids": playlist}]},
        )
        _save_json(PERSONAS_ROOT / spec.slug / "user_profile.json", spec.profile)

        ratings_list = _build_ratings(
            playlist, by_genre, rng, spec.rating_plan, spec.negative_genres, spec.neutral_genres
        )
        _save_json(
            PERSONAS_ROOT / spec.slug / "user_ratings.json",
            _ratings_dict(ratings_list),
        )

        doc_path = PERSONAS_ROOT / spec.slug / "PERSONA.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(PERSONA_DOCS[spec.slug], encoding="utf-8")

        print(f"Wrote {spec.slug}: {len(playlist)} playlist tracks, {len(ratings_list)} ratings")

    sys.path.insert(0, str(SRC))
    for spec in specs:
        pdir = PERSONAS_ROOT / spec.slug
        print(f"Training Module 4 for {spec.slug}...")
        _train_m4(pdir)

    print("Done.")


if __name__ == "__main__":
    main()
