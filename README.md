# Curated Music Recommendation System (Project 2 AI System)

## Overview

This system recommends music in a **curated, setlist-style** way: it uses structured song data and explicit user preferences to find tracks that fit a listener’s taste without relying on popularity alone. The unifying theme is a **hybrid pipeline**: a **knowledge base (Module 1)** stores queryable facts about songs (genre, mood, loudness, danceability, and related metadata). **Rule-based preferences (Module 2)** encode what the user wants using survey answers and ratings, producing a weighted **PreferenceScorer**. **Search over the KB (Module 3)** treats songs as a graph: neighbors come from shared indexes (genre, mood, etc.), edge costs measure feature dissimilarity, and **Uniform Cost Search** (with an optional **beam search** variant) finds top-K candidates from a **query song**; results are blended with preference scores via **`find_similar`**. **Supervised learning from playlists (Module 4)** refines weights or re-ranks results using learned feature weights. **Clustering (Module 5)** optionally organizes retrieval candidates into diverse groups (K-means on KB-derived features, round-robin serving). Together, the modules form a single AI system aligned with the course schedule: interpretable rules and search first, then learning and organization.

## Team

- Eleanor Badgett  
- Chace Sledge  

## Proposal

- **Course project:** [AI System — Project 2 instructions](https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md)  
- **Module planning & theme (detailed):** see [`MODULES.md`](MODULES.md) (music recommendation using Spotify-style data, broad coverage, DJ-like curation, emphasis on features over chart popularity).

## Module Plan

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Knowledge Representation / Data Processing — KB construction | Raw song data (metadata, audio features, credits) | Structured KB: `songs`, `facts`, `indexes` (e.g. `has_genre`, `has_mood`, `has_loudness`) | — | `src/knowledge_base_wrapper.py`, `src/data_acquisition/`; `unit_tests/knowledge_base_wrapper_test.py`, `unit_tests/data_acquisition/` |
| 2 | Rule-Based Preference Encoding (survey + song ratings) | KB (Module 1), survey answers, user ratings on sampled songs | Rule-based preference system: logical rules + weight vectors refined by ratings + scorer | Module 1 (KB) | `src/preferences/`; unit tests in `unit_tests/preferences/`; integration tests in `integration_tests/module_2/` |
| 3 | Search over KB (UCS, beam, path costs, preference blend) | KB (Module 1), `PreferenceScorer` (Module 2), query song MBID | Top-K `SearchResult` list via `find_similar` (UCS; optional `beam_topk`) | Modules 1–2 | `src/search/`; unit tests in `unit_tests/search/`; integration tests in `integration_tests/module_3/` |
| 4 | Machine Learning (supervised) | KB, playlists (positive examples), `data/user_ratings.json` | Learned preference model (feature weights + `LearnedPreferenceScorer` that can rerank Module 3 results) | Modules 1–3 | `src/ml/`; unit tests in `unit_tests/ml/`; integration tests in `integration_tests/module_4/` |
| 5 | Clustering | Ranked candidates from Module 3 (or re-ranked by Module 4), KB features | Diversified top-K via K-means + round-robin across clusters | Modules 1–4 | `src/clustering/`; `unit_tests/clustering/`; `integration_tests/module_5/`; [`MODULE5_PLAN.md`](MODULE5_PLAN.md) |
| 6 (optional) | *(unused or stretch)* | — | — | — | — |

## Repository Layout

```
project-2-ai-system-badgett-sledge-ftw/
├── src/                              # main system source code
│   ├── knowledge_base_wrapper.py     # KB query interface
│   ├── data_acquisition/             # KB building / external data clients
│   ├── preferences/                  # Module 2: survey, rules, scorer, sampling, ratings
│   ├── search/                       # Module 3: costs, graph, UCS, beam, pipeline, query_cli
│   ├── ml/                           # Module 4: dataset, learned scorer, reranker, training
│   └── clustering/                 # Module 5: KB features, K-means, organize / diversify
├── unit_tests/                       # unit tests (parallel structure to src/)
├── integration_tests/                # integration tests (per module beyond Module 1)
├── presentation/                     # optional figures / scripts for module demos (e.g. Module 5 PCA)
├── data/                             # knowledge_base.json, user profile/ratings, personas, etc.
├── .claude/skills/code-review/SKILL.md  # rubric-based agent review
├── AGENTS.md                         # instructions for your LLM agent
├── MODULES.md                        # module planning narrative (theme, feasibility)
└── README.md                         # system overview and checkpoints
```

## Setup

- **Python:** 3.10+ recommended (project tested with Python 3.12).
- **Install dependencies:**

```bash
pip install -r requirements.txt
```

- **Optional:** copy or configure `.env` if you use MusicBrainz API keys or similar (see `src/data_acquisition/` clients).

## Running

- **Tests (full project unit suite):**

```bash
pytest unit_tests/ -v
```

- **Module 2 preference loop / demos:** see `src/preferences/run_preference_loop.py`, `collect_preferences.py` (run from project root with `src` on `PYTHONPATH` or `python -m` as documented in those modules).

