"""
Knowledge Base Query Demonstrations for Module 1 Checkpoint

This script demonstrates the power and capabilities of our knowledge base
for use in future modules (Search, ML, Clustering, etc.)

Run this to showcase:
- Knowledge Representation (facts/relations)
- Query capabilities for Module 3 (Search)
- Data structure for Module 2 (Rule-based preferences)
- Feature extraction for Module 4 (ML)
- Similarity metrics for Module 5 (Clustering)
"""

import json
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import sys
from pathlib import Path

# Add src directory to path to import KnowledgeBase
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from knowledge_base_wrapper import KnowledgeBase


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_song_info(kb: KnowledgeBase, mbid: str, title: str = "Song"):
    """Print formatted song information."""
    song = kb.get_song(mbid)
    if not song:
        print(f"  {title}: Song not found")
        return
    
    print(f"\n  {title}:")
    print(f"    Artist: {song.get('artist', 'Unknown')}")
    print(f"    Track: {song.get('track', 'Unknown')}")
    print(f"    Album: {song.get('album', 'Unknown')}")
    
    # Show available facts (only show what exists)
    facts_shown = []
    
    genre = kb.get_fact('has_genre', mbid)
    if genre:
        genre_str = ', '.join(genre) if isinstance(genre, list) else str(genre)
        facts_shown.append(f"Genre: {genre_str}")
    
    loudness = kb.get_fact('has_loudness', mbid)
    if loudness is not None:
        facts_shown.append(f"Loudness: {loudness:.1f} dB")
    
    danceable = kb.get_fact('has_danceable', mbid)
    if danceable:
        facts_shown.append(f"Danceable: {danceable}")
    
    voice_instrumental = kb.get_fact('has_voice_instrumental', mbid)
    if voice_instrumental:
        facts_shown.append(f"Type: {voice_instrumental}")
    
    timbre = kb.get_fact('has_timbre', mbid)
    if timbre:
        facts_shown.append(f"Timbre: {timbre}")
    
    mood = kb.get_fact('has_mood', mbid)
    if mood:
        mood_str = ', '.join(mood) if isinstance(mood, list) else str(mood)
        facts_shown.append(f"Mood: {mood_str}")
    
    if facts_shown:
        print(f"    Facts: {', '.join(facts_shown)}")


def demo_1_knowledge_representation(kb: KnowledgeBase):
    """Demonstrate knowledge representation: facts and relations."""
    print_section("DEMO 1: Knowledge Representation (Facts & Relations)")
    
    print("\n  Our knowledge base represents music data as facts and relations:")
    print("    • has_genre(song, genre)")
    print("    • has_loudness(song, db)")
    print("    • has_danceable(song, danceable/not_danceable)")
    print("    • has_voice_instrumental(song, voice/instrumental)")
    print("    • has_timbre(song, timbre)")
    print("    • has_mood(song, mood)")
    
    # Show example facts
    print("\n  Example: Querying facts for a song")
    sample_mbid = list(kb.songs.keys())[0]
    print_song_info(kb, sample_mbid, "Sample Song")
    
    # Show statistics
    print("\n  Knowledge Base Statistics:")
    print(f"    • Total songs: {len(kb.songs)}")
    
    genre_count = len(kb.facts.get('has_genre', {}))
    loudness_count = len(kb.facts.get('has_loudness', {}))
    danceable_count = len(kb.facts.get('has_danceable', {}))
    voice_instrumental_count = len(kb.facts.get('has_voice_instrumental', {}))
    timbre_count = len(kb.facts.get('has_timbre', {}))
    mood_count = len(kb.facts.get('has_mood', {}))
    
    print(f"    • Songs with genre data: {genre_count}")
    print(f"    • Songs with loudness data: {loudness_count}")
    print(f"    • Songs with danceability data: {danceable_count}")
    print(f"    • Songs with voice/instrumental data: {voice_instrumental_count}")
    print(f"    • Songs with timbre data: {timbre_count}")
    print(f"    • Songs with mood data: {mood_count}")
    
    all_genres = kb.get_all_genres()
    print(f"    • Unique genres: {len(all_genres)}")
    print(f"    • Genre examples: {', '.join(list(all_genres)[:10])}")
    
    all_moods = kb.get_all_moods()
    print(f"    • Unique moods: {len(all_moods)}")
    print(f"    • Mood examples: {', '.join(list(all_moods)[:5])}")


