# Module Planning: Music Recommendation System

## System Theme
A music recommendation system that takes Spotify data and finds similar songs, using features like artist, tempo, genre, featured artists, writers, and producers. The system learns from your playlists and can find unpopular music that matches your preferences. The goal is for this to be as broad as possible. Spotify's custom playlists are good, but after some time, they begin repeating the same known songs. I want the selection to be more curated, as if a DJ was putting together a setlist while keeping the above features in mind.

## Proposed Module Order & Topics

### Module 1: Data Aggregation and Knowledge Base Construction
**Topic:** Knowledge Representation / Data Processing

**Purpose:** Extract and aggregate features from Spotify data (tempo, genre, artist, featured artists, writers, producers, language) and create a structured knowledge base. This module focuses on data collection, cleaning, and organizing information into queryable facts and relations.

**Input:** Raw Spotify song data (metadata, audio features, credits)

**Output:** Structured knowledge base with facts/relations (e.g., `has_tempo(song, bpm)`, `has_genre(song, genre)`, `produced_by(song, producer)`)

**Integration:** Provides the foundational data structure that all subsequent modules query and use.

**Prerequisites:** Knowledge Representation basics, data structures

---

### Module 2: Rule-Based Preference Encoding
**Topic:** Propositional Logic / Heuristic Design

**Purpose:** Encode user preferences as explicit rules and heuristics. User provides weights/priorities for features (via questionnaire or direct input), and the system creates logical rules (e.g., "IF tempo within range X AND genre matches THEN high priority"). This replaces ML-based learning for early checkpoints.

**Input:** Knowledge base from Module 1, user-provided feature weights/preferences

**Output:** Rule-based preference system (logical rules + weight vectors) for scoring songs

**Integration:** Provides the preference model that Module 3 (Search) uses to evaluate songs. Later, Module 4 (ML) can learn to refine these weights.

**Prerequisites:** Propositional Logic, Knowledge Base from Module 1

---

### Module 3: Search Over Knowledge Base
**Topic:** Search (Uniform Cost, A*, Beam Search, etc.)

**Purpose:** Search through the knowledge base to find similar songs using rule-based preferences from Module 2. The search explicitly avoids popularity bias by treating all songs equally in the search space. Uses path cost based on feature matching (tempo difference, genre match, shared collaborators, etc.).

**Input:** Knowledge base from Module 1, rule-based preferences from Module 2, query song(s) or preference profile

**Output:** Ranked list of top-K similar songs with similarity scores

**Integration:** Core retrieval mechanism. Results feed into Module 5 (Clustering) for organization, and later Module 4 (ML) can use search results + user feedback to learn better preferences.

**Prerequisites:** Search algorithms (UCS/A*/Beam), state-space formulation, path cost design, Modules 1 and 2

---

### Module 4: Machine Learning from Playlists
**Topic:** Machine Learning (Supervised Learning)

**Purpose:** Learn preference patterns from your playlists to refine the rule-based weights from Module 2. Identifies patterns in tempo preferences, artist connections, genre connections, and other features. Can update or replace the heuristic weights with learned weights.

**Input:** Knowledge base from Module 1, your playlists (positive examples), optionally search results from Module 3 with user feedback

**Output:** Learned preference model (refined weights, or learned scoring function)

**Integration:** Can refine Module 2's rule-based preferences, or be used to re-rank Module 3's search results. Works with Module 5 to improve clustering.

**Prerequisites:** Machine Learning fundamentals, supervised learning, training/optimization, evaluation, Modules 1-3

---

### Module 5: Clustering and Result Organization
**Topic:** Clustering

**Purpose:** Organize search results (from Module 3, potentially re-ranked by Module 4) into diverse groups/clusters to provide variety in recommendations, group similar results together, and ensure recommendations span different styles/languages/genres.

**Input:** Ranked candidates from Module 3 (or re-ranked by Module 4), knowledge base features, learned preferences from Module 4 (optional)

**Output:** Clustered groups of recommendations with diversity across clusters

**Integration:** Final organization step that takes search results and ensures diverse, curated output.

**Prerequisites:** Clustering algorithms, distance metrics, feature scaling, Modules 1-4

---

## Feasibility Study

_A timeline showing that each module's prerequisites align with the course schedule. Verify that you are not planning to implement content before it is taught._

| Module | Required Topic(s) | Checkpoint Due    |
| ------ | ---------------- | -------------------|
| 1      | KR + Data Proc   | 2/11 Checkpoint 1  |
| 2      | Propositional Logic |2/26 Checkpoint 2|
| 3      | Search (UCS/A*)  | 3/19 Checkpoint 3  |
| 4      | ML (Supervised)  | 4/2 Checkpoint 4   |
| 5      | Clustering       | 4/16 Checkpoint 5  |

**Legend (what each "Required Topic(s)" means):**
- **KR + Data Proc**: knowledge representation (facts/relations); data aggregation/processing; basic data structures
- **Propositional Logic**: logical rules; rule encoding; heuristic design; IF-THEN rules for preferences
- **Search (UCS/A*)**: state-space formulation; path cost; UCS/A*/Beam (whatever you pick); heuristic design (if A*); complexity tradeoffs
- **ML (Supervised)**: feature/label setup from playlists; training/optimization; basic evaluation (moved to later checkpoint)
- **Clustering**: k-means/hierarchical/etc. (as covered); distance metrics; feature scaling/normalization; cluster evaluation

## Coverage Rationale

_Brief justification for your choice of topics. Why do these topics fit your theme? What trade-offs did you consider?_

The system is structured to work with rule-based methods early (Modules 1-3) and introduce machine learning later (Module 4) to align with the course schedule. **Knowledge Representation** (Module 1) provides the foundation for organizing Spotify data into queryable facts. **Propositional Logic** (Module 2) allows explicit, interpretable preference encoding via user-provided weights and rules, which is essential for early checkpoints before ML is covered. **Search** (Module 3) is the core retrieval mechanism that can work with rule-based preferences immediately, and explicitly avoids popularity bias by treating all songs equally in the search space. **Machine Learning** (Module 4, moved later) learns from playlists to refine the rule-based preferences, providing a hybrid approach that combines interpretability with learned patterns. **Clustering** (Module 5) ensures diverse, curated recommendations.

**Trade-offs considered:** Moving ML later means early modules rely on user-provided weights rather than learned preferences, but this makes the system feasible for early checkpoints. The rule-based approach also provides explainability ("recommended because tempo matches AND shares producer"), which complements the later ML refinement. The focus on data aggregation and search early aligns with the feedback to emphasize these aspects before introducing learning.
