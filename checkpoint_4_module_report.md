# Checkpoint 4: Module Rubric Report

**Rubric:** [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric)  
**Scope:** Module 4 — Machine Learning from Playlists (learned scorer + reranker)  
**Implementation:** `src/ml/` (`dataset.py`, `artifacts.py`, `learned_scorer.py`, `reranker.py`, `train_module4.py`, `util.py`), unit tests in `unit_tests/ml/`, integration tests in `integration_tests/module_4/`

---

## Summary

Module 4 is implemented as an offline, train-once supervised-learning layer that learns feature weights from playlists + ratings, produces inspectable artifacts, and plugs into the existing Module 2/3 search pipeline without breaking contracts. A learned scorer (`LearnedPreferenceScorer`) wraps the existing `PreferenceScorer` and blends rule-based scores with feature-based scores, while a simple reranker module can apply a second-stage ordering over `SearchResult`s using the same feature family. The module meets the core ML-from-playlists goal and is well-covered by focused unit + integration tests; remaining gaps are mostly around polishing documentation/checkpoint narrative and deciding how prominently to surface the reranker in end-user flows.

---

## Findings

### Critical

- None.

### Major

1. **Module 4 behavior is present but not yet documented in a dedicated checkpoint report or README “story” section**  
   **Evidence:**  
   - `README.md` now has a concise “Module 4 training” subsection (inputs, `python -m ml.train_module4`, and wrapper usage), but there is no narrative description of design choices, limitations, or examples of before/after behavior beyond tests.  
   - `MODULE4_PLAN.md` todos are mostly marked `completed`, but `m4-docs-report` is still `in_progress` and there is no `checkpoint_4_module_report.md` prior to this file.  
   **Impact on rubric:**  
   - Can reduce confidence in Documentation and Topic Engagement, since reviewers rely on checkpoint reports to understand how learning is used and what experiments were run.  
   **Suggested fix:**  
   - Treat this report as the starting point, and add a short “Module 4 design + usage” section to `README.md` (or `MODULE4_PLAN.md`) summarizing: feature set, label scheme, what playlists vs ratings contribute, and how to interpret artifacts.

2. **Reranker is implemented but not wired into any user-facing CLI or demo flow**  
   **Evidence:**  
   - `src/ml/reranker.py` defines `rerank_results_with_artifact(kb, results, artifact)` and there is a `module4_reranker.json` artifact produced by `train_module4.py`.  
   - No CLI or example code path currently calls the reranker; all existing integration tests go through `find_similar` with `LearnedPreferenceScorer`, not a two-stage rerank.  
   **Impact on rubric:**  
   - Functionality and Topic Engagement are still strong (you can point to code + tests), but without a clear usage path it is harder to argue that the reranker is an intentional part of the “curated setlist” story rather than an extra helper.  
   **Suggested fix:**  
   - Add an optional rerank flag/path in the existing search CLI (or a new `query_with_ml_cli`) that:  
     1. Calls `find_similar` to get candidates.  
     2. If `module4_reranker.json` exists, applies `rerank_results_with_artifact`.  
     3. Prints both pre- and post-rerank top-K for illustration.

### Minor

1. **Blend weight λ and feature set are currently “reasonable defaults” but not experimentally justified in docs**  
   **Evidence:**  
   - `LearnedPreferenceScorer` uses a configurable `blend_weight` (λ), and `train_module4.py` uses a hand-designed feature family (genre, mood, danceable, voice/instrumental, timbre, loudness bucket, bias).  
   - Tests check that learned scores can flip rankings and remain numerically sane, but there is no short writeup describing why these λ defaults and feature choices were selected or what trade-offs were considered.  
   **Impact on rubric:**  
   - Slightly weakens Topic Engagement narrative; graders might want to see a sentence or two about why a simple linear feature model is appropriate.  
   **Suggested fix:**  
   - In the checkpoint report or plan file, briefly justify: “we chose a linear feature model and λ≈0.5 for interpretability and to keep scores numerically stable; features mirror the rule dimensions so learned behavior is explainable.”

2. **Module 4 entrypoints rely on manual Python usage rather than a single script that runs all steps**  
   **Evidence:**  
   - Training: `python -m ml.train_module4`.  
   - Recommendation: user must currently construct `PreferenceScorer` + `build_scorer_with_optional_ml` and call `find_similar` in Python.  
   **Impact on rubric:**  
   - Slight friction for Functionality/Documentation; instructors may prefer a minimal CLI to run “collect preferences → train ML → query” in one or two commands.  
   **Suggested fix:**  
   - Add a lightweight CLI (e.g., `src/search/query_with_ml_cli.py`) that takes a query MBID or track/artist name and prints recommendations using ML if artifacts exist.

