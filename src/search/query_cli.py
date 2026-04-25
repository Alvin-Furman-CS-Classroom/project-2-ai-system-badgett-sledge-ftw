#!/usr/bin/env python3
"""
Module 3 Query CLI

Lets a user input a song (track name and optional artist), resolves it to an MBID
using `KnowledgeBase`, then runs Module 3 search (`find_similar`) using the
Module 2 preference scorer (built from `data/user_profile.json`, optionally
refined using `data/user_ratings.json`).

Example:
  python3 src/search/query_cli.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add src/ to the path so we can import project modules when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base_wrapper import KnowledgeBase
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.ratings import UserRatings, refine_weights_from_ratings
from preferences.survey import PreferenceProfile
from search.pipeline import SearchResult, find_similar, rank_candidates_from_path_costs
from search.beam import beam_topk
from ml import build_scorer_with_optional_ml
from ml.artifacts import load_reranker_artifact
from ml.reranker import rerank_results_with_artifact
from clustering.kmeans import KMeansConfig
from clustering.organize import cluster_and_organize


def _load_profile(profile_path: str) -> PreferenceProfile:
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return PreferenceProfile(**data)


def _load_playlist_seed_mbids(playlists_path: str, seed_count: int) -> List[str]:
    """
    Load up to ``seed_count`` MBIDs from a user_playlists.json-style file.
    """
    if seed_count <= 0:
        return []

    try:
        with open(playlists_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        return []

    out: List[str] = []
    seen = set()
    for playlist in payload.get("playlists", []):
        mbids = playlist.get("mbids", [])
        if not isinstance(mbids, list):
            continue
        for mbid in mbids:
            if not isinstance(mbid, str):
                continue
            if mbid in seen:
                continue
            seen.add(mbid)
            out.append(mbid)
            if len(out) >= seed_count:
                return out
    return out


def _resolve_query_from_mbid(kb: KnowledgeBase, mbid: str) -> Optional[tuple[str, str, str]]:
    song = kb.get_song(mbid)
    if not song:
        print(f"MBID not found in knowledge base: {mbid}")
        return None
    artist = (song.get("artist") or "Unknown").strip()
    track = (song.get("track") or "Unknown").strip()
    return mbid, artist, track


def _apply_persona_overrides(args: argparse.Namespace) -> argparse.Namespace:
    """
    If --persona-dir is provided, set profile/ratings/artifact paths to that
    folder and enable ratings + ML toggles for low-friction demos.
    """
    if not args.persona_dir:
        return args

    pdir = Path(args.persona_dir)
    if not pdir.exists() or not pdir.is_dir():
        raise FileNotFoundError(f"Persona directory not found: {pdir}")

    args.profile = str(pdir / "user_profile.json")
    args.ratings = str(pdir / "user_ratings.json")
    args.playlists = str(pdir / "user_playlists.json")
    args.ml_scorer_artifact = str(pdir / "module4_scorer.json")
    args.ml_reranker_artifact = str(pdir / "module4_reranker.json")
    args.use_ratings = True
    args.use_ml_scorer = True
    args.use_ml_reranker = True
    return args


def _print_results_for_query(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    query_tuple: tuple[str, str, str],
    args: argparse.Namespace,
) -> List[SearchResult]:
    mbid, resolved_artist, resolved_track = query_tuple
    print(f"\nInterpreting your query as: {resolved_artist} - {resolved_track}")
    results = _retrieve_results(kb, scorer, mbid, args)
    if args.use_clustering and results:
        clustered = cluster_and_organize(
            kb,
            results,
            top_k=args.k,
            kmeans=KMeansConfig(k=args.cluster_k, seed=args.cluster_seed, max_iters=args.cluster_max_iters),
        )
        results = list(clustered.diversified)
    print(f"\nQuery: {resolved_artist} - {resolved_track}\n")
    if not results:
        print("No results found (unusually low connectivity). Try a different song.")
        return []

    print("Top recommendations:")
    for i, r in enumerate(results, 1):
        song = kb.get_song(r.mbid) or {}
        print(
            f"  {i}. {song.get('artist', 'Unknown')} - {song.get('track', 'Unknown')}"
            f" | combined={r.combined_score:.3f} | pref={r.preference_score:.3f} | cost={r.path_cost:.3f}"
        )
    return list(results)


def _maybe_refine_weights(
    kb: KnowledgeBase,
    rules,
    weights: dict,
    ratings_path: Optional[str],
    *,
    enable: bool,
    refinement_alpha: float,
) -> dict:
    if not enable or not ratings_path:
        return weights
    try:
        ratings = UserRatings.load(ratings_path)
    except FileNotFoundError:
        return weights

    if len(ratings) == 0:
        return weights

    # Refine weights in the rule-based Module 2 model.
    return refine_weights_from_ratings(
        kb=kb,
        rules=rules,
        current_weights=weights,
        user_ratings=ratings,
        alpha=refinement_alpha,
        normalize=True,
    )


def _print_candidate_list(kb: KnowledgeBase, candidates: List[str], limit: int = 10) -> None:
    to_show = candidates[:limit]
    for i, mbid in enumerate(to_show, 1):
        song = kb.get_song(mbid) or {}
        artist = song.get("artist", "Unknown")
        track = song.get("track", "Unknown")
        print(f"  [{i}] {artist} - {track} ({mbid})")


def _resolve_query_to_mbid(kb: KnowledgeBase) -> Optional[tuple[str, str, str]]:
    """
    Prompt the user for track/artist and resolve to an MBID.
    If multiple candidates exist, prompt the user to pick one.
    """
    track = input("\nTrack name: ").strip()
    if not track:
        return None
    artist = input("Artist (optional): ").strip() or None

    try:
        mbid = kb.get_mbid_by_song(track, artist)
    except ValueError:
        print("Track name cannot be empty.")
        return None

    if mbid:
        resolved_song = kb.get_song(mbid) or {}
        # Some KB entries may have empty artist/track tags; fall back to user input.
        resolved_artist = (resolved_song.get("artist") or artist or "Unknown").strip()
        resolved_track = (resolved_song.get("track") or track or "Unknown").strip()
        return mbid, resolved_artist, resolved_track

    candidates = kb.find_songs_by_name(track, artist)
    if not candidates:
        print("No matches found in the knowledge base.")
        return None

    print("\nI found multiple possible matches. Choose one:")
    _print_candidate_list(kb, candidates, limit=10)

    if len(candidates) == 1:
        mbid = candidates[0]
        resolved_song = kb.get_song(mbid) or {}
        resolved_artist = (resolved_song.get("artist") or artist or "Unknown").strip()
        resolved_track = (resolved_song.get("track") or track or "Unknown").strip()
        return mbid, resolved_artist, resolved_track

    while True:
        choice = input("Pick number (or press Enter to cancel): ").strip()
        if not choice:
            return None
        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if 1 <= idx <= min(len(candidates), 10):
            mbid = candidates[idx - 1]
            resolved_song = kb.get_song(mbid) or {}
            resolved_artist = (resolved_song.get("artist") or artist or "Unknown").strip()
            resolved_track = (resolved_song.get("track") or track or "Unknown").strip()
            return mbid, resolved_artist, resolved_track
        print("Number out of range. Try again.")


def _retrieve_results(kb: KnowledgeBase, scorer: PreferenceScorer, mbid: str, args) -> List[SearchResult]:
    """
    Run Module 3 retrieval for a resolved query MBID.

    Extracted for testability: unit tests can call this helper to validate that
    the CLI's algorithm switch routes UCS vs Beam correctly.
    """
    retrieval_k = args.k
    if getattr(args, "use_clustering", False):
        retrieval_k = max(int(args.k), int(args.cluster_pool_size))

    if args.algorithm == "ucs":
        results = find_similar(
            kb=kb,
            query_mbid=mbid,
            scorer=scorer,
            k=retrieval_k,
            alpha=args.alpha,
            beta=args.beta,
            max_degree=args.max_degree,
        )
        # Optional second-stage rerank using Module 4 artifact.
        if getattr(args, "use_ml_reranker", False):
            try:
                artifact_path = getattr(args, "ml_reranker_artifact", "data/module4_reranker.json")
                artifact = load_reranker_artifact(artifact_path)
            except FileNotFoundError:
                return results
            return rerank_results_with_artifact(kb, results, artifact)
        return results

    raw = beam_topk(
        kb=kb,
        query_mbid=mbid,
        k=retrieval_k,
        beam_width=args.beam_width,
        max_depth=args.beam_depth,
        max_degree=args.max_degree,
    )
    results = rank_candidates_from_path_costs(
        kb=kb,
        raw_costs=raw,
        scorer=scorer,
        alpha=args.alpha,
        beta=args.beta,
    )
    if getattr(args, "use_ml_reranker", False):
        try:
            artifact_path = getattr(args, "ml_reranker_artifact", "data/module4_reranker.json")
            artifact = load_reranker_artifact(artifact_path)
        except FileNotFoundError:
            return results
        return rerank_results_with_artifact(kb, results, artifact)
    return results


def _slug(s: str) -> str:
    s = "".join(ch if ch.isalnum() else "-" for ch in (s or "").strip().lower())
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-") or "unknown"


def _save_recommendation_playlist(
    mbids: List[str],
    *,
    playlist_name: str,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recommendations_{_slug(playlist_name)}_{stamp}.json"
    out_path = out_dir / filename
    payload = {"name": playlist_name, "mbids": mbids}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_path


def _extend_session_mbids(session_mbids: List[str], results: List[SearchResult]) -> None:
    """Append recommendation MBIDs in order; skip duplicates (keep first occurrence)."""
    seen = set(session_mbids)
    for r in results:
        if r.mbid not in seen:
            seen.add(r.mbid)
            session_mbids.append(r.mbid)


def _save_session_playlist_if_needed(args: argparse.Namespace, session_mbids: List[str]) -> None:
    if not args.save_playlist or not session_mbids:
        return
    out_path = _save_recommendation_playlist(
        session_mbids,
        playlist_name="session_recommendations",
        out_dir=Path(args.playlist_out_dir),
    )
    print(f"\nSaved recommendation playlist to: {out_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query Module 3 with a user-provided song.")
    parser.add_argument("--kb", default="data/knowledge_base.json", help="Path to knowledge_base.json")
    parser.add_argument(
        "--persona-dir",
        default=None,
        help="Persona directory containing user_profile.json, user_ratings.json, user_playlists.json, and module4 artifacts.",
    )
    parser.add_argument(
        "--profile",
        default="data/user_profile.json",
        help="Path to user_profile.json produced by Module 2 survey",
    )
    parser.add_argument(
        "--ratings",
        default="data/user_ratings.json",
        help="Path to user_ratings.json produced by Module 2 ratings (optional).",
    )
    parser.add_argument("--use-ratings", action="store_true", help="Refine weights using saved user ratings if available.")
    parser.add_argument("--k", type=int, default=10, help="Top-K results to return.")
    parser.add_argument("--max-degree", type=int, default=50, help="Neighbor cap for UCS.")
    parser.add_argument("--alpha", type=float, default=1.0, help="Weight on (negated) normalized path cost term.")
    parser.add_argument("--beta", type=float, default=1.0, help="Weight on normalized preference score term.")
    parser.add_argument("--refinement-alpha", type=float, default=0.15, help="Learning rate for refining rule weights from ratings.")
    parser.add_argument(
        "--algorithm",
        choices=["ucs", "beam"],
        default="ucs",
        help="Retrieval algorithm used to generate candidates (UCS = exact, Beam = approximate).",
    )
    parser.add_argument("--beam-width", type=int, default=10, help="Beam width (only used for --algorithm beam).")
    parser.add_argument("--beam-depth", type=int, default=6, help="Beam max depth (only used for --algorithm beam).")
    parser.add_argument(
        "--use-ml-scorer",
        action="store_true",
        help="Wrap the rule-based scorer with the Module 4 learned scorer if data/module4_scorer.json exists.",
    )
    parser.add_argument(
        "--use-ml-reranker",
        action="store_true",
        help="Apply Module 4 reranker on top of search results if data/module4_reranker.json exists.",
    )
    parser.add_argument(
        "--ml-scorer-artifact",
        default="data/module4_scorer.json",
        help="Path to Module 4 scorer artifact JSON.",
    )
    parser.add_argument(
        "--ml-reranker-artifact",
        default="data/module4_reranker.json",
        help="Path to Module 4 reranker artifact JSON.",
    )
    parser.add_argument(
        "--playlists",
        default="data/user_playlists.json",
        help="Path to user_playlists.json (used when --seed-from-playlist is enabled).",
    )
    parser.add_argument(
        "--query-mbid",
        default=None,
        help="Run non-interactively using this exact query MBID.",
    )
    parser.add_argument(
        "--seed-from-playlist",
        action="store_true",
        help="Run non-interactively using one or more MBIDs from playlists (see --seed-count).",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=1,
        help="Number of playlist MBIDs to use when --seed-from-playlist is set.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one query cycle and exit (useful for demos/scripts).",
    )
    parser.add_argument(
        "--use-clustering",
        action="store_true",
        help="Apply Module 5 clustering to diversify the final top-K results (post-retrieval).",
    )
    parser.add_argument("--cluster-k", type=int, default=5, help="Number of clusters for Module 5 K-means.")
    parser.add_argument(
        "--cluster-pool-size",
        type=int,
        default=50,
        help="Top-N candidate pool size to cluster (must be >= k).",
    )
    parser.add_argument("--cluster-seed", type=int, default=343, help="Random seed for deterministic K-means init.")
    parser.add_argument("--cluster-max-iters", type=int, default=25, help="Max iterations for K-means.")
    parser.add_argument(
        "--auto-ml",
        action="store_true",
        default=True,
        help="Automatically enable Module 4 learned scorer + reranker if artifact files exist (default: enabled).",
    )
    parser.add_argument(
        "--no-auto-ml",
        action="store_false",
        dest="auto_ml",
        help="Disable auto enabling of Module 4 learned scorer/reranker.",
    )
    parser.add_argument(
        "--save-playlist",
        action="store_true",
        default=True,
        help="When you finish searching (no more songs), save one combined playlist to data/playlists/ (default: enabled).",
    )
    parser.add_argument(
        "--no-save-playlist",
        action="store_false",
        dest="save_playlist",
        help="Do not save a combined playlist when you exit the search loop.",
    )
    parser.add_argument(
        "--playlist-out-dir",
        default="data/playlists",
        help="Directory where recommendation playlists will be saved (default: data/playlists).",
    )
    return parser


def _build_scorer(kb: KnowledgeBase, args: argparse.Namespace) -> PreferenceScorer:
    profile = _load_profile(args.profile)

    rules = build_rules(profile)
    weights = get_default_weights(rules)
    weights = _maybe_refine_weights(
        kb=kb,
        rules=rules,
        weights=weights,
        ratings_path=args.ratings,
        enable=args.use_ratings,
        refinement_alpha=args.refinement_alpha,
    )
    base_scorer = PreferenceScorer(rules, weights)

    # Auto-ML: enable scorer/reranker when artifacts exist.
    if args.auto_ml:
        if Path(args.ml_scorer_artifact).exists():
            args.use_ml_scorer = True
        if Path(args.ml_reranker_artifact).exists():
            args.use_ml_reranker = True

    if args.use_ml_scorer:
        return build_scorer_with_optional_ml(
            base_scorer,
            artifact_path=args.ml_scorer_artifact,
            blend_weight=0.5,
        )
    return base_scorer


def _print_runtime_status(args: argparse.Namespace) -> None:
    print("\nLoaded Module 2 preferences.", end="")
    if args.use_ml_scorer:
        print(" Module 4 learned scorer is ENABLED.", end="")
    if args.use_ml_reranker:
        print(" Module 4 reranker is ENABLED.", end="")
    print("\nStarting Module 3 query...\n")
    if args.save_playlist:
        print(
            "When you finish (answer N to 'Search another song?'), your recommendations "
            "from this session are saved as one playlist.\n"
        )


def _run_query_mbid_mode(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    args: argparse.Namespace,
    session_mbids: List[str],
) -> bool:
    if not args.query_mbid:
        return False
    resolved = _resolve_query_from_mbid(kb, args.query_mbid)
    if not resolved:
        return True
    results = _print_results_for_query(kb, scorer, resolved, args)
    _extend_session_mbids(session_mbids, results)
    _save_session_playlist_if_needed(args, session_mbids)
    return True


def _run_seed_playlist_mode(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    args: argparse.Namespace,
    session_mbids: List[str],
) -> bool:
    if not args.seed_from_playlist:
        return False
    seed_mbids = _load_playlist_seed_mbids(args.playlists, args.seed_count)
    if not seed_mbids:
        print(f"No seed MBIDs found in playlists file: {args.playlists}")
        return True
    print(f"Using {len(seed_mbids)} seed MBID(s) from {args.playlists}")
    for mbid in seed_mbids:
        resolved = _resolve_query_from_mbid(kb, mbid)
        if not resolved:
            continue
        results = _print_results_for_query(kb, scorer, resolved, args)
        _extend_session_mbids(session_mbids, results)
    _save_session_playlist_if_needed(args, session_mbids)
    return True


def _run_interactive_mode(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    args: argparse.Namespace,
    session_mbids: List[str],
) -> None:
    while True:
        resolved = _resolve_query_to_mbid(kb)
        if not resolved:
            print("No query selected. Exiting.")
            return

        results = _print_results_for_query(kb, scorer, resolved, args)
        _extend_session_mbids(session_mbids, results)
        if args.once:
            _save_session_playlist_if_needed(args, session_mbids)
            return

        # Ask whether to search another song; only specific y/n variants are accepted.
        while True:
            again = input("\nSearch another song? [y/N]: ").strip().lower()
            if again in ("y", "yes"):
                break
            if again in ("n", "no", ""):
                _save_session_playlist_if_needed(args, session_mbids)
                return
            print("Invalid input (must be y/n). Please try again.")


def main() -> None:
    parser = _build_parser()

    args = _apply_persona_overrides(parser.parse_args())

    kb = KnowledgeBase(args.kb)
    scorer = _build_scorer(kb, args)
    _print_runtime_status(args)

    session_mbids: List[str] = []

    # Non-interactive paths (ideal for repeatable tests/demos).
    if _run_query_mbid_mode(kb, scorer, args, session_mbids):
        return

    if _run_seed_playlist_mode(kb, scorer, args, session_mbids):
        return

    _run_interactive_mode(kb, scorer, args, session_mbids)


if __name__ == "__main__":
    main()

