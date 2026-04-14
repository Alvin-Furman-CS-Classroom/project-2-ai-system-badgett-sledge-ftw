# Persona: Omnivore indie (flagship diversity demo)

## Intent

A **deliberately wide** but still curated listener: alternative, electronic,
jazz, and folk/country flavors in one profile. Maximizes **spread in KB
features** so Module 5-style diversification has multiple natural groups.

## How the files encode this

- **`user_profile.json`**: Four **distinct** genre codes plus mixed moods
  (`relaxed`, `electronic`, `happy`).
- **`user_playlists.json`**: Roughly **equal quarters** from four genres—by
  construction, the playlist is multi-modal.
- **`user_ratings.json`**: Mostly positive labels across lanes; light negatives
  on rare/unwanted buckets; extra neutrals on pop—avoids a single-cluster
  collapse.
- **`module4_*.json`**: Should assign positive mass across several genre/mood
  features.

## Demo tips

Best persona to show **“same user, visibly different recommendation clusters”**
after Module 5. Before that, still shows varied top-K under search + ML.