---

## Rubric Scores

Below scores are on the same per-criterion scale as earlier checkpoints (total out of 50), referencing the [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric).

### 1. Functionality (8 points)

**Assessment:**  
Module 4 delivers the promised supervised-learning behavior: `train_module4.py` reads KB + playlists + ratings, builds training examples, computes feature weights, and writes scorer + reranker artifacts. At inference, `LearnedPreferenceScorer` wraps `PreferenceScorer` without changing Module 2/3 contracts, and the new helper `build_scorer_with_optional_ml` makes ML use optional and safe (falling back when artifacts are missing or invalid). The reranker module can re-order `SearchResult`s based on learned feature weights, and integration tests cover both direct learned scoring and the full train→recommend flow.

**Evidence:**  
- `src/ml/dataset.py`, `train_module4.py`, `learned_scorer.py`, `reranker.py`, `util.py`.  
- `integration_tests/module_4/test_module4_integration.py` (learned scorer flips ranking).  
- `integration_tests/module_4/test_module4_train_flow.py` (train→save→load→recommend).

**Score: 8/8** — Functional goals for Module 4 are met and integrated into the system.

---

### 2. Code Elegance and Quality (8 points)

**Assessment:**  
The ML code follows the same clean, modular style as earlier modules: `dataset.py`, `artifacts.py`, `learned_scorer.py`, `reranker.py`, and `train_module4.py` each have a focused responsibility; helpers are small and typed; and artifact structures are transparent JSON. The choice to keep the learned model linear and feature-based makes the implementation easy to read and reason about. The ML layer respects existing abstractions (e.g., `score(mbid, kb)` interface, `SearchResult` dataclass) and avoids entangling training with inference.

**Evidence:**  
- Clear dataclasses in `artifacts.py` and `dataset.py`.  
- Thin wrapper design in `learned_scorer.py` and the `build_scorer_with_optional_ml` helper.  
- Separation of training entrypoint (`train_module4.py`) from runtime scoring.

**Score: 8/8** — Code quality is strong and consistent with earlier modules.

---

### 3. Testing (8 points)

**Assessment:**  
Module 4 has solid unit and integration coverage: dataset construction, artifact save/load, learned scorer blend behavior, and reranker ordering are all tested. Integration tests verify both the “hand-crafted artifact” path and the real `train_module4_scorer(...)` pipeline using the fixture KB. Tests are deterministic (no random seeds needed beyond KB contents) and focus on behavior that matters (ranking changes, fallback semantics).

**Evidence:**  
- `unit_tests/ml/test_dataset.py` — playlist + ratings label semantics.  
- `unit_tests/ml/test_artifacts_roundtrip.py` — scorer/reranker artifact roundtrip.  
- `unit_tests/ml/test_learned_scorer.py` — fallback and learned score blend.  
- `unit_tests/ml/test_reranker.py` — reranker ordering.  
- `integration_tests/module_4/test_module4_integration.py` and `test_module4_train_flow.py`.  
- `pytest unit_tests/ml integration_tests/module_4 -q` → `10 passed`.

**Score: 8/8** — Comprehensive, meaningful tests for the new module.

---

### 4. Individual Participation (6 points)

**Assessment:**  
As with earlier checkpoints, local git history for Module 4 work appears concentrated under a single contributor in this clone. The scope of Module 4 is non-trivial (new package, training pipeline, tests, and integration), which reflects significant individual effort, but balanced multi-member participation is not clearly demonstrated from local evidence alone.

**Evidence:**  
- Local `git log` (not reproduced here) showing recent commits in `src/ml/`, `unit_tests/ml/`, and `integration_tests/module_4/` predominantly by one author.

**Score: 4/6** — Strong individual contribution; multi-member balance not evident locally.

---

### 5. Documentation (5 points)

**Assessment:**  
Module-level docstrings and type hints are good, and `README.md` now documents Module 4 inputs, training command, and high-level usage of the ML-enhanced scorer. `MODULE4_PLAN.md` has a detailed design and updated todos. However, there is not yet a dedicated prose summary (beyond this report) that explains design choices, trade-offs, and example behavior for non-code readers (e.g., “what changed when ML was turned on?”).

**Evidence:**  
- Docstrings in `train_module4.py`, `learned_scorer.py`, `reranker.py`.  
- Updated Module 4 row and training section in `README.md`.  
- Detailed plan in `MODULE4_PLAN.md`.  
- This `checkpoint_4_module_report.md` as rubric narrative.

**Score: 4/5** — Good docs; could be strengthened with a short narrative example and clearer λ/feature rationale.

