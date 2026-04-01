from typing import Iterable, List

from search.pipeline import SearchResult

from .artifacts import RerankerArtifact
from .learned_scorer import _feature_keys_for_mbid


def rerank_results_with_artifact(
    kb,
    results: Iterable[SearchResult],
    artifact: RerankerArtifact,
) -> List[SearchResult]:
    """
    Return a new list of SearchResult objects re-ordered by a reranker artifact.

    This treats the reranker as a second-stage model:
        - Input: existing SearchResult list (from UCS + preference blend).
        - Output: the same results, sorted by a learned score derived from
          feature weights in the artifact.

    The current implementation mirrors the feature-based approach used by the
    learned scorer: each candidate's MBID is mapped to a set of features, and
    the reranker score is the sum of feature weights for those features.
    """
    if not artifact.weights:
        # Nothing to do; return results unchanged.
        return list(results)

    weights = artifact.weights
    scored: List[SearchResult] = []

    tmp: List[tuple[SearchResult, float]] = []
    for r in results:
        features = _feature_keys_for_mbid(kb, r.mbid)
        score = 0.0
        for fk in features:
            w = weights.get(fk)
            if w is not None:
                score += w
        tmp.append((r, score))

    # Sort by reranker score descending; tie-break by original combined_score and mbid.
    tmp.sort(key=lambda pair: (-pair[1], -pair[0].combined_score, pair[0].mbid))

    for r, _ in tmp:
        scored.append(r)

    return scored

