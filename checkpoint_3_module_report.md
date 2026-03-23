# Checkpoint 3: Module Rubric Report

**Rubric:** [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric)  
**Reference:** [Module Rubric](https://csc-343.path.app/rubrics/module.rubric)  
**Scope:** Module 3 — Search Over Knowledge Base (UCS + graph neighbors + preference blend)  
**Implementation:** `src/search/` (`costs.py`, `graph.py`, `ucs.py`, `pipeline.py`), unit tests in `unit_tests/search/`, integration tests in `integration_tests/module_3/`

---

## Summary

Module 3 is implemented and integration-ready. It provides a clear search pipeline from query song MBID to ranked recommendations, combining graph path cost (UCS over KB-derived neighbors) with Module 2 preference scoring. Functionality, testing, I/O clarity, and topic engagement are strong. The main gaps before submission are project hygiene items: optional algorithm variant (Beam, if you want stronger search-topic breadth), minor doc wording cleanup, and verifying PR/issue workflow on GitHub for full GitHub-practices credit.

---

## Findings

### Critical

- None.

### Major

1) **README remains mostly template-level outside Module 3 row updates**  
**Evidence:** `README.md` still includes placeholders for system title/team/proposal and empty rows for modules 1/4/5.  
**Impact on rubric:** Can reduce documentation/readiness confidence under Documentation and project-level review.  
**Suggested fix:** Fill system overview/team/proposal and checkpoint log entries before checkpoint submission.

2) **No second search algorithm variant yet (Beam/A*)**  
**Evidence:** `src/search/` currently exports UCS-based retrieval and pipeline only (`__init__.py` exports `ucs_topk`, `find_similar`; no beam module).  
**Impact on rubric:** Functionality still satisfies Module 3, but topic breadth narrative is weaker if evaluators expect explicit comparison/tradeoff discussion.  
**Suggested fix:** Add optional `beam.py` and a short comparison note in docs (runtime tradeoff vs UCS).

### Minor

1) **One docstring wording typo in pipeline return description**  
**Evidence:** `src/search/pipeline.py` says “Sorted list of `SearchResult`, longest-first by `combined_score`.”  
**Impact on rubric:** Minor documentation precision issue only.  
**Suggested fix:** Change wording to “highest-first by `combined_score`” or “descending by `combined_score`”.

---

## Rubric Scores

### 1. Functionality (8 points)

**Assessment:** Module 3 implements all core specified behavior: pairwise dissimilarity costs, KB-index neighbor generation, degree-capped adjacency ordering, UCS top-K retrieval, and final ranking that combines search cost with Module 2 preference score. Query MBID validation and edge-case handling (`k <= 0`, unknown MBID) are implemented.

**Evidence:** `src/search/costs.py`, `src/search/graph.py`, `src/search/ucs.py`, `src/search/pipeline.py`.

**Score: 8/8** — Core module functionality is complete and working.

---

### 2. Code Elegance and Quality (8 points)

**Assessment:** Design is cleanly modular and readable: each file has one responsibility (cost model, graph, algorithm, orchestration), typed signatures, focused helpers, deterministic ordering/tie-breaks, and sensible defaults (`DissimilarityWeights`, normalization helper). API surface is concise through `src/search/__init__.py`.

**Evidence:** `src/search/__init__.py` exports stable public API; small single-purpose functions in `costs.py` and `graph.py`; deterministic heap and neighbor ordering in `ucs.py`.

**Score: 8/8** — High-quality architecture and implementation clarity.

---

### 3. Testing (8 points)

**Assessment:** Testing is comprehensive and behavior-focused. Unit tests cover distance behavior, neighbor construction/capping, UCS ordering/determinism/errors, and pipeline ranking/normalization logic. Integration tests cover full KB + scorer + pipeline flow.

**Evidence:** `unit_tests/search/test_costs.py`, `test_graph.py`, `test_ucs.py`, `test_pipeline.py`; `integration_tests/module_3/test_module3_integration.py`. Current run: `44 passed` for `unit_tests/search/` + `integration_tests/module_3/`.

**Score: 8/8** — Strong unit + integration coverage with meaningful assertions.

---

### 4. Individual Participation (6 points)

**Assessment:** Local commit evidence for recent work shows Module 3 commits by one contributor in the last 7 days in this clone.