---

### 6. I/O Clarity (5 points)

**Assessment:**  
Inputs and outputs are explicit and well-structured: `user_playlists.json` and `user_ratings.json` schemas are simple and documented; artifacts (`module4_scorer.json`, `module4_reranker.json`) have clear `version`, `trained_at`, `source`, `config`, and `weights` fields. Public APIs (`build_training_examples`, `train_module4_scorer`, `LearnedPreferenceScorer.score`, `rerank_results_with_artifact`, `build_scorer_with_optional_ml`) all have straightforward signatures and behavior.

**Evidence:**  
- `MODULE4_PLAN.md` Phase 1 data contract.  
- `ml.artifacts` dataclasses and load/save helpers.  
- `README.md` Module 4 training section.

**Score: 5/5** — Excellent clarity of input/output formats and APIs.

---

### 7. Topic Engagement (6 points)

**Assessment:**  
Module 4 engages meaningfully with supervised learning: it defines labels from playlists + ratings, extracts a feature representation tied to KB facts (genre, mood, danceability, etc.), learns linear feature weights, and integrates them into a live recommendation system. The reranker introduces a simple two-stage ranking architecture. The design stays intentionally simple (feature means rather than a complex ML library) to keep the focus on how learning shapes preferences, which fits the course goals.

**Evidence:**  
- Feature/label design in `dataset.py` and `train_module4.py`.  
- Learned vs rule-based scoring blend in `learned_scorer.py`.  
- Reranker module and associated tests.

**Score: 6/6** — Strong and appropriate engagement with the “ML from playlists” topic.

---

### 8. GitHub Practices (4 points)

**Assessment:**  
Repository organization remains strong (`src/ml/`, `unit_tests/ml/`, `integration_tests/module_4/` mirror existing patterns), and commit structure for Module 4 work is coherent. As with earlier checkpoints, PR/issue usage on GitHub cannot be verified from the local clone, but the overall structure and separation of concerns indicate good local practices.

**Evidence:**  
- New directories and files follow existing module layout conventions.  
- Tests are colocated with their module.  
- No indication of ad-hoc or experimental files left in the tree.

**Score: 3/4** — Good local practices; PR/issue workflow evidence not visible locally.

---

## Scores Summary

| Criterion                    | Points | Max | Notes |
| --------------------------- | ------ | --- | ----- |
| 1. Functionality            | 8      | 8   | ML scorer + reranker implemented and integrated. |
| 2. Code Elegance and Quality| 8      | 8   | Clean modular design, linear model keeps complexity low. |
| 3. Testing                  | 8      | 8   | Unit + integration tests for dataset, artifacts, scorer, reranker, and train flow. |
| 4. Individual Participation | 4      | 6   | Strong individual work; multi-member balance unclear locally. |
| 5. Documentation            | 4      | 5   | Good docs; could add a short narrative/example. |
| 6. I/O Clarity              | 5      | 5   | Clear schemas and APIs. |
| 7. Topic Engagement         | 6      | 6   | Concrete supervised-learning integration. |
| 8. GitHub Practices         | 3      | 4   | Local structure strong; PR/issue usage unverified. |

**Total: 46 / 50**

---

## Action Items

- [ ] Add a short narrative section (in `README.md` or `MODULE4_PLAN.md`) explaining Module 4’s design choices: feature set, label scheme, why linear weights, and how λ affects behavior.  
- [ ] Add a simple CLI or script (e.g., `query_with_ml_cli`) that demonstrates end-to-end usage: collect preferences → train Module 4 → query with/without ML for comparison.  
- [ ] If available, link or document GitHub PRs/issues showing collaboration on Module 4 to strengthen participation and GitHub-practices evidence.  
- [ ] Optionally, run a small qualitative experiment (even on a tiny playlist) and summarize “what changed” in recommendations with ML enabled, to enrich the checkpoint narrative.

---

## Conclusion

Module 4 is in good shape for the checkpoint: it satisfies the ML-from-playlists goal, integrates cleanly with existing modules, and is backed by solid tests. The main improvements now are about storytelling and usability—making it easier for a grader (or future you) to see how to run the full pipeline and understand the design trade-offs behind the learned scorer and reranker. With those small documentation and CLI additions, this module should be very strong under the course rubric.

---

## Rubric re-run (update)

**Date of re-run:** 2026-04-02  
**Rubric:** [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric) (same as above)  
**Purpose:** Re-assess Module 4 after addressing documentation and CLI usability gaps, **without replacing** the original scoring narrative above. This section records **what changed**, **evidence**, and **re-run scores** for comparison.

### Evidence of improvements (since original report)

