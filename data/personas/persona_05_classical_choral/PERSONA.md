# Persona: Classical + choral (accuracy demo)

## Intent

Older / long-form listener centered on **classical** (`cla`), including
**choral** repertoire. Vocal vs instrumental is **not** fixed so both
orchestral and choral music can score.

## How the files encode this

- **`user_profile.json`**: **Only** `cla` as preferred genre; `relaxed` and
  `acoustic` moods; **not danceable**; **`voice_instrumental` explicitly null**
  so choir/orchestra both match; **quiet** loudness band.
- **`user_playlists.json`**: Long playlist sampled from the classical index.
- **`user_ratings.json`**: Strong positives on playlist; dislikes on hip-hop,
  metal, etc.—sharp boundary for demos.
- **`module4_*.json`**: Should emphasize classical/quiet/acoustic-style features.

## Note

The KB tags **genre**, not “choral” as its own label; null
`voice_instrumental` is what allows **choral and instrumental** classical in
the same persona.
