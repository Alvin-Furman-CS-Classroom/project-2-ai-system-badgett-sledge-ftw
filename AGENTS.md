## Project Context

- System title: Curated Music Recommendation System (Project 2 AI System)
- Theme: DJ-style, feature-rich recommendations over a structured KB; hybrid pipeline: rules + search (Modules 2–3), supervised learning (Module 4), clustering for diversity (Module 5) — see `MODULES.md` and `README.md`.
- Proposal link or summary: [Project 2 instructions](https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md); detailed module theme in [`MODULES.md`](MODULES.md).

**Module plan:**

| Module | Topic(s) | Inputs | Outputs | Depends On |
| ------ | -------- | ------ | ------- | ---------- |
| 1 | KR / data processing — KB | Raw song data, metadata, features | Structured KB (`knowledge_base.json` + indexes) | — |
| 2 | Rule-Based Preference Encoding (survey + song ratings) | KB, survey answers, user ratings on sampled songs | Rule-based preference system (rules + refined weights + scorer) | Module 1 (KB) |
| 3 | Search over KB (UCS, beam, graph neighbors, pipeline) | KB, `PreferenceScorer`, query MBID | Ranked similar songs (`find_similar` / `SearchResult`; optional `beam_topk`) | Modules 1–2 |
| 4 | Machine Learning (supervised) | KB, playlists, `user_ratings.json` | Learned scorer + optional reranker artifacts; `LearnedPreferenceScorer` | Modules 1–3 |
| 5 | Clustering (K-means, diversify) | Ranked candidates from Module 3/4, KB features | Diversified top-K (`cluster_and_organize`; optional in `query_cli`) | Modules 1–4 |

Module 1: `src/knowledge_base_wrapper.py`, `src/data_acquisition/`. Tests: `unit_tests/knowledge_base_wrapper_test.py`, `unit_tests/data_acquisition/`.

Module 2 is implemented in `src/preferences/` (survey, rules, weights, scorer, sampling, ratings, hill-climbing loop). Tests: `unit_tests/preferences/`, `integration_tests/module_2/`.

Module 3 is implemented in `src/search/` (costs, graph neighbors, UCS, beam, `find_similar` pipeline, `query_cli`). Tests: `unit_tests/search/`, `integration_tests/module_3/`.

Module 4 is implemented in `src/ml/` (dataset, learned scorer, reranker, artifacts, `train_module4`). Tests: `unit_tests/ml/`, `integration_tests/module_4/`.

Module 5 is implemented in `src/clustering/` (KB feature vectors, K-means, organize / round-robin diversification). Tests: `unit_tests/clustering/`, `integration_tests/module_5/`. Optional presentation analysis: `presentation/module5_cluster_analysis.md`, `presentation/build_module5_query_pool_union.py`.

## Constraints

- 5-6 modules total, each tied to course topics.
- Each module must have clear inputs/outputs and tests.
- Align module timing with the course schedule.

## How the Agent Should Help

- Draft plans for each module before coding.
- Suggest clean architecture and module boundaries.
- Identify missing tests and edge cases.
- Review work against the rubric using the code-review skill.

## Agent Workflow

1. Ask for the current module spec from `README.md`.
2. Produce a plan (use "Plan" mode if available).
3. Wait for approval before writing or editing code.
4. After implementation, run the code-review skill and list gaps.

## Key References

- Project Instructions: https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md
- Code elegance rubric: https://csc-343.path.app/rubrics/code-elegance.rubric.md
- Course schedule: https://csc-343.path.app/resources/course.schedule.md
- Rubric: https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md