def demo_2_search_queries(kb: KnowledgeBase):
    """Demonstrate queries that Module 3 (Search) will use."""
    print_section("DEMO 2: Search Queries (Module 3 Preview)")
    
    print("\n  These queries demonstrate how Module 3 will search the knowledge base:")
    
    # Query 1: Find songs by genre
    print("\n  1. Find songs in 'rock' genre:")
    rock_songs = kb.songs_by_genre('rock')
    print(f"     Found {len(rock_songs)} rock songs")
    if rock_songs:
        print_song_info(kb, rock_songs[0], "Example Result")
    
    # Query 2: Find songs by danceability
    print("\n  2. Find danceable songs:")
    danceable_songs = kb.songs_by_danceable('danceable')
    print(f"     Found {len(danceable_songs)} danceable songs")
    if danceable_songs:
        print_song_info(kb, danceable_songs[0], "Example Result")
    
    # Query 3: Multi-criteria search (genre + danceability)
    print("\n  3. Multi-criteria search: Danceable rock songs:")
    danceable_rock = [mbid for mbid in rock_songs if mbid in danceable_songs]
    print(f"     Found {len(danceable_rock)} songs matching both criteria")
    if danceable_rock:
        print_song_info(kb, danceable_rock[0], "Example Result")
    
    # Query 4: Find songs by loudness range
    print("\n  4. Find songs with loudness between -10 and -5 dB (moderate volume):")
    moderate_loudness = kb.songs_in_loudness_range(-10, -5)
    print(f"     Found {len(moderate_loudness)} songs")
    if moderate_loudness:
        print_song_info(kb, moderate_loudness[0], "Example Result")
    
    # Query 5: Find songs by mood
    print("\n  5. Find songs with 'happy' mood:")
    happy_songs = kb.songs_by_mood('happy')
    print(f"     Found {len(happy_songs)} happy songs")
    if happy_songs:
        print_song_info(kb, happy_songs[0], "Example Result")
    
    # Query 6: Complex multi-criteria search
    print("\n  6. Complex search: Danceable rock songs with happy mood:")
    complex_match = [mbid for mbid in danceable_rock if mbid in happy_songs]
    print(f"     Found {len(complex_match)} songs matching all criteria")
    if complex_match:
        print_song_info(kb, complex_match[0], "Example Result")


def demo_3_rule_based_preferences(kb: KnowledgeBase):
    """Demonstrate how Module 2 (Rule-based preferences) will use the KB."""
    print_section("DEMO 3: Rule-Based Preferences (Module 2 Preview)")
    
    print("\n  Module 2 will create rules like:")
    print("    IF genre = 'rock' AND danceable = 'danceable' THEN high_score")
    print("    IF mood = 'happy' AND voice_instrumental = 'voice' THEN medium_score")
    print("    IF loudness IN [-10, -5] AND timbre = 'bright' THEN high_score")
    
    # Show how rules would be evaluated
    print("\n  Example: Evaluating a preference rule")
    print("    Rule: 'I like danceable rock songs with happy mood'")
    
    rock_songs = kb.songs_by_genre('rock')
    danceable_songs = kb.songs_by_danceable('danceable')
    happy_songs = kb.songs_by_mood('happy')
    
    matching = [mbid for mbid in rock_songs 
                if mbid in danceable_songs and mbid in happy_songs]
    
    print(f"    • Songs matching rule: {len(matching)}")
    print(f"    • Rule evaluation: IF genre='rock' AND danceable='danceable' AND mood='happy' THEN score=1.0")
    
    if matching:
        print("\n    Matching songs:")
        for i, mbid in enumerate(matching[:3], 1):
            song = kb.get_song(mbid)
            genre = kb.get_fact('has_genre', mbid)
            mood = kb.get_fact('has_mood', mbid)
            genre_str = ', '.join(genre[:2]) if isinstance(genre, list) else str(genre)
            mood_str = ', '.join(mood[:2]) if isinstance(mood, list) else str(mood)
            print(f"      {i}. {song.get('artist')} - {song.get('track')} (Genre: {genre_str}, Mood: {mood_str})")
    else:
        # Show partial matches
        print("\n    Partial matches (genre + danceable):")
        partial = [mbid for mbid in rock_songs if mbid in danceable_songs]
        for i, mbid in enumerate(partial[:3], 1):
            song = kb.get_song(mbid)
            print(f"      {i}. {song.get('artist')} - {song.get('track')}")


