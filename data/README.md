# Data Directory

This directory stores the knowledge base and archived data for the music recommendation system.

## Structure

```
data/
├── knowledge_base.json     # Structured knowledge base (Module 1 output) - ACTIVE
├── outdated data/          # Archived data files (no longer used)
│   ├── raw_songs.json      # Raw song data from data collection (archived)
│   ├── song_list_flat.json # Curated song list in flattened format (archived)
│   └── song_list.json      # Curated song list by decade/genre/tier (archived)
└── example_raw_song_data/  # Example AcousticBrainz data file (reference only)
    └── 000a8d06-0f2c-4aa1-88d0-802b3fdcd29c-0.json
```

## Active Files

### knowledge_base.json

The structured knowledge base output from Module 1. This is the **primary data file** used by all modules in the system.

**Structure:**
- `songs`: Dictionary mapping MBIDs to song metadata (artist, track, album)
- `facts`: Dictionary of fact types mapping MBIDs to values:
  - `has_genre`: Genre classifications (list of strings)
  - `has_loudness`: Loudness in dB (float)
  - `has_danceable`: Danceability classification (string: "danceable" or "not_danceable")
  - `has_voice_instrumental`: Voice/instrumental classification (string: "voice" or "instrumental")
  - `has_timbre`: Timbre classification (string: e.g., "bright", "dark")
  - `has_mood`: Mood classifications (list of strings: e.g., "happy", "sad", "relaxed")
  - `has_duration`: Song duration in seconds (float)
- `indexes`: Pre-built indexes for fast querying:
  - `by_genre`: Maps genre names to lists of MBIDs
  - `by_danceable`: Maps danceability to lists of MBIDs
  - `by_voice_instrumental`: Maps voice/instrumental to lists of MBIDs
  - `by_timbre`: Maps timbre to lists of MBIDs
  - `by_mood`: Maps moods to lists of MBIDs

**Usage:**
- Loaded by `src/knowledge_base_wrapper.py` for querying
- Used by Module 2 (Rule-based preferences) for rule evaluation
- Used by Module 3 (Search) for finding similar songs
- Used by Module 4 (ML) for feature extraction
- Used by Module 5 (Clustering) for similarity calculations

## Archived Files

### outdated data/

This folder contains data files that were used during Module 1 development but are no longer actively used:

- **raw_songs.json**: Raw song data collected from MusicBrainz and AcousticBrainz APIs. This was the intermediate data format before knowledge base construction.

- **song_list.json**: Original curated list of 1,000 songs organized by decade (1960s-2020s), genre, and popularity tier. Used to generate the initial song list for data collection.

- **song_list_flat.json**: Flattened version of the song list with metadata (decade, genre, tier, artist, track). Used during data collection to iterate through songs.

**Why archived:**
- These files served their purpose during data collection and knowledge base construction
- The knowledge base (`knowledge_base.json`) now contains all the structured information needed
- Kept for reference and historical context

## Reference Files

### example_raw_song_data/

Contains example AcousticBrainz data files showing the raw format of audio feature data. Useful for understanding the data structure and debugging.

## Data Flow

1. **Data Collection** (Completed):
   - Song lists (`song_list.json`, `song_list_flat.json`) were used to identify songs
   - MusicBrainz API was used to get MBIDs and metadata
   - AcousticBrainz API was used to get audio features
   - Data was stored in `raw_songs.json`

2. **Knowledge Base Construction** (Completed):
   - `raw_songs.json` and AcousticBrainz dump files were processed
   - Structured facts and relations were extracted
   - Indexes were built for fast querying
   - Output saved to `knowledge_base.json`

3. **Current Usage** (Active):
   - All modules query `knowledge_base.json` via `KnowledgeBase` wrapper class
   - No direct access to raw data files needed

## Statistics

The knowledge base contains:
- **1,000 songs** with structured facts and relations
- **Genre coverage**: Multiple genres including rock, pop, electronic, ambient, and more
- **Feature coverage**: Loudness, danceability, voice/instrumental, timbre, mood, and duration data
- **Indexed for fast queries**: Pre-built indexes enable efficient searching by genre, mood, danceability, etc.
