---
name: module-5-kmeans-plan
overview: Implement Module 5 as a deterministic K-means clustering layer that organizes Module 3/4 ranked candidates into diverse, interpretable recommendation groups without breaking existing retrieval/scoring APIs.
todos:
  - id: m5-contracts
    content: Define Module 5 data contracts and deterministic K-means configuration (k, seed, pool size).
    status: pending
  - id: m5-impl
    content: Implement src/clustering feature builder, K-means algorithm, and result organizer APIs.
    status: pending
  - id: m5-integration
    content: Integrate optional clustering path into query workflow without breaking existing Module 3/4 behavior.
    status: pending
  - id: m5-tests
    content: Add unit_tests/clustering and integration_tests/module_5 coverage for determinism, edge cases, and diversity behavior.
    status: pending
  - id: m5-docs
    content: Update README and create Module 5 planning/report artifacts for checkpoint submission.
    status: pending
isProject: false
---

# Module 5 Plan (K-means Clustering)

## Objective

Build a **post-retrieval clustering stage** that takes ranked candidates from Modules 3–4 and returns grouped recommendations that improve diversity while preserving relevance.

## Current Baseline (What We Reuse)

- Candidate generation and scoring already exist:
  - Module 3 retrieval + blend in [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/pipeline.py](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/pipeline.py)
  - Interactive query flow in [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/query_cli.py](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/query_cli.py)
  - Optional ML scorer/reranker from Module 4 in [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/ml](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/ml)
- Module 5 should be a **new organization layer**, not a replacement of retrieval/scoring.

## Design Decisions

- Primary algorithm: **K-means** on feature vectors derived from KB facts.
- Deterministic behavior for grading/testing:
  - fixed random seed
  - stable tie-breakers (MBID ascending)
  - bounded iteration count
- Operate on **top-N candidate pool** (from Module 3 or Module 4-reranked list), then produce clustered output.
- Keep Module 3 APIs backward compatible; add optional Module 5 path.

## Planned Architecture

```mermaid
flowchart LR
querySong[QueryMBID] --> retrieval[Module3_UCS_or_Beam]
retrieval --> optionalM4[Optional_Module4_Rerank]
optionalM4 --> candidatePool[TopN_Candidates]
candidatePool --> featureBuild[KB_FeatureVectorBuilder]
featureBuild --> kmeans[KMeans_Clustering]
kmeans --> clusterRank[RankWithinAndAcrossClusters]
clusterRank --> diverseOutput[DiverseClusteredRecommendations]
```



## Implementation Scope

### 1) New Module 5 package

Create [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/clustering](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/clustering) with:

- `features.py`
  - KB -> numeric feature vector builder for candidate MBIDs.
  - Initial feature set (simple + explainable):
    - one-hot/binary for genre/mood/danceable/voice_instrumental/timbre buckets
    - loudness bucket
    - optional normalized path/preference/combined score as clustering features (configurable)
- `kmeans.py`
  - deterministic K-means implementation (or sklearn wrapper if already allowed by requirements)
  - support `k`, `max_iters`, `seed`
  - handle edge cases (`k<=1`, fewer points than `k`, empty input)
- `organize.py`
  - public API to:
    1. cluster candidates
    2. rank results inside each cluster
    3. produce interleaved/diverse final ordering
  - return a structured output object with cluster metadata and members.
- `__init__.py`
  - export stable Module 5 interfaces.

### 2) Integration with existing recommendation flow

- Keep `[find_similar]( /Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/pipeline.py )` unchanged for compatibility.
- Add optional usage in query layer:
  - extend [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/query_cli.py](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/src/search/query_cli.py) with flags such as:
    - `--use-clustering`
    - `--cluster-k`
    - `--cluster-pool-size`
- Workflow: retrieve ranked candidates first, then pass to Module 5 organizer for grouped/round-robin output.

### 3) Output contract for Module 5

Define a clear data shape (e.g., dataclasses):

- `ClusteredResult` containing:
  - `cluster_id`
  - `centroid_summary` (optional lightweight explainability)
  - ordered list of `SearchResult` members
- `ClusteredRecommendationSet` containing:
  - list of clusters
  - final diversified top-K ordering
  - diagnostic metadata (k used, seed, pool size)

### 4) Diversity strategy

- Default serving strategy: **round-robin by cluster**, taking top member from each cluster, then second member, etc., until `k` filled.
- Cluster-level priority seeded by best `combined_score` in each cluster.
- Ensures no single cluster dominates final top-k.

### 5) Evaluation hooks for checkpoint evidence

- Add simple diversity metrics for reports/tests:
  - unique genres in top-k before vs after clustering
  - cluster coverage count in final top-k
  - optional average pairwise feature distance in served list
- Keep these lightweight and deterministic.

## Testing Plan

### Unit tests

Add [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/unit_tests/clustering](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/unit_tests/clustering):

- `test_features.py`
  - vector extraction correctness from KB fixture
  - missing fact handling defaults
- `test_kmeans.py`
  - deterministic assignments with fixed seed
  - convergence / max-iter behavior
  - edge cases (empty, small N, `k > N`, `k=1`)
- `test_organize.py`
  - round-robin diversity behavior
  - stable tie-breaking
  - final top-k length and ordering invariants

### Integration tests

Add [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/integration_tests/module_5](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/integration_tests/module_5):

- end-to-end: query -> Module 3/4 ranking -> Module 5 clustering output
- verify Module 5 can change presentation order while preserving candidate membership from pool
- verify fallback behavior when clustering disabled

## Documentation Updates

- Update [/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/README.md](/Users/eleanorbadgett/343-projects/project-2-ai-system-badgett-sledge-ftw/README.md):
  - Module 5 section (inputs/outputs)
  - CLI usage examples with clustering flags
  - test commands for `unit_tests/clustering/` and `integration_tests/module_5/`
- Add `MODULE5_PLAN.md` and checkpoint 5 report scaffold analogous to Module 4 documentation style.

## Milestones

1. Define Module 5 contracts + feature schema.
2. Implement deterministic K-means + organizer.
3. Integrate optional clustering path into CLI flow.
4. Add module-specific unit and integration tests.
5. Update docs/report artifacts and run rubric-style review.

## Risks and Mitigations

- **Risk:** K choice too small/large for candidate pool.
  - **Mitigation:** expose `--cluster-k` and enforce safe bounds (`1..min(k_pool, configured_k)`).
- **Risk:** sparse/noisy KB features reduce cluster quality.
  - **Mitigation:** begin with robust categorical features already used by Modules 2/4; keep feature builder extensible.
- **Risk:** relevance drops if diversity overpowers score quality.
  - **Mitigation:** rank within clusters by existing `combined_score`; diversify only at selection step.