**Evidence (local only):**  
`git log --since="7 days ago" --oneline --format="%h %an %ad %s" --date=short` includes:  
- `aa4016f eleanorbadgett 2026-03-22 UCS over neighbors`  
- `39dc961 eleanorbadgett 2026-03-22 module 3 plan and search bones`
- 'bd1338f Chace Sledge 2026-03-23 Queries for user input'

**Score: 4/6** — Substantial progress is present, but balanced multi-member participation is not demonstrated from local recent-history evidence alone.

---

### 5. Documentation (5 points)

**Assessment:** Module 3 source has good docstrings and typed APIs, and `README.md`/`AGENTS.md` now include Module 3 I/O/dependency entries and test paths. Minor wording precision issue noted.

**Evidence:** `src/search/*.py` docstrings; `README.md` module plan row for Module 3; `AGENTS.md` module table and implementation note for Module 3.

**Score: 4/5** — Good module-level docs, with minor precision/template cleanup remaining.

---

### 6. I/O Clarity (5 points)

**Assessment:** Inputs/outputs are explicit and verifiable at each public boundary: `pairwise_dissimilarity(kb, mbid_a, mbid_b, weights) -> float`; `capped_neighbors(...) -> List[str]`; `ucs_topk(...) -> List[Tuple[str, float]]`; `find_similar(...) -> List[SearchResult]` with `path_cost`, `preference_score`, `combined_score`.

**Evidence:** Typed signatures and dataclass in `src/search/costs.py`, `graph.py`, `ucs.py`, `pipeline.py`.

**Score: 5/5** — Excellent I/O clarity and integration contract quality.

---

### 7. Topic Engagement (6 points)

**Assessment:** Module strongly engages with search-topic material: explicit state-space neighbors over KB indexes, weighted path-cost formulation, UCS optimal expansion semantics, and algorithmic controls (`max_degree`, weights). Integration with rule-based preferences is meaningful and interpretable.

**Evidence:** `src/search/graph.py` neighbor/state construction; `src/search/costs.py` path-cost design; `src/search/ucs.py` UCS; `src/search/pipeline.py` score blending.

**Score: 6/6** — Deep and concrete engagement with Search topic requirements.

---

### 8. GitHub Practices (4 points)

**Assessment:** Repository organization is strong (`src/`, `unit_tests/`, `integration_tests/`, module-specific folders). Commit messages are descriptive. PR/issue usage cannot be confirmed from local repository alone.

**Evidence:** Local branches: `main`, `origin/main`, `origin/feedback`. Commit messages for Module 3 are clear and task-specific.

**Score: 3/4** — Good local practices; confirm PR/issues on GitHub for full marks.

---

## Scores Summary

| Criterion                    | Points | Max | Notes |
| --------------------------- | ------ | --- | ----- |
| 1. Functionality            | 8      | 8   | Full Module 3 flow implemented and working. |
| 2. Code Elegance and Quality| 8      | 8   | Clean modular design and deterministic behavior. |
| 3. Testing                  | 8      | 8   | 44 passing tests across unit + integration scope. |
| 4. Individual Participation | 4      | 6   | Recent local history shows one contributor for Module 3 commits. |
| 5. Documentation            | 4      | 5   | Good module docs; repo-level template placeholders remain. |
| 6. I/O Clarity              | 5      | 5   | Strong typed contracts and result structure. |
| 7. Topic Engagement         | 6      | 6   | Strong search-topic implementation. |
| 8. GitHub Practices         | 3      | 4   | Local structure/commits good; PR/issue usage unverified locally. |

**Total: 46 / 50**

---

## Action Items

- [ ] Fill remaining README placeholders (title/team/proposal/other module rows/checkpoint log).  
- [ ] (Optional but valuable) add `beam.py` + short UCS vs Beam tradeoff note for stronger search-topic breadth.  
- [ ] Fix minor pipeline doc wording (“descending by combined score”).  
- [ ] Verify and document PR/issue usage on GitHub before final submission.

---

## Questions

- Do you want this report to score only technical module artifacts (excluding participation/GitHub workflow), or keep all rubric categories as above?  
- If you have contribution evidence outside local git (pairing docs, PR reviews), should that be added to strengthen criterion 4?

---

## Conclusion

Checkpoint 3 implementation is in good shape for technical criteria: functionality, code quality, testing, I/O clarity, and topic engagement are strong. Remaining improvements are mostly documentation and process evidence. With those cleaned up, this module is likely submission-ready at a high score.

---

## Rubric re-run (update)

