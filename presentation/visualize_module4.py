#!/usr/bin/env python3
"""
Module 4 visualizations (no training required):

1. Feature importance — horizontal bar chart from data/module4_scorer.json weights
   (top positive vs top negative features; bias optional).

2. Playlist taste fingerprint — genres/moods from playlist MBIDs (reads
   data/user_playlists.json, or falls back to data/playlists/user_playlist_v1.json);
   bar + pie charts.

Run from project root:
  PYTHONPATH=src python3 presentation/visualize_module4.py

Outputs (default): presentation/figures/module4/
  - feature_importance.png
  - playlist_genres_bar.png / playlist_genres_pie.png
  - playlist_moods_bar.png / playlist_moods_pie.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

# Project root = parent of presentation/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Headless-safe matplotlib (no GUI); writable cache in repo for sandbox/CI
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".matplotlib_cache"))
os.environ.setdefault("MPLBACKEND", "Agg")

SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from knowledge_base_wrapper import KnowledgeBase


def plot_feature_importance(
    weights: dict[str, float],
    out_path: Path,
    *,
    top_n: int = 15,
    include_bias: bool = False,
) -> None:
    """Horizontal bar chart: top negative and top positive features (by value)."""
    items = [(k, float(v)) for k, v in weights.items() if include_bias or k != "bias"]
    if not items:
        print("No weights to plot.")
        return
    items.sort(key=lambda x: x[1])
    # Lowest values = most negative; highest = most positive
    neg = items[:top_n]
    pos = items[-top_n:][::-1]  # largest first (top of chart)

    fig_h = max(6, 0.38 * max(len(neg), len(pos), 1))
    fig, (ax_neg, ax_pos) = plt.subplots(1, 2, figsize=(12, fig_h))

    labels_n = [k for k, _ in neg]
    vals_n = [v for _, v in neg]
    y = range(len(labels_n))
    ax_neg.barh(y, vals_n, color="#c44e52")
    ax_neg.set_yticks(list(y))
    ax_neg.set_yticklabels(labels_n, fontsize=8)
    ax_neg.set_xlabel("Weight")
    ax_neg.set_title(f"Most negative (lowest {len(neg)} weights)")
    ax_neg.axvline(0, color="gray", linewidth=0.5)
    ax_neg.invert_yaxis()

    labels_p = [k for k, _ in pos]
    vals_p = [v for _, v in pos]
    yp = range(len(labels_p))
    ax_pos.barh(yp, vals_p, color="#4c72b0")
    ax_pos.set_yticks(list(yp))
    ax_pos.set_yticklabels(labels_p, fontsize=8)
    ax_pos.set_xlabel("Weight")
    ax_pos.set_title(f"Most positive (highest {len(pos)} weights)")
    ax_pos.axvline(0, color="gray", linewidth=0.5)
    ax_pos.invert_yaxis()

    fig.suptitle("Module 4 feature importance (learned weights)", fontsize=12)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def _normalize_playlists_blob(raw: dict) -> dict:
    """Ensure {\"playlists\": [{\"name\", \"mbids\"}, ...]}."""
    if isinstance(raw.get("playlists"), list):
        return raw
    if isinstance(raw.get("mbids"), list):
        name = raw.get("name", "playlist")
        return {"playlists": [{"name": str(name), "mbids": raw["mbids"]}]}
    return {"playlists": []}


def _playlist_blob_has_mbids(blob: dict) -> bool:
    for pl in blob.get("playlists", []):
        if not isinstance(pl, dict):
            continue
        mbs = pl.get("mbids", [])
        if isinstance(mbs, list) and any(isinstance(x, str) and x for x in mbs):
            return True
    return False


def resolve_playlist_blob(project_root: Path, preferred: Path) -> tuple[dict | None, str]:
    """
    Prefer ``preferred`` (usually data/user_playlists.json).
    If missing or no MBIDs, fall back to data/playlists/user_playlist_v1.json
    (written by create_playlist.py).
    """
    def _label(p: Path) -> str:
        try:
            return str(p.relative_to(project_root))
        except ValueError:
            return str(p)

    candidates: list[tuple[Path, str]] = []
    if preferred.exists():
        candidates.append((preferred, _label(preferred)))
    fallback = project_root / "data" / "playlists" / "user_playlist_v1.json"
    if fallback.exists() and fallback.resolve() not in {p.resolve() for p, _ in candidates}:
        candidates.append((fallback, _label(fallback)))

    for path, label in candidates:
        try:
            with path.open(encoding="utf-8") as f:
                blob = _normalize_playlists_blob(json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: could not read {path}: {e}")
            continue
        if _playlist_blob_has_mbids(blob):
            return blob, label
    return None, ""


def _collect_genre_mood_counts(kb: KnowledgeBase, blob: dict) -> tuple[Counter, Counter]:
    genre_counts: Counter = Counter()
    mood_counts: Counter = Counter()
    seen_mbids: set[str] = set()
    for pl in blob.get("playlists", []):
        if not isinstance(pl, dict):
            continue
        for mbid in pl.get("mbids", []):
            if not isinstance(mbid, str) or mbid in seen_mbids:
                continue
            seen_mbids.add(mbid)
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
    return genre_counts, mood_counts


def plot_counter_bars_and_pie(
    counter: Counter,
    title_prefix: str,
    out_bar: Path,
    out_pie: Path,
    *,
    top_k: int = 12,
) -> None:
    if not counter:
        print(f"No data for {title_prefix}; skipping charts.")
        return
    # Bar: top_k by count
    most = counter.most_common(top_k)
    labels = [k for k, _ in most]
    vals = [v for _, v in most]
    rest = sum(counter.values()) - sum(vals)
    if rest > 0 and len(most) >= top_k:
        labels.append("(other)")
        vals.append(rest)

    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(labels))))
    ax.barh(range(len(labels)), vals, color="#55a868")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Count (songs)")
    ax.set_title(f"{title_prefix} — top counts in playlist(s)")
    ax.invert_yaxis()
    fig.tight_layout()
    out_bar.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_bar, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_bar}")

    # Pie: same top_k, merge rest
    pie_labels = [k for k, _ in most]
    pie_vals = [v for _, v in most]
    if rest > 0 and len(most) >= top_k:
        pie_labels.append("other")
        pie_vals.append(rest)
    fig2, ax2 = plt.subplots(figsize=(8, 8))
    ax2.pie(pie_vals, labels=pie_labels, autopct="%1.1f%%", textprops={"fontsize": 8})
    ax2.set_title(f"{title_prefix} — distribution")
    fig2.tight_layout()
    fig2.savefig(out_pie, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Wrote {out_pie}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Module 4 visualizations")
    parser.add_argument(
        "--scorer",
        default="data/module4_scorer.json",
        help="Path to Module 4 scorer artifact JSON",
    )
    parser.add_argument(
        "--playlists",
        default="data/user_playlists.json",
        help="Path to user_playlists.json (if missing/empty, tries data/playlists/user_playlist_v1.json)",
    )
    parser.add_argument(
        "--kb",
        default="data/knowledge_base.json",
        help="Path to knowledge_base.json",
    )
    parser.add_argument(
        "--out-dir",
        default="presentation/figures/module4",
        help="Output directory for PNG files",
    )
    parser.add_argument("--top-n", type=int, default=15, help="Top N positive/negative features")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.out_dir
    scorer_path = PROJECT_ROOT / args.scorer
    playlists_path = PROJECT_ROOT / args.playlists
    kb_path = PROJECT_ROOT / args.kb

    # 1) Feature importance
    if scorer_path.exists():
        with scorer_path.open(encoding="utf-8") as f:
            artifact = json.load(f)
        weights = artifact.get("weights", {})
        if isinstance(weights, dict):
            plot_feature_importance(
                {str(k): float(v) for k, v in weights.items()},
                out_dir / "feature_importance.png",
                top_n=args.top_n,
            )
    else:
        print(f"Skip feature plot: not found {scorer_path}")

    # 2) Playlist fingerprint
    pl_blob, pl_source = resolve_playlist_blob(PROJECT_ROOT, playlists_path)
    if pl_blob is not None:
        print(f"Playlist data source: {pl_source}")
        kb = KnowledgeBase(str(kb_path))
        genres, moods = _collect_genre_mood_counts(kb, pl_blob)
        plot_counter_bars_and_pie(
            genres,
            "Genres (playlist songs)",
            out_dir / "playlist_genres_bar.png",
            out_dir / "playlist_genres_pie.png",
        )
        plot_counter_bars_and_pie(
            moods,
            "Moods (playlist songs)",
            out_dir / "playlist_moods_bar.png",
            out_dir / "playlist_moods_pie.png",
        )
    else:
        print(
            "Skip playlist plots: no playlist MBIDs found. "
            "Add data/user_playlists.json or run src/create_playlist.py "
            "(writes data/playlists/user_playlist_v1.json and can update user_playlists.json)."
        )


if __name__ == "__main__":
    main()