- **Module 3 search (library API):** import `find_similar`, `ucs_topk`, or `beam_topk` from `search` after adding `src` to `PYTHONPATH` (same pattern as tests).

- **Module 4 training (offline ML from playlists + ratings):**

  1. Ensure `data/user_ratings.json` exists (e.g., by running `src/preferences/run_preference_loop.py`).
  2. Create `data/user_playlists.json` with the agreed schema:

     ```json
     {
       "playlists": [
         {
           "name": "favorites",
           "mbids": ["<mbid-1>", "<mbid-2>"]
         }
       ]
     }
     ```

  3. Train the Module 4 scorer + reranker artifacts:

     ```bash
     python -m ml.train_module4
     ```

     This writes `data/module4_scorer.json` and `data/module4_reranker.json`.

  4. At recommendation time, wrap the existing `PreferenceScorer`:

     ```python
     from preferences.scorer import PreferenceScorer
     from ml import build_scorer_with_optional_ml
     from search.pipeline import find_similar

     base_scorer = PreferenceScorer(rules, weights)
     scorer = build_scorer_with_optional_ml(base_scorer, "data/module4_scorer.json", blend_weight=0.5)
     results = find_similar(kb, query_mbid, scorer, k=10)
     ```

- **Module 4 interactive demo (Query CLI with ML):**

  After training Module 2 preferences and (optionally) running Module 4 training:

  ```bash
  python src/search/query_cli.py --use-ml-scorer --use-ml-reranker
  ```

- **Module 5 clustering (diversify recommendations):**

  Module 5 is an optional post-retrieval organization step that clusters the top-N
  candidate recommendations (from Module 3, optionally reranked by Module 4) and
  returns a diversified top-K list via round-robin across clusters.

  ```bash
  python src/search/query_cli.py --use-clustering --cluster-k 5 --cluster-pool-size 50
  ```

  This CLI:
  - loads `user_profile.json` and optionally refines rule-based weights from `user_ratings.json`
  - wraps the scorer with Module 4’s learned scorer if `data/module4_scorer.json` exists (when `--use-ml-scorer`)
  - runs Module 3 search (`ucs` or `beam`) to get candidates
  - applies the Module 4 reranker if `data/module4_reranker.json` exists (when `--use-ml-reranker`)
  - optionally applies Module 5 clustering (`--use-clustering`) to diversify the final top-K
  - prints top recommendations with combined, preference, and path-cost scores

## Module 4 Design and Behavior

Module 4 adds a **supervised-learning layer** on top of the rule-based preferences:

- **Labels (what “good” means):**
  - Any song in any playlist in `data/user_playlists.json` is treated as a **base positive**.
  - Ratings in `data/user_ratings.json` refine that signal:
    - `REALLY_LIKE` / `LIKE` → stronger positives.
    - `DISLIKE` → negative, even if the song is in a playlist.
    - `NEUTRAL` → weak/optional signal.
  - Additional negatives come from songs that are rated but not in playlists.

- **Features (what the model looks at):**
  - Derived from the KB via `KnowledgeBase.get_fact(...)`:
    - `genre:*`, `mood:*`, `danceable:*`
    - `voice/instrumental` (`vi:*`), `timbre:*`
    - `loudness_bucket:quiet|medium|loud`
    - a `bias` feature for baseline preference.

- **Learned scorer (how scores are computed):**
  - Training computes, for each feature \(f\):

    \[
    w_f = \text{avg(label | f present)} - \text{global avg label}
    \]

  - At inference, `LearnedPreferenceScorer`:
    - sums \(w_f\) over all features present for a song to get a **learned feature score**,
    - blends it with the existing rule-based score:

    \[
    \text{final} = (1 - \lambda) \cdot \text{rule\_score} + \lambda \cdot \text{learned\_score}
    \]

  - \(\lambda\) (blend weight) defaults to 0.5 in the CLI helper but can be tuned.

- **Reranker (optional second stage):**
  - Module 3’s `find_similar` produces a list of `SearchResult`s (with path cost, preference score, and combined score).
  - The reranker uses the same feature family and learned weights to compute a **reranker score** per candidate and re-orders the list, without changing `find_similar` itself.

This design keeps the system **interpretable** (features and rules are KB-based) while allowing playlists + ratings to statistically adjust which features matter most, and it integrates cleanly with the existing search pipeline and CLIs.

## Testing

**Unit Tests** (`unit_tests/`): Mirror the structure of `src/`. Each module should have corresponding unit tests.

**Integration Tests** (`integration_tests/`): One subfolder per integrated module beyond the first (`module_2/`, `module_3/`, …).

### Running Tests

Install test dependencies:

```bash
pip install -r requirements.txt
```

Run all unit tests:

```bash
pytest unit_tests/ -v
```

Run specific areas:

