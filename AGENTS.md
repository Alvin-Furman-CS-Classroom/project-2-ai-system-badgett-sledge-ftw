## Project Context

- System title: [Your System Title]
- Theme: [Your Theme]
- Proposal link or summary: [Your Proposal Link or Summary]

**Module plan:**

| Module | Topic(s) | Inputs | Outputs | Depends On |
| ------ | -------- | ------ | ------- | ---------- |
| 1 | (TBD) | — | — | — |
| 2 | Rule-Based Preference Encoding (survey + song ratings) | KB, survey answers, user ratings on sampled songs | Rule-based preference system (rules + refined weights + scorer) | Module 1 (KB) |
| 3 | Search over KB (UCS, graph neighbors, pipeline) | KB, `PreferenceScorer`, query MBID | Ranked similar songs (`find_similar` / `SearchResult`) | Modules 1–2 |

Module 2 is implemented in `src/preferences/` (survey, rules, weights, scorer, sampling, ratings, hill-climbing loop). Tests: `unit_tests/preferences/`, `integration_tests/module_2/`.

Module 3 is implemented in `src/search/` (costs, graph neighbors, UCS, `find_similar` pipeline). Tests: `unit_tests/search/`, `integration_tests/module_3/`.

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