def demo_4_ml_features(kb: KnowledgeBase):
    """Demonstrate feature extraction for Module 4 (ML)."""
    print_section("DEMO 4: Machine Learning Features (Module 4 Preview)")
    
    print("\n  Module 4 will extract features from the knowledge base for training:")
    
    # Show feature vector example
    print("\n  Example feature vector for a song:")
    sample_mbid = list(kb.songs.keys())[0]
    song = kb.get_song(sample_mbid)
    
    features = {
        'genre': kb.get_fact('has_genre', sample_mbid),
        'loudness': kb.get_fact('has_loudness', sample_mbid),
        'danceable': kb.get_fact('has_danceable', sample_mbid),
        'voice_instrumental': kb.get_fact('has_voice_instrumental', sample_mbid),
        'timbre': kb.get_fact('has_timbre', sample_mbid),
        'mood': kb.get_fact('has_mood', sample_mbid),
    }
    
    print(f"    Song: {song.get('artist')} - {song.get('track')}")
    print("    Features:")
    for feature, value in features.items():
        if value is not None:
            if isinstance(value, list):
                print(f"      • {feature}: {value}")
            else:
                print(f"      • {feature}: {value}")
    
    # Show feature statistics
    print("\n  Feature coverage statistics:")
    total = len(kb.songs)
    for fact_type in ['has_genre', 'has_loudness', 'has_danceable', 
                      'has_voice_instrumental', 'has_timbre', 'has_mood']:
        count = len(kb.facts.get(fact_type, {}))
        coverage = (count / total * 100) if total > 0 else 0
        print(f"    • {fact_type}: {count}/{total} songs ({coverage:.1f}%)")


def demo_5_clustering_features(kb: KnowledgeBase):
    """Demonstrate similarity metrics for Module 5 (Clustering)."""
    print_section("DEMO 5: Clustering & Similarity (Module 5 Preview)")
    
    print("\n  Module 5 will cluster songs based on similarity in the knowledge base:")
    
    # Show similarity calculation
    print("\n  Example: Calculating similarity between two songs")
    
    songs_list = list(kb.songs.keys())
    if len(songs_list) >= 2:
        song1_mbid = songs_list[0]
        song2_mbid = songs_list[1]
        
        song1 = kb.get_song(song1_mbid)
        song2 = kb.get_song(song2_mbid)
        
        print(f"\n    Song 1: {song1.get('artist')} - {song1.get('track')}")
        print(f"    Song 2: {song2.get('artist')} - {song2.get('track')}")
        
        # Calculate similarity metrics
        genre1 = kb.get_fact('has_genre', song1_mbid)
        genre2 = kb.get_fact('has_genre', song2_mbid)
        
        loudness1 = kb.get_fact('has_loudness', song1_mbid)
        loudness2 = kb.get_fact('has_loudness', song2_mbid)
        
        danceable1 = kb.get_fact('has_danceable', song1_mbid)
        danceable2 = kb.get_fact('has_danceable', song2_mbid)
        
        mood1 = kb.get_fact('has_mood', song1_mbid)
        mood2 = kb.get_fact('has_mood', song2_mbid)
        
        print("\n    Similarity metrics:")
        
        if genre1 and genre2:
            if isinstance(genre1, list) and isinstance(genre2, list):
                shared_genres = set(genre1) & set(genre2)
                print(f"      • Shared genres: {len(shared_genres)} ({', '.join(shared_genres) if shared_genres else 'none'})")
        
        if loudness1 is not None and loudness2 is not None:
            loudness_diff = abs(loudness1 - loudness2)
            print(f"      • Loudness difference: {loudness_diff:.1f} dB")
        
        if danceable1 and danceable2:
            danceable_match = "Yes" if danceable1 == danceable2 else "No"
            print(f"      • Danceability match: {danceable_match}")
        
        if mood1 and mood2:
            if isinstance(mood1, list) and isinstance(mood2, list):
                shared_moods = set(mood1) & set(mood2)
                print(f"      • Shared moods: {len(shared_moods)} ({', '.join(shared_moods) if shared_moods else 'none'})")
        
        # Show clustering potential
        print("\n  Clustering capabilities:")
        print("    • Can cluster by genre")
        print("    • Can cluster by loudness ranges")
        print("    • Can cluster by danceability")
        print("    • Can cluster by voice/instrumental")
        print("    • Can cluster by timbre")
        print("    • Can cluster by mood")
        print("    • Can cluster by multiple features simultaneously")