```bash
pytest unit_tests/knowledge_base_wrapper_test.py -v
pytest unit_tests/data_acquisition/test_build_kb.py -v
pytest unit_tests/preferences/ -v
pytest unit_tests/search/ -v
pytest unit_tests/ml/ -v
pytest unit_tests/clustering/ -v
pytest integration_tests/module_2/ -v
pytest integration_tests/module_3/ -v
pytest integration_tests/module_4/ -v
pytest integration_tests/module_5/ -v
```

Run tests with coverage:

```bash
pytest unit_tests/ --cov=src --cov-report=html
```

### Test Structure

- `unit_tests/knowledge_base_wrapper_test.py`: `KnowledgeBase` class
- `unit_tests/data_acquisition/test_build_kb.py`: KB builder
- `unit_tests/preferences/`: Module 2 (survey, rules, scorer, sampling, ratings)
- `unit_tests/search/`: Module 3 (costs, graph, UCS, beam, pipeline)
- `unit_tests/ml/`: Module 4 (dataset, learned scorer, reranker, artifacts)
- `unit_tests/clustering/`: Module 5 (features, K-means, organize / diversify)
- `integration_tests/module_2/`: end-to-end preference loop + scorer
- `integration_tests/module_3/`: KB + `PreferenceScorer` + `find_similar`
- `integration_tests/module_4/`: train → load → recommend with learned scorer
- `integration_tests/module_5/`: retrieval pool + clustering invariants
- `unit_tests/fixtures/test_knowledge_base.json`: shared KB fixture

### Test Coverage Goals

- Public APIs for `KnowledgeBase`, KB construction, and fact/index consistency
- Module 2: rules, scorer, weight refinement, sampling, survey validation
- Module 3: edge costs, neighbors, UCS, optional beam, pipeline blend with preferences
- Module 4: supervised labels from playlists/ratings, artifact round-trip, optional reranker
- Module 5: KB feature vectors, deterministic K-means, diversified ordering from candidate pools
- Error handling and edge cases for missing KB facts and invalid inputs

## Checkpoint Log

| Checkpoint | Date (course) | Modules Included | Status | Evidence |
| ---------- | -------------- | ---------------- | ------ | -------- |
| 1 | 2026-02-11 | Module 1 — KB / data | Complete | `src/knowledge_base_wrapper.py`, `src/data_acquisition/`; [`MODULE1_PLAN.md`](MODULE1_PLAN.md); unit tests under `unit_tests/data_acquisition/`, `knowledge_base_wrapper_test.py` |
| 2 | 2026-02-26 | Module 2 — Preferences | Complete | `src/preferences/`; [`MODULE2_PLAN.md`](MODULE2_PLAN.md); [`checkpoint_2_module_report.md`](checkpoint_2_module_report.md); `unit_tests/preferences/`; `integration_tests/module_2/` |
| 3 | 2026-03-19 | Module 3 — Search | Complete | `src/search/`; [`MODULE3_PLAN.md`](MODULE3_PLAN.md); [`checkpoint_3_module_report.md`](checkpoint_3_module_report.md); `unit_tests/search/`; `integration_tests/module_3/` |
| 4 | 2026-04-02 | Module 4 — ML | Complete | `src/ml/`; [`MODULE4_PLAN.md`](MODULE4_PLAN.md); [`checkpoint_4_module_report.md`](checkpoint_4_module_report.md); `unit_tests/ml/`; `integration_tests/module_4/`; train: `python -m ml.train_module4`; demo: `python src/search/query_cli.py --use-ml-scorer --use-ml-reranker` |
| 5 | 2026-04-16 | Module 5 — Clustering | Complete | `src/clustering/`; [`MODULE5_PLAN.md`](MODULE5_PLAN.md); [`presentation/module5_cluster_analysis.md`](presentation/module5_cluster_analysis.md); `unit_tests/clustering/`; `integration_tests/module_5/`; demo: `python src/search/query_cli.py --use-clustering --cluster-k 5 --cluster-pool-size 50` |

## Required Workflow (Agent-Guided)

Before each module:

1. Write a short module spec in this README (inputs, outputs, dependencies, tests).
2. Ask the agent to propose a plan in "Plan" mode.
3. Review and edit the plan. You must understand and approve the approach.
4. Implement the module in `src/`.
5. Unit test the module, placing tests in `unit_tests/` (parallel structure to `src/`).
6. For modules beyond the first, add integration tests in `integration_tests/` (new subfolder per module).
7. Run a rubric review using the code-review skill at `.claude/skills/code-review/SKILL.md`.

Keep `AGENTS.md` updated with your module plan, constraints, and links to APIs/data sources.

## References

- **Course:** [Project 2 AI System](https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md), [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md), [Code elegance rubric](https://csc-343.path.app/rubrics/code-elegance.rubric.md)
- **Python libraries:** `requests`, `python-dotenv`, `musicbrainzngs`, `pytest` (see `requirements.txt`)
- **Data / APIs:** Knowledge base derived from curated pipelines in `src/data_acquisition/` (e.g. AcousticBrainz-style features, MusicBrainz metadata); see `data/README.md` and module plans for fact types
