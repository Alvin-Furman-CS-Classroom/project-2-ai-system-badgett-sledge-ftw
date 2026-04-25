# Persona: Classic rock / dad-rock (diversity demo)

## Intent

Represents a **Gen X “radio rock”** listener: rock, blues-based tracks, and a
little country/folk-adjacent material—one ecosystem, but **enough genre spread**
that clustering and graph neighbors can differ (anthem rock vs ballads vs
twang).

## How the files encode this

- **`user_profile.json`**: `roc`, `blues`, `folkcountry` with `happy`,
  `relaxed`, `acoustic` moods; moderate loudness; open categorical prefs.
- **`user_playlists.json`**: Weighted toward **rock**, with **blues** and
  **folk/country** representation—not a single-subgenre list.
- **`user_ratings.json`**: Diverse-style mix on the playlist; dislikes on
  hip-hop and techno outliers; a little neutral pop—keeps the model from
  pretending taste is only guitar rock.
- **`module4_*.json`**: Learns feature weights aligned with that multi-genre
  classic-radio palette.

## Demo tips

Good contrast with **hip-hop** or **EDM-heavy** personas; diversity shows up as
rock vs blues vs folk **clusters** in ranked pools.
