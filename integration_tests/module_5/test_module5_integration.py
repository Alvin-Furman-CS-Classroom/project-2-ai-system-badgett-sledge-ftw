import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from knowledge_base_wrapper import KnowledgeBase
from preferences.rules import build_rules, get_default_weights
from preferences.scorer import PreferenceScorer
from preferences.survey import PreferenceProfile
from search.pipeline import find_similar

from clustering.kmeans import KMeansConfig
from clustering.organize import cluster_and_organize


def test_module5_clusters_do_not_change_candidate_membership():
    kb_path = Path(__file__).parent.parent.parent / "unit_tests" / "fixtures" / "test_knowledge_base.json"
    kb = KnowledgeBase(str(kb_path))

    profile = PreferenceProfile(
        preferred_genres=["rock"],
        preferred_moods=["happy"],
        danceable=None,
        voice_instrumental=None,
        timbre=None,
        loudness_min=None,
        loudness_max=None,
    )
    rules = build_rules(profile)
    weights = get_default_weights(rules)
    scorer = PreferenceScorer(rules, weights)

    pool = find_similar(kb, "test-mbid-001", scorer, k=5)
    assert len(pool) > 0

    clustered = cluster_and_organize(
        kb,
        pool,
        top_k=3,
        kmeans=KMeansConfig(k=2, seed=343, max_iters=10),
    )
    out_mbids = [r.mbid for r in clustered.diversified]
    assert len(out_mbids) == 3
    assert set(out_mbids).issubset({r.mbid for r in pool})