**Date of re-run:** 2026-03-23  
**Rubric:** [Module Review Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric) (same as above)  
**Purpose:** Re-assess Module 3 after optional beam search and other improvements, **without replacing** the original scoring narrative above. This section records **what changed**, **evidence**, and **re-run scores** for comparison.

### Evidence of improvements (since original report)

| Area | Before (original report) | After (re-run) | Evidence |
| ---- | ------------------------ | -------------- | -------- |
| Second search algorithm | Major finding: no Beam/A* variant; `__init__.py` listed only UCS + pipeline | **`beam_topk`** implemented; exported from `search` package | `src/search/beam.py`; `src/search/__init__.py` (`beam_topk` in `__all__`) |
| Search-topic narrative | UCS only in primary path | UCS **plus** beam module docstring: optimality vs approximation, informal complexity | Module docstring in `src/search/beam.py` (lines 1–16): UCS vs beam tradeoff, informal \(O(\cdot)\) discussion |
| Pipeline docstring precision | Minor finding: “longest-first by `combined_score`” | **Fixed:** “descending by `combined_score`” | `src/search/pipeline.py` (`find_similar` Returns, ~line 86) |
| Test count (Module 3 scope) | 44 passed (`unit_tests/search/` + `integration_tests/module_3/`) | **53 passed** (added beam unit tests) | Command: `pytest unit_tests/search/ integration_tests/module_3/ -q` → `53 passed` (2026-03-23) |

### Resolution status of earlier findings

