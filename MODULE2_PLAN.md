# Module 2: Rule-Based Preference System (Survey + Song Ratings)

## Goal

Deliver a **rule-based preference system** (logical rules + weight vectors) that scores songs using the existing knowledge base. Input is **(1) survey answers** and **(2) user ratings on a sample of songs** from the KB. Ratings are used to refine weights (and optionally to boost songs similar to highly-rated ones). Module 3 will consume this system to rank candidates.

## Current Foundation

- **Knowledge base** (`[src/knowledge_base_wrapper.py](src/knowledge_base_wrapper.py)`): exposes `get_fact(fact_type, mbid)`, `songs_by_*`, `songs_in_loudness_range`, and indexes for `has_genre`, `has_loudness`, `has_danceable`, `has_voice_instrumental`, `has_timbre`, `has_mood`.
- **Facts** (from `[unit_tests/fixtures/test_knowledge_base.json](unit_tests/fixtures/test_knowledge_base.json)`): genre (list), loudness (float), danceable (categorical), voice_instrumental (categorical), timbre (categorical), mood (list).
- **Demo preview** (`[presentation/queries.py](presentation/queries.py)` `demo_3_rule_based_preferences`): illustrates IF genre AND danceable AND mood style rules; no scoring yet.

## 1. Survey Design (Questions → KB Features)

Define a small **survey schema**: each question id, prompt text, type (multi-choice / range / multi-select), and mapping to KB fact(s) and value(s).

**Suggested questions (align with KB facts):**


| Survey question / concept        | KB fact(s)               | Allowed values / range          |
| -------------------------------- | ------------------------ | ------------------------------- |
| Preferred genres (multi-select)  | `has_genre`              | from `kb.get_all_genres()`      |
| Preferred mood(s) (multi-select) | `has_mood`               | from `kb.get_all_moods()`       |
| Danceability                     | `has_danceable`          | danceable / not_danceable / any |
| Voice vs instrumental            | `has_voice_instrumental` | voice / instrumental / any      |
| Timbre                           | `has_timbre`             | bright / dark / any             |
| Loudness range                   | `has_loudness`           | min_db, max_db (e.g. -15 to -5) |


Survey **output**: a single structured object (e.g. dict or dataclass) holding user choices (e.g. `preferred_genres: List[str]`, `preferred_moods: List[str]`, `danceable: str`, `voice_instrumental: str`, `timbre: str`, `loudness_min: float`, `loudness_max: float`). This is the **preference profile** input to the rule/weight system.

**Implementation note:** Survey can be implemented as (a) a static config (e.g. JSON or Python dict) that defines questions and allowed values, plus (b) a function or small script that collects answers (CLI prompts or later a simple UI) and returns the preference profile. For checkpoint, CLI or hardcoded profile is enough; no need for a full web survey.

## 2. Song Sampling and User Ratings (Post-Survey)

After the user completes the survey:

- **Sample songs from the KB**: Select a fixed number of songs (e.g. 10–20) to show the user. Options: (a) random sample, (b) stratified (e.g. cover multiple genres/moods so the user sees variety), or (c) top-K by initial rule-based score so they are relevant to the profile. Stratified or score-based sampling gives more informative ratings.
- **Present the list**: Show each song's artist and track (and optionally a few KB facts) so the user can rate them. Data comes from `kb.get_song(mbid)` and optionally `kb.get_fact(...)`.
- **Collect ratings**: User rates how much they like each song. Simple scheme: numeric scale (e.g. 1–5) or like / neutral / dislike. Store as a list of `(mbid, rating)` pairs (e.g. `UserRatings` or list of tuples).
- **Persistence**: Keep ratings in memory for the session; optionally save/load (e.g. JSON) so the same user can reuse them without re-rating.

This list of **rated songs** is a second input to the preference system and is used in the next step to refine weights (and optionally in scoring).

## 3. Data Model: Preference Profile, Rules, Weight Vector, Ratings

- **Preference profile**: holds raw survey answers (preferred genres, moods, danceable, voice_instrumental, timbre, loudness range). Stored as a single object (e.g. `PreferenceProfile` dataclass or typed dict).
- **Logical rules**: each rule is a **condition** over KB facts plus an optional **label/priority**. Prefer a simple, evaluatable representation, e.g.:
  - **Condition**: "genre in preferred_genres", "mood in preferred_moods", "danceable == preference", "voice_instrumental == preference", "timbre == preference", "loudness in [min, max]".
  - Stored as a list of rule objects (e.g. `Rule(condition_type, fact_type, target_value(s))`) or equivalent dicts.
