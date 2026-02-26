#!/usr/bin/env python3
"""
Hill-climbing preference loop for Module 2.

Runs: Survey -> build rules + weights -> scorer -> loop:
  (next batch -> present -> rate -> refine weights -> update scorer) until done.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import collect_survey_cli, PreferenceProfile
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.sampling import sample_songs, sample_next_batch
from preferences.ratings import (
    UserRatings,
    collect_ratings_interactive,
    refine_weights_from_ratings,
)
import json


def save_profile(profile: PreferenceProfile, filepath: str = "data/user_profile.json") -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile_dict = {
        "preferred_genres": profile.preferred_genres,
        "preferred_moods": profile.preferred_moods,
        "danceable": profile.danceable,
        "voice_instrumental": profile.voice_instrumental,
        "timbre": profile.timbre,
        "loudness_min": profile.loudness_min,
        "loudness_max": profile.loudness_max,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile_dict, f, indent=2)
    print(f"  Profile saved to {filepath}")


def main(
    batch_size: int = 5,
    max_rounds: int = 3,
    kb_path: str = "data/knowledge_base.json",
) -> tuple:
    """
    Run the full hill-climbing preference collection loop.
    Returns (profile, ratings, final_scorer).
    """
    print("\n" + "=" * 70)
    print("  MODULE 2: HILL-CLIMBING PREFERENCE LOOP")
    print("=" * 70)

    print("\nLoading knowledge base...")
    try:
        kb = KnowledgeBase(kb_path)
        print(f"  Loaded {len(kb.songs)} songs")
    except FileNotFoundError:
        print(f"  Error: {kb_path} not found. Run from project root.")
        return None, None, None

    kb_genres = list(kb.get_all_genres())
    kb_moods = list(kb.get_all_moods())

    # Step 1: Survey
    print("\n" + "-" * 70)
    print("  STEP 1: SURVEY")
    print("-" * 70)
    profile = collect_survey_cli(kb_genres=kb_genres, kb_moods=kb_moods)
    save_profile(profile)

    # Step 2: Build rules and initial scorer
    rules = build_rules(profile)
    if not rules:
        print("  No rules from profile (all preferences 'any'). Using one batch of random songs.")
    weights = get_default_weights(rules)
    scorer = PreferenceScorer(rules, weights)

    # Step 3: Hill-climbing loop
    ratings = UserRatings()
    already_rated: list = []

    for round_num in range(1, max_rounds + 1):
        print("\n" + "-" * 70)
        print(f"  ROUND {round_num}/{max_rounds}: SONG BATCH (rate {batch_size} songs)")
        print("-" * 70)

        if round_num == 1:
            if rules:
                batch = sample_songs(kb, n=batch_size, method="score_based", scorer=scorer)
            else:
                batch = sample_songs(kb, n=batch_size, method="stratified")
        else:
            batch = sample_next_batch(kb, batch_size, scorer, already_rated)

        if not batch:
            print("  No more songs to rate.")
            break

        print(f"\n  Selected {len(batch)} songs (exploit + explore).")
        new_ratings = collect_ratings_interactive(batch, kb)
        for mbid, r in new_ratings.get_all_ratings():
            ratings.add_rating(mbid, r)
            already_rated.append(mbid)

        if not rules:
            break

        weights = refine_weights_from_ratings(kb, rules, weights, ratings, alpha=0.15)
        scorer = PreferenceScorer(rules, weights)
        print(f"  Weights refined from your ratings. Total rated so far: {len(ratings)}")

        if round_num < max_rounds:
            try:
                cont = input("\n  Continue to next batch? [Y/n]: ").strip().lower()
                if cont and cont != "y" and cont != "yes":
                    break
            except (KeyboardInterrupt, EOFError):
                break

    # Save ratings
    ratings_path = "data/user_ratings.json"
    ratings.save(ratings_path)
    print(f"\n  Ratings saved to {ratings_path}")

    # Optional: show top-scoring songs
    if rules and len(ratings) > 0:
        print("\n" + "-" * 70)
        print("  TOP-SCORING SONGS (with refined weights)")
        print("-" * 70)
        all_mbids = kb.get_all_songs()
        scored = [(mbid, scorer.score(mbid, kb)) for mbid in all_mbids]
        scored.sort(key=lambda x: x[1], reverse=True)
        for i, (mbid, score) in enumerate(scored[:10], 1):
            song = kb.get_song(mbid)
            name = f"{song.get('artist', '?')} - {song.get('track', '?')}" if song else mbid
            print(f"  {i}. {name}  (score: {score:.3f})")

    print("\n" + "=" * 70)
    print("  PREFERENCE LOOP COMPLETE")
    print("=" * 70 + "\n")
    return profile, ratings, scorer


if __name__ == "__main__":
    main(batch_size=5, max_rounds=3)
