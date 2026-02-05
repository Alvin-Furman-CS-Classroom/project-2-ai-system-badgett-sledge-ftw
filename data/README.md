# Data Directory

This directory stores raw and processed data for the music recommendation system.

## Structure

```
data/
├── song_list.json          # Curated list of 1,000 songs (structured by decade/genre/tier)
├── song_list_flat.json     # Curated list of 1,000 songs (flattened format)
├── raw_songs.json          # Raw song data from data source (Module 1 input) - to be created
├── knowledge_base.json     # Structured knowledge base (Module 1 output) - to be created
└── test_data/              # Sample data for testing - to be created
```

## Current Files

- **song_list.json**: Curated list of 1,000 songs organized by decade (1960s-2020s), genre, and popularity tier (popular/mid-tier/obscure). This is the master list of songs to collect data for. The list includes specific tracks for each artist and is designed to be a comprehensive survey of music across all decades, not based on personal preferences.

- **song_list_flat.json**: Same 1,000 songs in a flattened format with metadata (decade, genre, tier, artist, track). Each entry includes:
  - `decade`: The decade the song is from (1960s-2020s)
  - `genre`: The genre classification
  - `tier`: Popularity tier (popular, mid_tier, or obscure)
  - `artist`: Artist name
  - `track`: Track title

## Future Files

- **raw_songs.json**: Will contain the actual collected song data (metadata, audio features, etc.) from your chosen data source (Last.fm, Spotify, etc.). This is the input for Module 1.

- **knowledge_base.json**: Will contain the structured knowledge base output from Module 1 (facts/relations like `has_tempo(song, bpm)`, `has_genre(song, genre)`, `produced_by(song, producer)`, etc.).

## Usage

1. The song list files (`song_list.json` and `song_list_flat.json`) define which songs to collect data for.
2. Use these lists with your data acquisition scripts to collect actual song data.
3. The collected data will be stored in `raw_songs.json`.
4. Module 1 will process `raw_songs.json` and create `knowledge_base.json`.

## Song List Details

The curated list contains:
- **1,000 songs total**
- **Distribution across decades**: Roughly 100-200 songs per decade (1960s-2020s)
- **Distribution across tiers**: 
  - Popular: ~41%
  - Mid-tier: ~36%
  - Obscure: ~23%
- **Genres covered**: Rock, pop, hip-hop, R&B, electronic, country, jazz, soul, folk, blues, and more
- **Representative artists**: Includes both well-known and influential but less commercial artists from each era
