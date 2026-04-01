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


def _load_profile(profile_path: str) -> PreferenceProfile:
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return PreferenceProfile(**data)


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
        return candidates[0]

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
    if args.algorithm == "ucs":
        results = find_similar(
            kb=kb,
            query_mbid=mbid,
            scorer=scorer,
            k=args.k,
            alpha=args.alpha,
            beta=args.beta,
            max_degree=args.max_degree,
        )
        # Optional second-stage rerank using Module 4 artifact.
        if args.use_ml_reranker:
            try:
                artifact = load_reranker_artifact(args.ml_reranker_artifact)
            except FileNotFoundError:
                return results
            return rerank_results_with_artifact(kb, results, artifact)
        return results

    raw = beam_topk(
        kb=kb,
        query_mbid=mbid,
        k=args.k,
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
    if args.use_ml_reranker:
        try:
            artifact = load_reranker_artifact(args.ml_reranker_artifact)
        except FileNotFoundError:
            return results
        return rerank_results_with_artifact(kb, results, artifact)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Module 3 with a user-provided song.")
    parser.add_argument("--kb", default="data/knowledge_base.json", help="Path to knowledge_base.json")
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

    args = parser.parse_args()

    kb = KnowledgeBase(args.kb)
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
    if args.use_ml_scorer:
        scorer = build_scorer_with_optional_ml(
            base_scorer,
            artifact_path=args.ml_scorer_artifact,
            blend_weight=0.5,
        )
    else:
        scorer = base_scorer

    print("\nLoaded Module 2 preferences.", end="")
    if args.use_ml_scorer:
        print(" Module 4 learned scorer is ENABLED.", end="")
    if args.use_ml_reranker:
        print(" Module 4 reranker is ENABLED.", end="")
    print("\nStarting Module 3 query...\n")

    while True:
        resolved = _resolve_query_to_mbid(kb)
        if not resolved:
            print("No query selected. Exiting.")
            return

        mbid, resolved_artist, resolved_track = resolved

        # Always show the interpreted song, since partial-name matching is allowed.
        print(f"\nInterpreting your query as: {resolved_artist} - {resolved_track}")

        results = _retrieve_results(kb, scorer, mbid, args)

        # Query label after search (kept for clarity with the output block).
        print(f"\nQuery: {resolved_artist} - {resolved_track}\n")
        if not results:
            print("No results found (unusually low connectivity). Try a different song.")
        else:
            print("Top recommendations:")
            for i, r in enumerate(results, 1):
                song = kb.get_song(r.mbid) or {}
                print(
                    f"  {i}. {song.get('artist', 'Unknown')} - {song.get('track', 'Unknown')}"
                    f" | combined={r.combined_score:.3f} | pref={r.preference_score:.3f} | cost={r.path_cost:.3f}"
                )

        # Ask whether to search another song; only specific y/n variants are accepted.
        while True:
            again = input("\nSearch another song? [y/N]: ").strip().lower()
            if again in ("y", "yes"):
                break
            if again in ("n", "no", ""):
                return
            print("Invalid input (must be y/n). Please try again.")


if __name__ == "__main__":
    main()

