# Persona: College commuter (diversity demo)

## Intent

Represents a listener whose **day splits between high-energy and chill**:
chart-adjacent hip-hop, R&B, and pop crossover tracks. The goal is a **broad
but coherent** taste profile so retrieval—and later Module 5 clustering—can
surface **multiple lanes** (party vs relaxed, rap vs melodic) instead of one
compact cluster.

## How the files encode this

- **`user_profile.json`**: `hip`, `rhy`, and `pop` with moods `happy`, `party`,
  and `relaxed`. Loudness in the **moderate** survey band. Open-ended fields
  (`danceable`, `voice_instrumental`, `timbre` left null) so both upbeat and
  smoother tracks can match.
- **`user_playlists.json`**: Deliberate **split**—more hip-hop, substantial R&B,
  and a pop slice—so positive supervision is visibly multi-genre.
- **`user_ratings.json`**: **Mixed** `LIKE`, `REALLY_LIKE`, and `NEUTRAL` on
  playlist tracks; a few **explicit dislikes** on classical/jazz and some
  **neutral** electronic tracks outside the core blend—signals breadth without
  collapsing onto one feature.
- **`module4_*.json`**: Trained from this persona’s playlist + ratings; weights
  should tilt toward their genres/moods while still reflecting mixed labels.

## Demo tips

Try **two different seed songs** (one “party”, one “chill”) to show how the
same user still gets coherent but varied candidate pools.