def demo_6_statistics(kb: KnowledgeBase):
    """Show comprehensive statistics about the knowledge base."""
    print_section("DEMO 6: Knowledge Base Statistics")
    
    print("\n  Overall Knowledge Base Coverage:")
    print(f"    • Total songs: {len(kb.songs)}")
    
    # Fact coverage
    print("\n  Fact Coverage:")
    for fact_type in ['has_genre', 'has_loudness', 'has_danceable', 
                      'has_voice_instrumental', 'has_timbre', 'has_mood', 'has_duration']:
        count = len(kb.facts.get(fact_type, {}))
        coverage = (count / len(kb.songs) * 100) if kb.songs else 0
        print(f"    • {fact_type}: {count} songs ({coverage:.1f}%)")
    
    # Genre distribution
    print("\n  Genre Distribution (top 10):")
    genre_facts = kb.facts.get('has_genre', {})
    genre_counter = Counter()
    for genres in genre_facts.values():
        if isinstance(genres, list):
            genre_counter.update(genres)
    
    for genre, count in genre_counter.most_common(10):
        print(f"    • {genre}: {count} songs")
    
    # Loudness distribution
    print("\n  Loudness Distribution:")
    loudness_facts = kb.facts.get('has_loudness', {})
    if loudness_facts:
        loudnesses = list(loudness_facts.values())
        print(f"    • Min loudness: {min(loudnesses):.1f} dB")
        print(f"    • Max loudness: {max(loudnesses):.1f} dB")
        print(f"    • Average loudness: {sum(loudnesses)/len(loudnesses):.1f} dB")
    
    # Danceability distribution
    print("\n  Danceability Distribution:")
    danceable_facts = kb.facts.get('has_danceable', {})
    danceable_counter = Counter(danceable_facts.values())
    for danceable, count in danceable_counter.items():
        print(f"    • {danceable}: {count} songs")
    
    # Mood distribution
    print("\n  Mood Distribution (top 5):")
    mood_facts = kb.facts.get('has_mood', {})
    mood_counter = Counter()
    for moods in mood_facts.values():
        if isinstance(moods, list):
            mood_counter.update(moods)
    
    for mood, count in mood_counter.most_common(5):
        print(f"    • {mood}: {count} songs")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  MUSIC RECOMMENDATION SYSTEM - KNOWLEDGE BASE DEMONSTRATION")
    print("  Module 1 Checkpoint: Knowledge Representation & Data Processing")
    print("=" * 70)
    
    # Load knowledge base
    try:
        kb = KnowledgeBase("data/knowledge_base.json")
        print(f"✓ Loaded knowledge base: {len(kb.songs)} songs")
    except FileNotFoundError:
        print("\n❌ Error: Could not find data/knowledge_base.json")
        print("   Make sure you're running from the project root directory.")
        return
    except Exception as e:
        print(f"\n❌ Error loading knowledge base: {e}")
        return
    
    # Run all demos
    demo_1_knowledge_representation(kb)
    demo_2_search_queries(kb)
    demo_3_rule_based_preferences(kb)
    demo_4_ml_features(kb)
    demo_5_clustering_features(kb)
    demo_6_statistics(kb)
    
    # Final summary
    print_section("SUMMARY")
    print("\n  This knowledge base provides:")
    print("    ✓ Structured facts and relations for knowledge representation")
    print("    ✓ Fast query capabilities for Module 3 (Search algorithms)")
    print("    ✓ Rule evaluation support for Module 2 (Propositional logic)")
    print("    ✓ Feature extraction for Module 4 (Machine learning)")
    print("    ✓ Similarity metrics for Module 5 (Clustering)")
    print("\n  The knowledge base is ready to support all future modules!")
    print("\n" + "=" * 70 + "\n")


    print_section("HUMAN GENERATED QUERY EXAMPLE")
    mbid = kb.get_mbid_by_song("Fire Engine Dream")
    print("\nFire Engine Dream by Sonic Youth MBID: " + mbid)
    print("Genres: " + str(kb.get_fact('has_genre',mbid)))
    print("Loudness: " + str(kb.get_fact('has_loudness', mbid)))
    print("\n")



   

if __name__ == "__main__":
    main()
