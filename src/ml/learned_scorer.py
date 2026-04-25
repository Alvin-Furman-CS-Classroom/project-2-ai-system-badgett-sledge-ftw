from typing import Optional, Set

from preferences import PreferenceScorer

from .artifacts import ScorerArtifact


def _feature_keys_for_mbid(kb, mbid: str) -> Set[str]:
    """
    Extract the same family of feature keys used during training.

    This mirrors the logic in ml.train_module4, but is kept local so that the
    scorer can work with any KnowledgeBase-like object that exposes get_fact().
    """
    features: Set[str] = set()

    genres = kb.get_fact("has_genre", mbid)
    if isinstance(genres, list):
        for g in genres:
            features.add(f"genre:{str(g).strip().lower()}")
    elif genres is not None:
        features.add(f"genre:{str(genres).strip().lower()}")

    moods = kb.get_fact("has_mood", mbid)
    if isinstance(moods, list):
        for m in moods:
            features.add(f"mood:{str(m).strip().lower()}")
    elif moods is not None:
        features.add(f"mood:{str(moods).strip().lower()}")

    danceable = kb.get_fact("has_danceable", mbid)
    if danceable is not None:
        features.add(f"danceable:{str(danceable).strip().lower()}")

    vi = kb.get_fact("has_voice_instrumental", mbid)
    if vi is not None:
        features.add(f"vi:{str(vi).strip().lower()}")

    timbre = kb.get_fact("has_timbre", mbid)
    if timbre is not None:
        features.add(f"timbre:{str(timbre).strip().lower()}")

    loudness = kb.get_fact("has_loudness", mbid)
    if isinstance(loudness, (int, float)):
        if loudness <= -20:
            bucket = "quiet"
        elif loudness >= -8:
            bucket = "loud"
        else:
            bucket = "medium"
        features.add(f"loudness_bucket:{bucket}")

    features.add("bias")
    return features


class LearnedPreferenceScorer:
    """
    Wrapper that is compatible with PreferenceScorer's score(mbid, kb) API.

    If a ScorerArtifact with feature weights is provided, this scorer computes
    a learned feature score and blends it with the underlying rule-based score.
    Otherwise, it behaves exactly like the base PreferenceScorer.
    """

    def __init__(
        self,
        base_scorer: PreferenceScorer,
        artifact: Optional[ScorerArtifact] = None,
        *,
        blend_weight: float = 0.5,
    ) -> None:
        """
        Args:
            base_scorer: Existing Module 2 PreferenceScorer instance.
            artifact: Optional ScorerArtifact loaded from JSON. If None or if
                it contains no weights, learned_score will be treated as 0.0.
            blend_weight: λ in the blend:

                final = (1 - λ) * rule_score + λ * learned_score

                λ=0.0 means "rules only"; λ=1.0 means "learned only".
        """
        self._base_scorer = base_scorer
        self._artifact = artifact
        self._blend_weight = float(blend_weight)

    @property
    def artifact(self) -> Optional[ScorerArtifact]:
        """Return the attached ScorerArtifact, if any."""
        return self._artifact

    @property
    def blend_weight(self) -> float:
        """Return the current blend weight λ."""
        return self._blend_weight

    def _learned_score(self, mbid: str, kb) -> float:
        """Compute learned feature-based score from the artifact, if available."""
        if self._artifact is None or not self._artifact.weights:
            return 0.0
        weights = self._artifact.weights
        score = 0.0
        for fk in _feature_keys_for_mbid(kb, mbid):
            w = weights.get(fk)
            if w is not None:
                score += w
        return score

    def score(self, mbid: str, kb) -> float:
        """
        Score a song by blending rule-based and learned feature scores.

        If no artifact is attached (or it has no weights), this reduces to the
        underlying PreferenceScorer.score(mbid, kb) for full backward
        compatibility.
        """
        rule_score = self._base_scorer.score(mbid, kb)
        learned = self._learned_score(mbid, kb)

        if self._artifact is None or not self._artifact.weights:
            return rule_score

        lam = self._blend_weight
        return (1.0 - lam) * rule_score + lam * learned