| Area | Before (original report) | After (re-run) | Evidence |
| ---- | ------------------------ | -------------- | -------- |
| Module 4 CLI / usability | No dedicated CLI path to toggle ML on/off; only Python snippets and tests. | `query_cli.py` extended with `--use-ml-scorer` and `--use-ml-reranker` flags; uses `build_scorer_with_optional_ml` and `rerank_results_with_artifact` when artifacts exist. | `src/search/query_cli.py` (new args and wiring). |
| Design narrative | README had only a short training subsection; no explicit explanation of labels, features, λ blend, or reranker role. | New “Module 4 Design and Behavior” section in README describing label scheme (playlists + ratings), feature family, linear weight formula, blend equation, and reranker behavior. | `README.md` under “Module 4 Design and Behavior”. |
| Plan/todo alignment | `MODULE4_PLAN.md` todos still marked `pending` for several completed items. | Todos updated to `completed` for data contracts, ML package, training, scorer integration, reranker hook, validation/fallbacks, unit tests, and integration tests; docs/report marked `in_progress`. | `MODULE4_PLAN.md` frontmatter `m4-*` todos. |

### Resolution status of earlier findings

| Original finding | Status (original report) | Status after re-run |
| ---------------- | ------------------------ | ------------------- |
| Major 1 — Missing narrative/README story for Module 4 behavior | Open | **Addressed** — README now has a dedicated Module 4 design section; this report serves as checkpoint narrative. |
| Major 2 — Reranker not exposed via CLI/demo | Open | **Addressed** — `query_cli.py` supports optional ML scorer + reranker flags and uses artifacts when present. |
| Minor 1 — λ and feature choices not justified in docs | Open | **Addressed** — README explains feature family and linear/blend design rationale. |
| Minor 2 — No single CLI for “see ML effect” | Open | **Addressed** — Module 3 Query CLI can now be run with `--use-ml-scorer`/`--use-ml-reranker` for side-by-side use. |

### Rubric scores (re-run)

Only criteria materially affected by these changes are Documentation and, slightly, Topic Engagement (narrative strength). Other criteria remain as in the baseline Module 4 report.

#### 5. Documentation (5 points)

**Re-run assessment:**  
Docs now include both **how** to run Module 4 (commands, flags, artifacts) and **why** it works the way it does (label scheme, feature design, blend formula, reranker role). The new README section plus this updated checkpoint report give graders enough context to understand the ML choices without reading code.

**Evidence:**  
- `README.md` “Module 4 training (offline ML from playlists + ratings)” and “Module 4 Design and Behavior” sections.  
- Updated CLI usage (`python src/search/query_cli.py --use-ml-scorer --use-ml-reranker`).  
- This rubric re-run section.

**Re-run score: 5/5** — Documentation is now strong at both module and project levels.

#### 7. Topic Engagement (6 points)

**Re-run assessment:**  
The underlying implementation was already engaging with ML concepts; the added narrative and CLI make that engagement **much more visible**. Users and graders can now concretely see how playlists + ratings affect the model and how learned scoring/reranking changes output, which strengthens the story without changing the numeric score bracket.

**Evidence:**  
- README design section referencing supervised labels, features, and linear model.  
- CLI that lets users toggle ML components and observe ranking changes interactively.

**Re-run score: 6/6** — Same numeric score; justification strengthened.

### Scores summary (re-run)

| Criterion                    | Original | Re-run | Delta |
| --------------------------- | -------- | ------ | ----- |
| 1. Functionality            | 8        | 8      | —     |
| 2. Code Elegance and Quality| 8        | 8      | —     |
| 3. Testing                  | 8        | 8      | —     |
| 4. Individual Participation | 4        | 4      | —     |
| 5. Documentation            | 4        | **5**  | +1    |
| 6. I/O Clarity              | 5        | 5      | —     |
| 7. Topic Engagement         | 6        | 6      | —     |
| 8. GitHub Practices         | 3        | 3      | —     |

**Original total: 46 / 50**  
**Re-run total: 47 / 50** (delta: **+1**, from Documentation)

### Updated action items (re-run)

- [x] ~~Add short Module 4 design narrative in README and clarify labels/features/λ/reranker~~ **Done** — see README.  
- [x] ~~Expose ML scorer + reranker via CLI for interactive use~~ **Done** — `src/search/query_cli.py`.  
- [ ] If available, add or reference GitHub PRs/issues showing collaboration on Module 4 to strengthen Participation and GitHub Practices criteria.  
- [ ] Optionally, add a brief “before vs after ML” example (e.g., run the CLI with and without `--use-ml-*` for a sample playlist) to this report or README as anecdotal evidence of effect.


