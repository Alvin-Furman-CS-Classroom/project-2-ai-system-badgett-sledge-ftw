#!/usr/bin/env python3
"""
Module 5 cluster visualization:

- Build the same feature vectors as ``cluster_and_organize`` (``build_feature_vectors``).
- Run K-means (same as Module 5) to assign cluster ids.
- Project vectors to 2D with PCA via NumPy SVD (no scikit-learn).
- Scatter plot: x/y = first two PCs, color = cluster id, optional short labels from KB.

Run from project root:
  PYTHONPATH=src python3 presentation/visualize_module5.py --mbids-json path/to/mbids.json

Or derive the candidate pool from a Module 3 query (same defaults as query_cli retrieval):
  PYTHONPATH=src python3 presentation/visualize_module5.py --query-mbid <UUID> ...

Outputs (default): presentation/figures/module5/cluster_pca.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Project root = parent of presentation/
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
from knowledge_base_wrapper import KnowledgeBase
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.survey import PreferenceProfile
from search.pipeline import SearchResult, find_similar
from ml import build_scorer_with_optional_ml


def _load_profile(profile_path: Path) -> PreferenceProfile:
    with profile_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return PreferenceProfile(**data)


def _load_mbids_from_json(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, dict):
        if "mbids" in raw and isinstance(raw["mbids"], list):
            return [str(x) for x in raw["mbids"] if x]
    raise ValueError(f"Expected a JSON list of MBIDs or an object with key 'mbids': {path}")


def pca_project_2d(X: np.ndarray) -> np.ndarray:
    """
    PCA to 2 components using SVD of centered X (rows = samples).

    Returns array of shape (n, 2); if n < 2 or variance is degenerate, pads with zeros.
    """
    n, d = X.shape
    if n == 0:
        return np.zeros((0, 2))
    if n == 1:
        return np.zeros((1, 2))

    Xc = X.astype(float) - X.mean(axis=0, keepdims=True)
    # SVD: Xc = U @ diag(s) @ Vt  => scores = U[:, :2] * s[:2]
    U, s, _Vt = np.linalg.svd(Xc, full_matrices=False)
    k = min(2, len(s))
    proj = U[:, :k] * s[:k]
    if k < 2:
        proj = np.pad(proj, ((0, 0), (0, 2 - k)), mode="constant")
    return proj


def _song_label(kb: KnowledgeBase, mbid: str, *, max_len: int = 42) -> str:
    song = kb.get_song(mbid) or {}
    artist = str(song.get("artist") or "?").strip()
    track = str(song.get("track") or "?").strip()
    text = f"{artist} — {track}"
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def plot_cluster_scatter(
    proj: np.ndarray,
    cluster_ids: np.ndarray,
    labels: list[str] | None,
    out_path: Path,
    *,
    title: str,
    max_labels: int,
) -> None:
    n = proj.shape[0]
    if n == 0:
        print("No points to plot.")
        return

    uniq = np.unique(cluster_ids)
    sorted_cids = sorted(uniq.tolist())

    fig, ax = plt.subplots(figsize=(10, 8))
    for j, cid in enumerate(sorted_cids):
        mask = cluster_ids == cid
        color = f"C{j % 10}"
        ax.scatter(
            proj[mask, 0],
            proj[mask, 1],
            c=[color],
            label=f"cluster {int(cid)}",
            alpha=0.85,
            edgecolors="white",
            linewidths=0.4,
            s=55,
        )

    if labels is not None and max_labels > 0:
        step = max(1, n // max_labels)
        for i in range(0, n, step):
            ax.annotate(
                labels[i],
                (proj[i, 0], proj[i, 1]),
                fontsize=6,
                alpha=0.75,
                xytext=(3, 3),
                textcoords="offset points",
            )

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def _retrieve_pool_ucs(
    kb: KnowledgeBase,
    scorer: PreferenceScorer,
    query_mbid: str,
    *,
    retrieval_k: int,
    alpha: float,
    beta: float,
    max_degree: int,
) -> list[SearchResult]:
    return find_similar(
        kb=kb,
        query_mbid=query_mbid,
        scorer=scorer,
        k=retrieval_k,
        alpha=alpha,
        beta=beta,
        max_degree=max_degree,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Module 5: PCA scatter of K-means clusters")
    parser.add_argument("--kb", default="data/knowledge_base.json", help="Path to knowledge_base.json")
    parser.add_argument(
        "--out",
        default="presentation/figures/module5/cluster_pca.png",
        help="Output PNG path (under project root unless absolute)",
    )
    parser.add_argument("--cluster-k", type=int, default=5, help="K-means clusters (Module 5)")
    parser.add_argument("--cluster-seed", type=int, default=343, help="K-means RNG seed")
    parser.add_argument("--cluster-max-iters", type=int, default=25, help="K-means max iterations")
    parser.add_argument(
        "--cluster-pool-size",
        type=int,
        default=50,
        help="Candidate pool size when using --query-mbid (retrieval uses max(k, pool))",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mbids-json",
        help="JSON file: list of MBIDs or {\"mbids\": [...]}",
    )
    group.add_argument(
        "--query-mbid",
        help="Seed song MBID; runs Module 3 UCS to build the candidate pool",
    )
    parser.add_argument("--profile", default="data/user_profile.json", help="With --query-mbid: Module 2 profile")
    parser.add_argument("--k", type=int, default=10, help="With --query-mbid: top-K for retrieval (min with pool)")
    parser.add_argument("--max-degree", type=int, default=50, help="UCS neighbor cap")
    parser.add_argument("--alpha", type=float, default=1.0, help="UCS blend alpha")
    parser.add_argument("--beta", type=float, default=1.0, help="UCS blend beta")
    parser.add_argument(
        "--use-ml-scorer",
        action="store_true",
        help="Blend Module 4 learned scorer if data/module4_scorer.json exists (same idea as query_cli)",
    )
    parser.add_argument("--ml-scorer-artifact", default="data/module4_scorer.json")
    parser.add_argument(
        "--max-labels",
        type=int,
        default=25,
        help="Annotate up to this many points (spread across the set); 0 disables",
    )
    parser.add_argument("--no-labels", action="store_true", help="Do not annotate song titles")
    args = parser.parse_args()

    kb_path = PROJECT_ROOT / args.kb
    out_path = PROJECT_ROOT / args.out
    kb = KnowledgeBase(str(kb_path))

    if args.mbids_json:
        mbids_path = PROJECT_ROOT / args.mbids_json
        mbids = _load_mbids_from_json(mbids_path)
        results = [
            SearchResult(mbid=m, path_cost=0.0, preference_score=0.0, combined_score=0.0) for m in mbids
        ]
        title_note = f"from {mbids_path.name} ({len(mbids)} songs)"
    else:
        profile = _load_profile(PROJECT_ROOT / args.profile)
        rules = build_rules(profile)
        weights = get_default_weights(rules)
        base_scorer = PreferenceScorer(rules, weights)
        use_ml = args.use_ml_scorer and (PROJECT_ROOT / args.ml_scorer_artifact).exists()
        if use_ml:
            scorer = build_scorer_with_optional_ml(
                base_scorer,
                artifact_path=str(PROJECT_ROOT / args.ml_scorer_artifact),
                blend_weight=0.5,
            )
        else:
            scorer = base_scorer

        retrieval_k = max(int(args.k), int(args.cluster_pool_size))
        results = _retrieve_pool_ucs(
            kb,
            scorer,
            args.query_mbid,
            retrieval_k=retrieval_k,
            alpha=args.alpha,
            beta=args.beta,
            max_degree=args.max_degree,
        )
        title_note = f"query {args.query_mbid[:8]}… pool={len(results)}"

    if not results:
        print("No songs in pool; nothing to plot.")
        return

    mbids = [r.mbid for r in results]
    feature_spec = FeatureVectorSpec()
    kmeans_cfg = KMeansConfig(k=args.cluster_k, seed=args.cluster_seed, max_iters=args.cluster_max_iters)

    vectors, _vocab = build_feature_vectors(kb, mbids, spec=feature_spec)
    assignments = kmeans_cluster(vectors, config=kmeans_cfg)
    cluster_ids = np.array([assignments[m] for m in mbids], dtype=int)

    X = np.array([vectors[m] for m in mbids], dtype=float)
    proj = pca_project_2d(X)

    labels: list[str] | None = None
    if not args.no_labels and args.max_labels > 0:
        labels = [_song_label(kb, m) for m in mbids]

    title = f"Module 5 clusters (K={kmeans_cfg.k}, PCA 2D)\n{title_note}"
    plot_cluster_scatter(
        proj,
        cluster_ids,
        labels,
        out_path,
        title=title,
        max_labels=args.max_labels,
    )


if __name__ == "__main__":
    main()
