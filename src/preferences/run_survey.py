#!/usr/bin/env python3
"""
Run the music preference survey interactively.

Usage:
    python3 src/preferences/run_survey.py
"""

import sys
from pathlib import Path

# Add src to path to import KnowledgeBase
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_wrapper import KnowledgeBase
from preferences.survey import collect_survey_cli, PreferenceProfile


def main():
    """Load KB and run interactive survey."""
    print("Loading knowledge base...")
    try:
        kb = KnowledgeBase("data/knowledge_base.json")
        print(f"✓ Loaded {len(kb.songs)} songs\n")
    except FileNotFoundError:
        print("⚠ Warning: Could not find data/knowledge_base.json")
        print("  Running survey without KB validation...\n")
        kb = None
    
    # Get available genres and moods from KB if available
    kb_genres = list(kb.get_all_genres()) if kb else None
    kb_moods = list(kb.get_all_moods()) if kb else None
    
    # Run the survey
    profile = collect_survey_cli(kb_genres=kb_genres, kb_moods=kb_moods)
    
    # Display the collected profile
    print("\n" + "=" * 70)
    print("  YOUR PREFERENCE PROFILE")
    print("=" * 70)
    print(f"\nPreferred Genres: {profile.preferred_genres if profile.preferred_genres else '(none)'}")
    print(f"Preferred Moods: {profile.preferred_moods if profile.preferred_moods else '(none)'}")
    print(f"Danceability: {profile.danceable if profile.danceable else '(no preference)'}")
    print(f"Voice/Instrumental: {profile.voice_instrumental if profile.voice_instrumental else '(no preference)'}")
    print(f"Timbre: {profile.timbre if profile.timbre else '(no preference)'}")
    if profile.has_loudness_preference():
        print(f"Loudness Range: {profile.loudness_min} to {profile.loudness_max} dB")
    else:
        print("Loudness: (no preference)")
    
    print("\n" + "=" * 70)
    print("  Profile saved! This will be used to build preference rules.")
    print("=" * 70 + "\n")
    
    return profile


if __name__ == "__main__":
    profile = main()