- **Weight vector**: one weight per rule or per **feature dimension** (e.g. `genre_weight`, `mood_weight`, `danceable_weight`, …). Non-negative floats; can be normalized to sum to 1 or left as-is and used in a weighted sum. Stored as a dict mapping rule id or feature name to float.

**Build step:** From a **preference profile** (survey answers), the system **builds** the set of logical rules and an **initial** weight vector (e.g. equal weights).

- **User ratings**: A list (or dict) of `(mbid, rating)` for the sampled songs. Ratings are used to **refine the weight vector** (see below) and optionally to add a "similarity to highly-rated songs" term to the score.

**Incorporating ratings into the preference system (rule-based, no ML):**

- **Weight refinement**: For each rated song, compute which rules it satisfies (using the KB). Then:
  - **High-rated songs**: Increase the weights of the rules they satisfy (e.g. small positive delta or multiplicative boost), so that future songs satisfying those rules score higher.
  - **Low-rated songs**: Decrease the weights of the rules they satisfy (or increase weights of rules they *don't* satisfy), so that songs like them score lower.
  - Implementation: one pass over rated songs; for each rule, compute average rating of songs that satisfy it vs. don't; adjust that rule's weight accordingly (e.g. rule weight += alpha * (avg_rating_satisfied - avg_rating_overall)). Keep weights non-negative (e.g. clamp or use a small floor).
- **Optional similarity term**: Add a second component to the score: for each candidate song, compute a "similarity to highly-rated songs" (e.g. fraction of shared genre/mood, or inverse distance in loudness). Blend with the rule-based score: `final_score = (1 - beta) * rule_score + beta * similarity_to_rated`. This stays rule-based if similarity is defined only on KB features (no learned embeddings). For minimal scope, weight refinement alone is enough; similarity can be added if time permits.

## 4. Rule Evaluation and Scoring

- **Rule evaluation**: For a given song (mbid) and KB, evaluate each rule (true/false or partial score). Use existing `KnowledgeBase` API: `get_fact`, `songs_by_*`, `songs_in_loudness_range`. For "genre in preferred", check intersection of song's `has_genre` with profile's preferred genres; for "mood in preferred", same with `has_mood`. For numeric loudness, check if song's loudness is in [min, max].
- **Scoring**: Combine rule outcomes with the weight vector. Simple approach: **weighted sum** of rule scores (e.g. 1.0 if rule satisfied, 0.0 otherwise). Optional: partial scores for genre/mood (e.g. fraction of preferred genres that match). Output a single **score** per song (float).
- **API**: One clear entry point for Module 3, e.g.  
`score(song_mbid: str, kb: KnowledgeBase) -> float`  
and optionally  
`score_all(song_mbids: List[str], kb: KnowledgeBase) -> List[Tuple[str, float]]`  
or a method on a `PreferenceSystem` / `RuleBasedScorer` class that holds the profile, rules, weights, and (optionally) the refined weights after applying ratings.

## 5. Code Layout

- **New package under `src/`**: e.g. `src/preferences/` (or `src/rule_based_preferences/`).
  - `survey.py` (or `survey_schema.py`): survey question definitions and allowed values; function to build a `PreferenceProfile` from answers (e.g. from dict or CLI).
  - `profile.py`: `PreferenceProfile` (survey answers) and possibly validation (e.g. loudness_min <= loudness_max, allowed categories).
  - `rules.py`: rule representation (condition types, target values) and **building** rules from a `PreferenceProfile` (e.g. one rule per feature: genre match, mood match, danceable match, etc.).
  - `weights.py` or inside `rules.py`: weight vector definition and default weights (equal or configurable).
  - `scorer.py`: class that holds rules + weights (refined by ratings if provided), takes KB in constructor or `score(song_mbid, kb)`, and returns float; optionally `score_all` for batch.
  - `sampling.py`: function to select N songs from the KB for rating (random, stratified, or by initial score). Returns list of mbids.
  - `ratings.py`: data structure for user ratings `(mbid, rating)`; function to apply ratings to refine the weight vector (given KB, rules, current weights, and ratings list).
- **Dependency**: This module **depends only on** the KB interface (`KnowledgeBase` from `src/knowledge_base_wrapper.py`). No dependency on Module 3 or 4.
- **Entry point / demo**: A script that (1) loads KB, (2) runs survey (or loads hardcoded profile), (3) builds initial rules + weights, (4) samples songs and collects ratings (CLI or hardcoded list for demo), (5) refines weights from ratings, (6) runs scorer on a few songs and prints scores. This demonstrates the full flow: survey → ratings → rule-based scoring.

## 6. Flow Diagram

```mermaid
flowchart LR
  subgraph inputs [Inputs]
    Survey[Survey answers]
    KB[Knowledge base Module 1]
  end
  subgraph module2 [Module 2]
    Profile[Preference profile]
    Rules[Logical rules]
    InitialWeights[Initial weight vector]
    Sample[Sample songs from KB]
    Ratings[User ratings]
    RefineWeights[Refine weights from ratings]
    Scorer[Scorer]
  end
  Survey --> Profile
  Profile --> Rules
  Profile --> InitialWeights
  KB --> Sample
  Sample --> Ratings
  Rules --> RefineWeights
  InitialWeights --> RefineWeights
  Ratings --> RefineWeights
  Rules --> Scorer
  RefineWeights --> Scorer
  KB --> Scorer
  Scorer --> Scores["Scores per song"]
```

## 7. Testing

- **Unit tests** (in `unit_tests/preferences/`, mirroring `src/preferences/`):
  - **Profile**: build profile from dict; validation (e.g. loudness range, allowed categories).
  - **Rules**: build rules from a profile; rule structure matches expected condition types.
  - **Weights**: default weight vector; optional custom weights.
  - **Scorer**: with a **fixture KB** (reuse or copy from `unit_tests/fixtures/test_knowledge_base.json`), create a small profile + rules + weights, then assert that:
    - A song that matches all rules gets a higher score than one that matches none.
    - A song that matches genre but not mood gets a score between those two (if weights are positive).
    - Edge cases: song missing a fact (e.g. no mood) → rule for mood yields 0 or "no match"; scorer does not crash.
  - **Sampling**: given KB, request N songs; get N distinct mbids (or fewer if KB is small); optionally assert stratification if implemented.
  - **Ratings and weight refinement**: with fixture KB and a small ratings list (e.g. high rating for a song that satisfies "genre=rock", low for one that doesn't), apply refinement and assert that the "genre" rule weight increases (or that after refinement, a rock song scores higher than before).
- **Integration test** (in `integration_tests/module_2/`): load real or fixture KB, (1) build profile from survey-like input, (2) build rules and initial weights, (3) sample songs and apply mock ratings (e.g. high for some mbids, low for others), (4) refine weights, (5) run scorer on multiple songs. Assert that output is a list of (mbid, score) with sensible ordering and that highly-rated-style songs rank higher after refinement.

## 8. README and AGENTS.md

- **README.md**: Add/update Module 2 row in the module plan table (inputs: KB + survey answers + user ratings on sampled songs; outputs: rule-based preference system = logical rules + weight vectors refined by ratings + scorer). Reference `src/preferences/` and tests.
- **AGENTS.md**: Copy updated module plan; note that Module 2 is "Rule-Based Preference Encoding (survey + song ratings)" and that Module 3 will use the scorer.

## 9. Out of Scope for This Plan

- Playlist-based preference input (deferred to Module 4).
- ML-based learning or tuning (Module 4); weight refinement here is a simple rule-based update from ratings (e.g. average rating per rule).
- Search implementation (Module 3); only the **scoring API** that Module 3 will call needs to be defined and tested.

## Summary of Deliverables

| Deliverable        | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| Survey schema      | Questions and mapping to KB facts; way to produce a preference profile.    |
| Preference profile | Data structure for survey answers.                                         |
| Song sampling      | Select N songs from KB for rating (random or stratified).                  |
| User ratings       | Data structure and collection for (mbid, rating); optional save/load.      |
| Logical rules      | Representation and construction from profile; evaluatable against KB.     |
| Weight vector      | Initial (from survey) and refined (from ratings); per-rule or per-feature. |
| Weight refinement  | Update weights using which rules each rated song satisfies and its rating. |
| Scorer             | `score(mbid, kb) -> float` (and optionally batch) using refined weights.   |
| Unit tests         | Profile, rules, weights, sampling, refinement, scorer with fixture KB.     |
| Integration test   | End-to-end: survey → profile → rules → sample → ratings → refine → scores. |
| Demo               | Script: survey (or hardcoded profile) → sample → ratings → refined scores. |
| Docs               | README/AGENTS.md module spec and layout.                                   |