| Original finding | Status | Notes |
| ---------------- | ------ | ----- |
| **Major 1** — README mostly template outside Module 3 row | **Open** *(at time of re-run #1)* | **Addressed** in **re-run #2** — see [`README.md`](README.md), [`AGENTS.md`](AGENTS.md). |
| **Major 2** — No second search variant (Beam/A*) | **Addressed** | `beam_topk` + complexity/tradeoff narrative in `src/search/beam.py`. |
| **Minor 1** — Pipeline return wording | **Addressed** | `find_similar` return description now uses “descending by `combined_score`”. |

### Rubric scores (re-run)

Assumptions: same rubric categories; evidence updated for improvements. Criteria not listed below are **unchanged** from the original report (see sections above).

#### 1. Functionality (8 points)

**Re-run assessment:** Original core behavior remains. **Additional** optional API: `beam_topk(...)` for approximate top-K retrieval with `beam_width` and `max_depth`, using the same neighbor policy and edge costs as UCS.

**Evidence:** `src/search/beam.py`; export in `src/search/__init__.py`.

**Re-run score: 8/8** — Still meets full functionality expectation; beam is additive.

#### 3. Testing (8 points)

**Re-run assessment:** Beam behavior covered (exclusion of query, ordering, determinism, invalid args, parity with UCS on a small clique fixture).

**Evidence:** `unit_tests/search/test_beam.py`; full suite **53 passed** for `unit_tests/search/` + `integration_tests/module_3/`.

**Re-run score: 8/8** — Coverage strengthened; count updated.

#### 5. Documentation (5 points)

**Re-run assessment:** Module 3 source documentation improved: pipeline return wording fixed; beam module includes explicit UCS vs beam and complexity discussion suitable for checkpoint narrative. Repository-wide README placeholders (**Major 1**) remain a separate gap.

**Evidence:** `src/search/pipeline.py`; `src/search/beam.py` module docstring.

**Re-run score: 5/5** — Module-level docs for Module 3 are strong; README template issue tracked separately under Major 1.

#### 7. Topic Engagement (6 points)

**Re-run assessment:** Original UCS + graph formulation remains. Beam adds explicit **algorithmic comparison** and tradeoff language (optimality vs speed/memory), strengthening the “search variants” story for the course topic.

**Evidence:** `src/search/beam.py` (checkpoint narrative + complexity note).

**Re-run score: 6/6** — Same top score; justification strengthened.

### Scores summary (re-run)

| Criterion | Original | Re-run | Delta |
| --------- | -------- | ------ | ----- |
| 1. Functionality | 8 | 8 | — |
| 2. Code Elegance and Quality | 8 | 8 | — |
| 3. Testing | 8 | 8 | — (evidence: 44 → **53** tests) |
| 4. Individual Participation | 4 | 4 | — |
| 5. Documentation | 4 | **5** | +1 |
| 6. I/O Clarity | 5 | 5 | — |
| 7. Topic Engagement | 6 | 6 | — (narrative strengthened) |
| 8. GitHub Practices | 3 | 3 | — |

**Original total: 46 / 50**  
**Re-run total: 47 / 50** (delta: **+1**, from Documentation criterion)

### Updated action items (re-run)

- [x] ~~(Optional) add `beam.py` + short UCS vs Beam tradeoff note~~ **Done** — see `src/search/beam.py`.  
- [x] ~~Fix pipeline doc wording (“descending by combined score”)~~ **Done** — see `src/search/pipeline.py`.  
- [x] ~~Fill remaining README placeholders~~ **Done** in re-run #2 — see [`README.md`](README.md). *(Was open at re-run #1.)*  
- [ ] Verify and document PR/issue usage on GitHub before final submission. *(Unchanged.)*

### Questions (re-run)

- Should the checkpoint submission include a **short written comparison** (1 paragraph) of UCS vs `beam_topk` parameters in the student report, pointing to `beam.py` docstring as the canonical reference?

---

**Note:** The original Summary, Findings, Rubric Scores, Scores Summary (46/50), Action Items, Questions, and Conclusion **remain valid as the historical baseline** for the first review pass. This re-run section **supplements** that baseline with post-improvement evidence and updated scoring where justified.

---

## Rubric re-run (update #2) — README & AGENTS

**Date of re-run:** 2026-03-23  
**Trigger:** Repository documentation updated to resolve **Major finding 1** from the baseline review (README placeholders and thin project-level docs), in line with [`README.md`](README.md) and [`AGENTS.md`](AGENTS.md) changes.

### Evidence of improvements (since re-run #1)

| Area | Re-run #1 state | After re-run #2 | Evidence |
| ---- | ----------------- | --------------- | -------- |
| **Major 1 — README / project docs** | Open (“fill README before submission”) | **Addressed** | [`README.md`](README.md): system title, overview, team (Eleanor Badgett, Chace Sledge), proposal links (course + `MODULES.md`), **full module plan rows 1–6**, repository layout, setup, running, expanded testing commands, test structure for Modules 2–3, **checkpoint log** with dates and evidence pointers, references. |
| **AGENTS.md alignment** | Partial placeholders in project context | **Updated** | [`AGENTS.md`](AGENTS.md): system title, theme, proposal pointer; Module **1** row added; Module 3 line mentions **beam**; implementation paths for Module 1. |
| Module 3 test count | 53 passed | **Unchanged (53 passed)** | `pytest unit_tests/search/ integration_tests/module_3/ -q` → `53 passed` (verified 2026-03-23). |

### Resolution status (supersedes re-run #1 row for Major 1 only)

| Finding | Re-run #1 status | Status after re-run #2 |
| ------- | ---------------- | ---------------------- |
| **Major 1** — README mostly template | Open | **Addressed** — see table above. |

### Rubric scores (re-run #2)

**Documentation (criterion 5):** Re-run #1 scored documentation **5/5** on the strength of **Module 3 source** docs (`pipeline.py`, `beam.py`) while noting README gaps. After **`README.md` and `AGENTS.md` updates**, **project-level** documentation now matches the same tier: clear I/O, module table, checkpoints, setup, and references. **Score remains 5/5**; the improvement is **breadth and submission readiness**, not a higher numeric bracket.

**All other criteria:** Unchanged from re-run #1 totals (Functionality 8, Code quality 8, Testing 8, Participation 4, I/O 5, Topic engagement 6, GitHub practices 3).

| Metric | Re-run #1 | Re-run #2 |
| ------ | --------- | --------- |
| **Total** | **47 / 50** | **47 / 50** |
| **Notes** | +1 vs baseline from Module 3 docs | Major 1 closed; score stable; evidence stronger |

### Updated action items (re-run #2)

- [x] ~~Fill README placeholders (title/team/proposal/module rows/checkpoint log)~~ **Done** — [`README.md`](README.md).  
- [x] ~~Align `AGENTS.md` project context with README~~ **Done** — [`AGENTS.md`](AGENTS.md).  
- [x] ~~Optional beam + pipeline doc~~ *(already done in re-run #1)*.  
- [ ] Verify and document **PR/issue** usage on GitHub before final submission. *(Still open.)*

### Note on historical sections

The **baseline Findings** (lines 22–39) still record the original Major/Minor list as first-pass history. **Re-run #1** and **#2** document subsequent fixes; use **re-run #2** for the current accuracy of Major 1 and documentation evidence.
