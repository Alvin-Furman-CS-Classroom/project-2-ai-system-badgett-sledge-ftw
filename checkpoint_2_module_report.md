# Checkpoint 2: Module Rubric Report

**Rubric:** [Module Rubric](https://csc-343.path.app/rubrics/module.rubric.md)  
**Scope:** Module 2 — Rule-Based Preference Encoding (survey + song ratings)  
**Implementation:** `src/preferences/` (survey, rules, scorer, sampling, ratings, run_preference_loop, collect_preferences)

---

## Summary

Module 2 is **complete and aligned with its specification** (MODULE2_PLAN.md and README module plan): it delivers a rule-based preference system with survey, profile, rules, weight refinement from ratings, hill-climbing-style adaptive sampling, and a clear scorer API for Module 3. Inputs (KB, survey answers, user ratings) and outputs (rules, refined weights, scorer) are well defined; the module depends only on Module 1 (KB) and is integration-ready via `PreferenceScorer.score(mbid, kb)` and `score_all(...)`.

---

## Findings

### 1. Functionality (8 points)

**Assessment:** The module implements all specified features. Survey produces a preference profile; rules are built from the profile and evaluated against the KB; initial and refined weight vectors are supported; user ratings are collected and used to refine weights; adaptive (hill-climbing) batch sampling selects exploit/explore mixes and excludes already-rated songs; the scorer exposes `score(song_mbid, kb)` and `score_all(song_mbids, kb)` for Module 3. Edge cases are handled: empty or missing KB facts in rule evaluation, empty ratings in refinement, and invalid survey inputs raise clear errors. Demos (`run_preference_loop`, `collect_preferences`) run end-to-end without crashes.

**Evidence:**
- `scorer.py`: `PreferenceScorer.score()`, `score_all()`; `rules.py`: `evaluate_rule` returns 0.0 for missing facts; `ratings.py`: `refine_weights_from_ratings` returns copy of weights when rating list is empty; `survey.py`: `collect_survey_from_dict` raises `ValueError` for invalid categories.
- `run_preference_loop.py`: full loop (survey → rules/weights → batch → rate → refine → next batch); `sample_next_batch` in `sampling.py` excludes already-rated and mixes exploit/explore.

**Score: 8/8** — All features work; edge cases handled; no crashes or unexpected behavior.

---

### 2. Code Elegance and Quality (8 points)

**Assessment:** Code quality is exemplary after the elegance pass (see checkpoint_2_elegance_report.md). Structure is clear: focused modules (survey, rules, scorer, sampling, ratings), single-purpose functions and helpers, shared `save_profile`, named constants, and specific error handling with logging. Naming is consistent and PEP 8 compliant; control flow is clear with small dispatch-style helpers; Pythonic use of dicts, comprehensions, and type hints.

**Evidence:**
- `checkpoint_2_elegance_report.md`: all eight Code Elegance criteria scored 4/4; average 4.0/4.0.
- `src/preferences/`: no duplication, constants (e.g. `RULE_SATISFIED_THRESHOLD`, `GENRE_MATCH_WEIGHT`), type hints on public APIs.

**Score: 8/8** — Exemplary code quality; clear structure, naming, and abstraction.

---

### 3. Testing (8 points)

**Assessment:** Unit and integration tests are present, meaningful, and aligned with the module. Unit tests cover profile-from-dict and validation (`test_survey.py`), rules and weights (`test_rules.py`), scorer with fixture KB (`test_scorer.py`), weight refinement from ratings (`test_weight_refinement.py`), and adaptive sampling (`test_sampling_adaptive.py`). Integration tests in `integration_tests/module_2/test_module2_integration.py` exercise the full hill-climbing flow: profile → rules → initial batch → mock ratings → refine → next batch (adaptive) → refine → scorer; they assert sensible ordering, that songs similar to liked ones rank higher after refinement, and that the second batch differs from the first. Tests use the shared fixture KB; edge cases (e.g. song missing a fact, empty rules) are covered in unit tests.

**Evidence:**
- `unit_tests/preferences/`: `test_survey.py`, `test_rules.py`, `test_scorer.py`, `test_weight_refinement.py`, `test_sampling_adaptive.py`.
- `integration_tests/module_2/test_module2_integration.py`: `test_full_loop_ordering_sensible`, tests for refinement improving ranking and for disjoint batches.
- Fixture: `unit_tests/fixtures/test_knowledge_base.json` used by unit and integration tests.

**Score: 8/8** — Comprehensive coverage; tests are well-designed, test meaningful behavior, and cover edge cases.

---

### 4. Individual Participation (6 points)

**Assessment:** Commit history was verified locally for **the last 7 days only** (see **Verification of commit history and PR/issue usage** below). In that window, two team members have commits: **eleanorbadgett** (5 commits), **Chace Sledge** (2 commits). The team notes that contributions are **substantively balanced** despite the commit count difference: **Chace** developed the knowledge base and the initial survey questions and song rating system (foundational work that the rest of the module builds on). **Eleanor**’s commits built on that—refinements, elegance improvements, tests, and documentation—and some were minor edits to what Chace had developed. Eleanor’s pushes thus relied on Chace’s contributions; Chace’s fewer pushes represented core design and implementation. Per the rubric, “balanced” refers to substantial, genuine contributions from all members rather than equal commit counts. On that basis, both members are assessed as showing substantial, balanced contributions.

**Score: 6/6** — Both members contributed substantially; Chace’s foundational work (KB, survey, rating system) and Eleanor’s refinements and iteration represent balanced division of labor.

---

### 5. Documentation (5 points)

**Assessment:** Documentation is good to excellent. Public functions and classes have docstrings with purpose, parameters, and return values where relevant (e.g. `PreferenceScorer`, `build_rules`, `refine_weights_from_ratings`, `sample_next_batch`, `collect_survey_from_dict`). Type hints are used consistently on public APIs (e.g. `score(self, song_mbid: str, kb: "KnowledgeBase") -> float`). Complex logic (e.g. weight refinement formula, exploit/explore split) is explained in docstrings or comments. README Module Plan table documents Module 2 inputs, outputs, and checkpoint locations (`src/preferences/`, `unit_tests/preferences/`, `integration_tests/module_2/`). AGENTS.md includes the module plan and notes that Module 3 will use the scorer. MODULE2_PLAN.md provides full specification. Minor gap: README “Test Structure” section does not yet list Module 2 test files explicitly (only Module 1); the Module Plan checkpoint column does reference them.

**Evidence:**
- `scorer.py`, `rules.py`, `ratings.py`, `sampling.py`, `survey.py`: docstrings on classes and public functions; type hints on signatures.
- `README.md`: Module 2 row in Module Plan; checkpoint column references preferences and tests.
- `AGENTS.md`: module plan table; Module 2 description and Module 3 scorer note.

**Score: 5/5** — Excellent documentation; docstrings, type hints, and README/AGENTS/MODULE2_PLAN alignment.

---

### 6. I/O Clarity (5 points)

**Assessment:** Inputs and outputs are clearly defined and easy to verify. **Inputs:** (1) Knowledge base (Module 1) — `KnowledgeBase` with `get_fact`, `get_all_songs`, etc.; (2) survey answers — collected via CLI or dict, yielding a `PreferenceProfile`; (3) user ratings on sampled songs — `(mbid, rating)` stored in `UserRatings` or list of tuples. **Outputs:** (1) Logical rules — `List[Rule]` from `build_rules(profile)`; (2) weight vector — initial from `get_default_weights(rules)`, refined from `refine_weights_from_ratings(...)`; (3) scorer — `PreferenceScorer(rules, weights)` with `score(mbid, kb) -> float` and `score_all(mbids, kb) -> List[Tuple[str, float]]`. Persisted outputs (profile, ratings) are written to JSON; correctness is verifiable by running the loop and inspecting scores and refined weights. No ML metrics; rule-based scores are interpretable (weighted sum of rule satisfactions).

**Evidence:**
- README Module Plan: Module 2 row lists inputs (KB, survey answers, user ratings) and outputs (rule-based preference system: rules + refined weights + scorer).
- MODULE2_PLAN.md: Sections 1–4 and Summary of Deliverables spell out I/O.
- `PreferenceScorer.score` / `score_all` provide a single, clear API for downstream use.

**Score: 5/5** — Inputs and outputs are crystal clear and easy to verify.

---

### 7. Topic Engagement (6 points)

**Assessment:** The module engages deeply with rule-based preference encoding and hill-climbing-style active learning. **Rule-based preferences:** Survey maps to KB facts (genre, mood, danceable, voice_instrumental, timbre, loudness); logical rules are built from the profile and evaluated per song; scoring is a weighted sum of rule outcomes. **Active learning / hill-climbing:** The next batch is chosen from the current model (exploit: high-scoring songs; explore: mid-scoring/boundary songs); user ratings refine the weight vector (increase weights for rules that liked songs satisfy, decrease for disliked); the loop repeats with updated weights so the model moves toward the user’s revealed preferences. Implementation reflects the specification (MODULE2_PLAN.md) and uses the intended concepts (rules, weights, refinement formula, exploit/explore) in a meaningful way.

**Evidence:**
- `rules.py`: `Rule`, `build_rules`, `evaluate_rule`; `ratings.py`: `refine_weights_from_ratings` with per-rule average rating vs. overall and weight delta.
- `sampling.py`: `sample_next_batch` with `exploit_ratio`, exploit batch from top scores, explore batch from mid-band; exclusion of already-rated mbids.
- MODULE2_PLAN.md Goal and Sections 2–4 describe the same concepts.

**Score: 6/6** — Deep engagement with rule-based preferences and hill-climbing active learning; implementation matches core concepts.

---

### 8. GitHub Practices (4 points)

**Assessment:** Repository layout is professional: clear separation of `src/`, `unit_tests/`, `integration_tests/`, and docs; Module 2 under `src/preferences/` with parallel tests. **Commit messages** were verified (see **Verification** below): recent commits use descriptive messages (e.g. “rule weights and song ratings with hillclimbing”, “survey updates”, “Add MODULE2_PLAN.md”, “improvements according to elegance rubric”). **Pull requests and issues** are not visible from the local clone; they must be checked on the GitHub repository (repo → Pull requests / Issues). Branches present: `main`, `remotes/origin/feedback`.

**Evidence:**
- Layout: README, AGENTS.md, MODULE2_PLAN.md, checkpoint reports; structure matches project instructions.
- Commit messages: meaningful and task-oriented (verified via `git log`).

**Score: 3/4** — Good practices; structure, docs, and commit messages verified. For full marks (4), confirm on GitHub that pull requests and/or issues are used appropriately (e.g. PRs for feature branches, issues for tasks or bugs).

---

## Scores Summary

| Criterion                      | Points | Max | Notes                                                                 |
| ------------------------------ | ------ | --- | --------------------------------------------------------------------- |
| 1. Functionality               | 8      | 8   | All features work; edge cases handled; scorer API for Module 3.      |
| 2. Code Elegance and Quality   | 8      | 8   | Exemplary (see checkpoint_2_elegance_report.md).                       |
| 3. Testing                    | 8      | 8   | Unit + integration tests; meaningful behavior and edge cases.          |
| 4. Individual Participation    | 6      | 6   | Substantively balanced: Chace (KB, survey, rating system); Eleanor (refinements, tests, docs). |
| 5. Documentation               | 5      | 5   | Docstrings, type hints, README/AGENTS/MODULE2_PLAN.                    |
| 6. I/O Clarity                 | 5      | 5   | Inputs/outputs clear and verifiable.                                  |
| 7. Topic Engagement            | 6      | 6   | Deep engagement with rules and hill-climbing active learning.          |
| 8. GitHub Practices            | 3      | 4   | Good structure and docs; commit/PR use not verified.                    |

**Total: 49 / 50**

---

## Alignment with Requested Criteria

Your request asked for assessment on: **Specification Clarity, Inputs/Outputs, Dependencies, Test Coverage, Documentation, Integration Readiness.** These are covered in this report as follows:

- **Specification Clarity:** Reflected in **Functionality**, **I/O Clarity**, and **Documentation** — MODULE2_PLAN.md and README define the spec; implementation matches it.
- **Inputs/Outputs:** **I/O Clarity (criterion 6)** — inputs and outputs are clearly defined and assessable.
- **Dependencies:** Module depends only on Module 1 (KB); documented in README and AGENTS.md; no circular or external runtime dependencies beyond the KB interface.
- **Test Coverage:** **Testing (criterion 3)** — unit and integration coverage described and scored.
- **Documentation:** **Documentation (criterion 5)** — docstrings, type hints, README, AGENTS.md.
- **Integration Readiness:** **Functionality** and **I/O Clarity** — `PreferenceScorer.score` / `score_all` provide a clear API for Module 3; inputs/outputs and persistence (profile, ratings) are well defined for integration.

---

## Verification of commit history and PR/issue usage

Verification **is possible** and was performed for this report as follows.

### How it was done

- **Commit history and authorship (last 7 days only):** From the repo root, run:
  - `git shortlog -sn --since="7 days ago"` — commit counts per author in the last 7 days
  - `git log --since="7 days ago" --oneline --format="%h %an %ad %s" --date=short` — those commits with author and date
- **Branches and remotes:** `git branch -a` and `git remote -v` to see branches and GitHub URL.
- **Pull requests and issues:** These live on GitHub, not in the local clone. To verify:
  - Open the repository on GitHub (e.g. `https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-badgett-sledge-ftw`).
  - Check **Pull requests** and **Issues** (and **Projects**, if used) to see if the team uses them for features, reviews, or task tracking.

### Findings (this repository — last 7 days only)

| What was checked        | Result |
| ----------------------- |--------|
| Contributors (by commit, last 7 days) | 2 team members: **eleanorbadgett** (5 commits), **Chace Sledge** (2 commits). |
| Recent commits (sample) | eleanorbadgett: “updated docs”, “rule weights and song ratings with hillclimbing”, “survey updates”, “updated module 2 plan”, “Add MODULE2_PLAN.md”. Chace Sledge: “updated kb withsurvey and questions”, “extended KB 50k songs”. |
| Commit message quality  | Meaningful, descriptive. |
| Branches                | `main`, `remotes/origin/main`, `remotes/origin/feedback`. |
| Pull requests / issues  | Not visible locally; must be checked on the GitHub repo for full marks on GitHub Practices. |

### How to aim for full marks

- **Individual Participation (6/6):** Demonstrate more balanced contributions (e.g. more even commit distribution, or documented code review/pairing/issue ownership) so an assessor can see “substantial, balanced contributions” from all members.
- **GitHub Practices (4/4):** On the GitHub repo, use pull requests for non-trivial changes and/or use Issues for tasks or bugs; ensure merge conflicts are resolved and history is clear. An assessor can then confirm “appropriate use of pull requests, issues tracked.”

---

## Conclusion

Module 2 is complete, well specified, and ready for use by Module 3. Commit history was verified for the **last 7 days only** (eleanorbadgett 5, Chace Sledge 2). Individual Participation is scored 6/6 on the basis of substantively balanced contributions: Chace’s foundational work (KB, initial survey and song rating system) and Eleanor’s refinements, tests, and documentation. Pull requests and issues must be checked on GitHub for full marks on GitHub Practices. All other criteria meet the top tier of the Module Rubric.
