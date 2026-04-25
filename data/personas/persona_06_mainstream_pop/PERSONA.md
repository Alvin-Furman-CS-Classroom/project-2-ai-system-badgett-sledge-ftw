# Persona: Mainstream pop purist (accuracy demo)

## Intent

**Chart- and radio-style pop** listener: vocal, upbeat, hooks-first. Like the
old metal slot, this is a **narrow-lane accuracy** persona—but the KB has
**thousands** of `pop` tracks, so search and learning behave reliably.

## How the files encode this

- **`user_profile.json`**: **Only** `pop` as preferred genre; moods `happy`,
  `party`, `relaxed`; **danceable**, **voice**, **bright** timbre; **moderate**
  loudness band—roughly “Top 40 energy without the trap-maximalist extreme.”
- **`user_playlists.json`**: Long playlist drawn **entirely** from the `pop`
  genre index for strong positive supervision.
- **`user_ratings.json`**: **Accuracy-style**—mostly `REALLY_LIKE`/`LIKE` on
  playlist tracks; **dislikes** on classical, hip-hop, and rock samples to
  sharpen boundaries vs other demos; a couple **neutral** R&B tracks (often
  overlaps radio pop) so labels are not cartoonishly pure.
- **`module4_*.json`**: Should emphasize `genre:pop` and party/happy-adjacent
  features for this user.

## Demo tips

Contrast with **persona 4** (hip-hop + electronic party) and **persona 1**
(multi-genre commuter): same “mainstream” aisle, different genre centers.
