#!/usr/bin/env python3
"""
Write data/playlists/persona_*_diversified_topN.json for each persona union file.

Reads mbids_diversified_round_robin from presentation/figures/module5/persona_*_union_query_pool_mbids.json
and takes the first N MBIDs (round-robin diversified order).

Run from project root:
  PYTHONPATH=src python3 scripts/export_persona_diversified_topn.py
  PYTHONPATH=src python3 scripts/export_persona_diversified_topn.py --top-n 100
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from knowledge_base_wrapper import KnowledgeBase


def _song_row(kb: KnowledgeBase, mbid: str) -> dict[str, str]:
    song = kb.get_song(mbid) or {}
    artist = str(song.get("artist") or "Unknown").strip()
    track = str(song.get("track") or "Unknown").strip()
    return {"mbid": mbid, "artist": artist, "track": track, "label": f"{artist} — {track}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument(
        "--figures-dir",
        default="presentation/figures/module5",
        help="Where persona_*_union_query_pool_mbids.json live",
    )
    parser.add_argument("--out-dir", default="data/playlists")
    parser.add_argument("--kb", default="data/knowledge_base.json")
    args = parser.parse_args()

    fig = PROJECT_ROOT / args.figures_dir
    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, int(args.top_n))
    kb = KnowledgeBase(str(PROJECT_ROOT / args.kb))

    for path in sorted(fig.glob("persona_*_union_query_pool_mbids.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        div = data.get("mbids_diversified_round_robin")
        if not isinstance(div, list) or not div:
            print(f"SKIP (no mbids_diversified_round_robin): {path}")
            continue
        slug = path.name.replace("_union_query_pool_mbids.json", "")
        slice_mbids = [str(x) for x in div[:n] if x]
        tracks = [_song_row(kb, m) for m in slice_mbids]
        out_path = out_dir / f"{slug}_diversified_top{n}.json"
        payload = {
            "name": f"{slug} diversified top {n}",
            "source": str(path.relative_to(PROJECT_ROOT)),
            "mbids": slice_mbids,
            "tracks": tracks,
        }
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"Wrote {out_path.relative_to(PROJECT_ROOT)} ({len(slice_mbids)} tracks)")


if __name__ == "__main__":
    main()
