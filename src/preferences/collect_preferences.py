#!/usr/bin/env python3
"""
Complete preference collection: Survey + Song Ratings

This script runs the full Module 2 preference collection flow:
1. Run survey to get preference profile
2. Sample songs from KB
3. Collect user ratings on sampled songs
4. Save profile and ratings for use in rule building
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import collect_survey_cli, PreferenceProfile
from preferences.sampling import sample_songs
from preferences.ratings import collect_ratings_interactive, UserRatings, Rating
import json


def save_profile(profile: PreferenceProfile, filepath: str = "data/user_profile.json"):
    """Save preference profile to JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    profile_dict = {
        "preferred_genres": profile.preferred_genres,
        "preferred_moods": profile.preferred_moods,
        "danceable": profile.danceable,
        "voice_instrumental": profile.voice_instrumental,
        "timbre": profile.timbre,
        "loudness_min": profile.loudness_min,
        "loudness_max": profile.loudness_max
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profile_dict, f, indent=2)
    
    print(f"✓ Profile saved to {filepath}")


def main():
    """Run complete preference collection flow."""
    print("\n" + "=" * 70)
    print("  MODULE 2: PREFERENCE COLLECTION")
    print("=" * 70)
    
    # Load knowledge base
    print("\nStep 1: Loading knowledge base...")
    try:
        kb = KnowledgeBase("data/knowledge_base.json")
        print(f"✓ Loaded {len(kb.songs)} songs")
    except FileNotFoundError:
        print("❌ Error: Could not find data/knowledge_base.json")
        print("   Make sure you're running from the project root directory.")
        return
    
    # Step 1: Survey
    print("\n" + "=" * 70)
    print("  STEP 1: SURVEY")
    print("=" * 70)
    kb_genres = list(kb.get_all_genres())
    kb_moods = list(kb.get_all_moods())
    
    profile = collect_survey_cli(kb_genres=kb_genres, kb_moods=kb_moods)
    
    # Save profile
    save_profile(profile)
    
    # Step 2: Sample songs based on preferences
    print("\n" + "=" * 70)
    print("  STEP 2: SONG SAMPLING")
    print("=" * 70)
    print("\nSampling songs that match your preferences...")
    
    num_songs = 15
    print(f"Selecting {num_songs} songs that match your preferences...")
    sampled_mbids = sample_songs(kb, n=num_songs, method="preference_based", profile=profile)
    
    print(f"✓ Selected {len(sampled_mbids)} songs matching your preferences")
    
    # Step 3: Collect ratings
    print("\n" + "=" * 70)
    print("  STEP 3: SONG RATINGS")
    print("=" * 70)
    
    ratings = collect_ratings_interactive(sampled_mbids, kb)
    
    # Save ratings
    ratings_path = "data/user_ratings.json"
    ratings.save(ratings_path)
    print(f"✓ Ratings saved to {ratings_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  COLLECTION COMPLETE")
    print("=" * 70)
    print(f"\n✓ Profile: {len(profile.preferred_genres)} genres, {len(profile.preferred_moods)} moods")
    print(f"✓ Ratings: {len(ratings)} songs rated")
    
    # Show rating distribution
    rating_counts = {
        "Really Like": len([r for mbid, r in ratings.get_all_ratings() if r == Rating.REALLY_LIKE]),
        "Like": len([r for mbid, r in ratings.get_all_ratings() if r == Rating.LIKE]),
        "Neutral": len([r for mbid, r in ratings.get_all_ratings() if r == Rating.NEUTRAL]),
        "Dislike": len([r for mbid, r in ratings.get_all_ratings() if r == Rating.DISLIKE]),
    }
    print(f"\nRating distribution:")
    for rating_name, count in rating_counts.items():
        print(f"  {rating_name}: {count}")
    
    print("\n" + "=" * 70)
    print("  Next Steps:")
    print("=" * 70)
    print("  Your profile and ratings are saved and ready to use for:")
    print("    1. Building logical rules from your profile")
    print("    2. Refining rule weights based on your ratings")
    print("    3. Scoring songs in Module 3")
    print("=" * 70 + "\n")
    
    return profile, ratings


if __name__ == "__main__":
    profile, ratings = main()
