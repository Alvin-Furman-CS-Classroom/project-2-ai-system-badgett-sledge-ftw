# Module 5 Cluster Analysis (How Data Was Created + Interpretation)

This note explains how the cluster visualizations in `presentation/figures/module5/` were generated, what models/modules were involved, what the plot axes mean, and what takeaways are reasonable.

## 1) How We Created Enough Data for Clusters

The final cluster figures were generated from a **multi-seed query-pool union** workflow (not from only 1-4 songs).

For each persona:

1. Read that persona's curated seed playlist (`user_playlists.json`).
2. Take `--seed-count 10` seed MBIDs.
3. For each seed, run retrieval with a candidate pool of `--cluster-pool-size 150`.
4. Union and deduplicate all retrieved MBIDs across seeds.
5. Cluster the union set with K-means (`--cluster-k 6`).
6. Project clustered vectors to 2D and plot.

This creates ~1.3k-1.5k points per persona (large enough to reveal structure).

## 2) Modules Used in This Pipeline

- **Module 1 (Knowledge Base)**  
  Source of songs and facts (genres, moods, timbre, etc.) used for features.

- **Module 2 (Rule-based preferences)**  
  Persona profile (`user_profile.json`) defines user preference logic/weights baseline.

- **Module 3 (Search/Retrieval)**  
  `find_similar` retrieves per-seed candidate pools (graph/path + preference blend).

- **Module 4 (Learned scorer)**  
  Enabled with `--use-ml-scorer`; blends learned scoring with rule-based scoring.

- **Module 5 (Clustering + diversification)**  
  Builds feature vectors, runs deterministic K-means, and analyzes resulting groups.

## 3) Model Types Used

This workflow combines multiple model types:

- **Rule-based model (Module 2):** preference rules + weighted scoring.
- **Learned linear scorer (Module 4):** artifact-driven scorer blended into retrieval scoring (`module4_scorer.json`).
- **Graph search model (Module 3):** UCS-style retrieval over the KB graph.
- **Unsupervised clustering model (Module 5):** deterministic K-means.
- **Linear projection model:** PCA to 2D using NumPy SVD for visualization.

## 4) Feature Space Used for Clustering (Module 5)

Feature vectors are multi-hot/binary indicators from KB facts:

- genres
- moods
- danceable
- voice vs instrumental
- timbre
- loudness bucket (quiet/medium/loud)

So points are clustered by **music metadata similarity**, not raw audio embeddings.

## 5) Axes in the Cluster Images

Each plot is a 2D PCA projection:

- **X-axis = PC1** (first principal component)
- **Y-axis = PC2** (second principal component)

Important interpretation notes:

- PC1/PC2 are **derived linear combinations** of original features, not single human-readable attributes.
- Distances/regions in the 2D plot are an approximation of high-dimensional relationships.
- Clusters are assigned in full feature space first; PCA is for visualization only.

## 6) Commands Used (Final High-Capacity Setting)

All personas were generated with:

```bash
PYTHONPATH=src python3 presentation/build_module5_query_pool_union.py \
  --persona-dir data/personas/<persona_name> \
  --use-ml-scorer \
  --seed-count 10 \
  --cluster-pool-size 150 \
  --cluster-k 6
```

## 7) Final Union Sizes (Points per Persona)

- `persona_01_college_commuter`: 1379 points
- `persona_02_classic_rock_dad`: 1499 points
- `persona_03_omnivore_indie`: 1367 points
- `persona_04_trap_maximalist`: 1415 points
- `persona_05_classical_choral`: 1419 points
- `persona_06_mainstream_pop`: 1458 points

All were created with 10 seeds and retrieval pool size 150.

## 8) Potential Takeaways from These Clusters

1. **Cluster structure appears consistently across personas**  
   The workflow does not rely on one special profile; each persona produces non-trivial grouping.

2. **Retrieval is multi-modal, not one-neighborhood-only**  
   Union pools from multiple seeds reveal several stylistic neighborhoods per user.

3. **Module 5 diversification is justified**  
   Since candidate pools are clustered, round-robin diversification can surface varied-but-relevant songs instead of near-duplicates.

4. **Persona design affects cluster geometry**  
   Broader personas (e.g., omnivore) tend to show wider spread/more mixed regions; narrower personas may show tighter concentration.

5. **PCA plot should be paired with quantitative checks**  
   For stronger claims, include cluster size balance and top feature/genre summaries per cluster (visual + numeric evidence).

## 9) Suggested Slide/Report Wording

"We generated large candidate sets by unioning retrieval results from 10 persona-specific seed songs (150 candidates per seed), then clustered in Module 5 feature space. PCA plots show consistent multi-cluster structure across all personas, indicating recommendations occupy multiple stylistic regions. This supports using Module 5 diversification to improve variety while preserving preference relevance."

