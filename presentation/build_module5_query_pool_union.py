#!/usr/bin/env python3
"""
Build a multi-seed query-pool union for Module 5 and visualize clusters.

Workflow:
1) Read seed MBIDs from a persona playlist file.
2) For each seed, run Module 3 retrieval (optionally with Module 4 scorer blend).
3) Union across seeds (stable order, deduplicated) as SearchResults (best combined_score per MBID).
4) Cluster with Module 5 K-means features and apply round-robin diversification (cluster_and_organize).
5) Project to 2D with PCA (NumPy SVD) and write a scatter plot.
6) Write JSON including mbids (union order) and mbids_diversified_round_robin (Module 5 ordering).

Fast path (--reuse-union-json): load mbids from an existing union JSON, score with persona scorer only
(preference blend, no path cost), then cluster + diversify + optional plot without re-retrieving.

Run from project root:
  PYTHONPATH=src python3 presentation/build_module5_query_pool_union.py \
    --persona-dir data/personas/persona_03_omnivore_indie
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".matplotlib_cache"))
os.environ.setdefault("MPLBACKEND", "Agg")

SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from clustering.features import FeatureVectorSpec, build_feature_vectors
from clustering.kmeans import KMeansConfig, kmeans_cluster
from clustering.organize import cluster_and_organize
from knowledge_base_wrapper import KnowledgeBase
from ml import build_scorer_with_optional_ml
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.survey import PreferenceProfile
from search.pipeline import SearchResult, find_similar


def _load_profile(path: Path) -> PreferenceProfile:
    with path.open(encoding="utf-8") as f:
        return PreferenceProfile(**json.load(f))


def _load_seed_mbids(playlists_path: Path, seed_count: int) -> list[str]:
    with playlists_path.open(encoding="utf-8") as f:
        raw = json.load(f)
    out: list[str] = []
    seen = set()
    for pl in raw.get("playlists", []):
        mbids = pl.get("mbids", [])
        if not isinstance(mbids, list):
            continue
        for mbid in mbids:
            if not isinstance(mbid, str) or mbid in seen:
                continue
            seen.add(mbid)
            out.append(mbid)
            if len(out) >= seed_count:
                return out
    return out


def _retrieve_union_results(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    seeds: list[str],
    *,
    retrieval_k: int,
    alpha: float,
    beta: float,
    max_degree: int,
) -> list[SearchResult]:
    """
    Union retrieval pools: first-seen order, keep the SearchResult with highest combined_score per MBID.
    """
    order: list[str] = []
    by_mbid: dict[str, SearchResult] = {}
    for seed in seeds:
        results = find_similar(
            kb=kb,
            query_mbid=seed,
            scorer=scorer,
            k=retrieval_k,
            alpha=alpha,
            beta=beta,
            max_degree=max_degree,
        )
        for r in results:
            if r.mbid not in by_mbid:
                by_mbid[r.mbid] = r
                order.append(r.mbid)
            elif r.combined_score > by_mbid[r.mbid].combined_score:
                by_mbid[r.mbid] = r
    return [by_mbid[m] for m in order]


def _synthetic_results_from_mbids(kb: KnowledgeBase, scorer, mbids: list[str]) -> list[SearchResult]:
    """Preference-only scores for diversify when reusing a saved MBID list (no retrieval)."""
    out: list[SearchResult] = []
    for m in mbids:
        ps = float(scorer.score(m, kb))
        out.append(SearchResult(mbid=m, path_cost=0.0, preference_score=ps, combined_score=ps))
    return out


def _pca_2d(X: np.ndarray) -> np.ndarray:
    if X.shape[0] == 0:
        return np.zeros((0, 2))
    if X.shape[0] == 1:
        return np.zeros((1, 2))
    Xc = X.astype(float) - X.mean(axis=0, keepdims=True)
    U, s, _Vt = np.linalg.svd(Xc, full_matrices=False)
    k = min(2, len(s))
    proj = U[:, :k] * s[:k]
    if k < 2:
        proj = np.pad(proj, ((0, 0), (0, 2 - k)), mode="constant")
    return proj


def _label(kb: KnowledgeBase, mbid: str, max_len: int = 42) -> str:
    song = kb.get_song(mbid) or {}
    text = f"{song.get('artist', '?')} — {song.get('track', '?')}"
    text = str(text).strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _plot_clusters(
    proj: np.ndarray,
    cluster_ids: np.ndarray,
    labels: list[str] | None,
    out_path: Path,
    title: str,
    max_labels: int,
) -> None:
    uniq = sorted(np.unique(cluster_ids).tolist())
    fig, ax = plt.subplots(figsize=(10, 8))
    for i, cid in enumerate(uniq):
        mask = cluster_ids == cid
        ax.scatter(
            proj[mask, 0],
            proj[mask, 1],
            c=[f"C{i % 10}"],
            s=45,
            alpha=0.85,
            edgecolors="white",
            linewidths=0.4,
            label=f"cluster {cid}",
        )
    if labels is not None and max_labels > 0:
        step = max(1, len(labels) // max_labels)
        for i in range(0, len(labels), step):
            ax.annotate(labels[i], (proj[i, 0], proj[i, 1]), fontsize=6, alpha=0.7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build multi-seed query-pool union and plot Module 5 clusters")
    parser.add_argument("--persona-dir", required=True, help="Persona folder with user_profile.json/user_playlists.json/module4_scorer.json")
    parser.add_argument("--kb", default="data/knowledge_base.json")
    parser.add_argument("--seed-count", type=int, default=10, help="How many playlist MBIDs to use as seeds")
    parser.add_argument("--cluster-pool-size", type=int, default=150, help="Per-seed retrieval pool size")
    parser.add_argument("--k", type=int, default=20, help="Top-k setting; retrieval uses max(k, cluster-pool-size)")
    parser.add_argument("--max-degree", type=int, default=50)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--use-ml-scorer", action="store_true", help="Blend persona module4_scorer.json if present")
    parser.add_argument("--cluster-k", type=int, default=6)
    parser.add_argument("--cluster-seed", type=int, default=343)
    parser.add_argument("--cluster-max-iters", type=int, default=25)
    parser.add_argument("--max-labels", type=int, default=0, help="0 = no labels")
    parser.add_argument("--out-json", default=None, help="Output union MBIDs JSON")
    parser.add_argument("--out-plot", default=None, help="Output cluster PCA PNG")
    parser.add_argument(
        "--reuse-union-json",
        action="store_true",
        help="Load mbids from existing out-json (default path); skip retrieval. Uses preference-only scores for ranking within clusters.",
    )
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Skip PCA scatter (faster with --reuse-union-json).",
    )
    args = parser.parse_args()

    persona_dir = PROJECT_ROOT / args.persona_dir
    persona_name = persona_dir.name
    kb = KnowledgeBase(str(PROJECT_ROOT / args.kb))
    profile = _load_profile(persona_dir / "user_profile.json")

    out_json = PROJECT_ROOT / (
        args.out_json or f"presentation/figures/module5/{persona_name}_union_query_pool_mbids.json"
    )
    out_plot = PROJECT_ROOT / (
        args.out_plot or f"presentation/figures/module5/{persona_name}_union_query_pool_cluster_pca.png"
    )

    rules = build_rules(profile)
    weights = get_default_weights(rules)
    base_scorer = PreferenceScorer(rules, weights)
    scorer = base_scorer
    scorer_path = persona_dir / "module4_scorer.json"
    if args.use_ml_scorer and scorer_path.exists():
        scorer = build_scorer_with_optional_ml(base_scorer, artifact_path=str(scorer_path), blend_weight=0.5)

    seeds: list[str] = []
    retrieval_k = max(int(args.k), int(args.cluster_pool_size))
    union_results: list[SearchResult]

    if args.reuse_union_json:
        if not out_json.exists():
            raise FileNotFoundError(f"--reuse-union-json requires existing file: {out_json}")
        with out_json.open(encoding="utf-8") as f:
            blob = json.load(f)
        raw_seeds = blob.get("seed_mbids")
        if isinstance(raw_seeds, list):
            seeds = [str(x) for x in raw_seeds if x]
        mbids = blob.get("mbids")
        if not isinstance(mbids, list) or not mbids:
            raise ValueError(f"No mbids list in {out_json}")
        union_mbids = [str(x) for x in mbids if x]
        rk = blob.get("retrieval_k_per_seed")
        if isinstance(rk, int):
            retrieval_k = rk
        union_results = _synthetic_results_from_mbids(kb, scorer, union_mbids)
    else:
        seeds = _load_seed_mbids(persona_dir / "user_playlists.json", max(1, int(args.seed_count)))
        if not seeds:
            raise RuntimeError(f"No seed MBIDs found in {persona_dir / 'user_playlists.json'}")
        union_results = _retrieve_union_results(
            kb,
            scorer,
            seeds,
            retrieval_k=retrieval_k,
            alpha=float(args.alpha),
            beta=float(args.beta),
            max_degree=int(args.max_degree),
        )
        if not union_results:
            raise RuntimeError("Union results empty; nothing to cluster.")

    union_mbids = [r.mbid for r in union_results]
    if not union_mbids:
        raise RuntimeError("Union MBIDs is empty; no output to create.")

    kmeans_cfg = KMeansConfig(k=int(args.cluster_k), seed=int(args.cluster_seed), max_iters=int(args.cluster_max_iters))
    clustered = cluster_and_organize(
        kb,
        union_results,
        top_k=len(union_results),
        kmeans=kmeans_cfg,
    )
    diversified_mbids = [r.mbid for r in clustered.diversified]

    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "name": f"{persona_name}_union_query_pool",
        "seed_mbids": seeds,
        "mbids": union_mbids,
        "retrieval_k_per_seed": retrieval_k,
        "mbids_diversified_round_robin": diversified_mbids,
        "module5_diversify": {
            **clustered.metadata,
            "diversified_length": len(diversified_mbids),
            "reuse_union_json_preference_only_scores": bool(args.reuse_union_json),
        },
    }
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    if not args.skip_plot:
        vectors, _vocab = build_feature_vectors(kb, union_mbids, spec=FeatureVectorSpec())
        assignments = kmeans_cluster(vectors, config=kmeans_cfg)
        X = np.array([vectors[m] for m in union_mbids], dtype=float)
        proj = _pca_2d(X)
        cluster_ids = np.array([assignments[m] for m in union_mbids], dtype=int)
        labels = None if int(args.max_labels) <= 0 else [_label(kb, m) for m in union_mbids]
        _plot_clusters(
            proj,
            cluster_ids,
            labels,
            out_plot,
            title=f"Module 5 multi-seed query-pool clusters ({persona_name})\nseeds={len(seeds)}, union={len(union_mbids)}, K={args.cluster_k}",
            max_labels=int(args.max_labels),
        )
        print(f"Wrote {out_plot}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

