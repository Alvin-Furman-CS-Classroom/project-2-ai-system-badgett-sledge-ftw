"""
Logical rules and weight vector for Module 2 rule-based preference system.

Builds rules from a PreferenceProfile, evaluates them against the knowledge base,
and provides default (equal) weights per rule.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase

from preferences.survey import PreferenceProfile


@dataclass
class Rule:
    """
    A single preference rule: condition over one KB fact.
    rule_id identifies the rule for weights; fact_type and target define the condition.
    """

    rule_id: str
    fact_type: str  # e.g. 'has_genre', 'has_mood', 'has_danceable', ...
    target: Any  # list of allowed values (genre/mood), single value (categorical), or (min, max) for loudness

    def __post_init__(self) -> None:
        # Loudness range: ensure (min, max) ordering
        if (
            self.fact_type == "has_loudness"
            and self.target is not None
            and isinstance(self.target, (list, tuple))
            and len(self.target) == 2
        ):
            a, b = self.target[0], self.target[1]
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > b:
                self.target = (b, a)
            else:
                self.target = (float(a), float(b))


def build_rules(profile: PreferenceProfile) -> List[Rule]:
    """
    Build a list of logical rules from a preference profile.
    Only includes rules for dimensions where the user expressed a preference.
    """
    rules: List[Rule] = []

    if profile.preferred_genres:
        rules.append(
            Rule(rule_id="genre", fact_type="has_genre", target=[g.lower() for g in profile.preferred_genres])
        )

    if profile.preferred_moods:
        rules.append(
            Rule(rule_id="mood", fact_type="has_mood", target=[m.lower() for m in profile.preferred_moods])
        )

    if profile.danceable and profile.danceable.lower() not in ("any", ""):
        rules.append(
            Rule(rule_id="danceable", fact_type="has_danceable", target=profile.danceable.lower())
        )

    if profile.voice_instrumental and profile.voice_instrumental.lower() not in ("any", ""):
        rules.append(
            Rule(rule_id="voice_instrumental", fact_type="has_voice_instrumental", target=profile.voice_instrumental.lower())
        )

    if profile.timbre and profile.timbre.lower() not in ("any", ""):
        rules.append(
            Rule(rule_id="timbre", fact_type="has_timbre", target=profile.timbre.lower())
        )

    if profile.loudness_min is not None and profile.loudness_max is not None:
        lo, hi = profile.loudness_min, profile.loudness_max
        if lo > hi:
            lo, hi = hi, lo
        rules.append(
            Rule(rule_id="loudness", fact_type="has_loudness", target=(lo, hi))
        )

    return rules


def evaluate_rule(rule: Rule, mbid: str, kb: "KnowledgeBase") -> float:
    """
    Evaluate a single rule for a song. Returns 0.0 (not satisfied) or 1.0 (satisfied).
    Optional: partial score for genre/mood (fraction of preferred that match); here we use 0/1.
    """
    value = kb.get_fact(rule.fact_type, mbid)

    if rule.fact_type == "has_genre":
        if not value:
            return 0.0
        song_genres: Set[str] = set(g.lower() for g in (value if isinstance(value, list) else [value]))
        preferred: Set[str] = set(rule.target)
        return 1.0 if (song_genres & preferred) else 0.0

    if rule.fact_type == "has_mood":
        if not value:
            return 0.0
        song_moods: Set[str] = set(m.lower() for m in (value if isinstance(value, list) else [value]))
        preferred_m: Set[str] = set(rule.target)
        return 1.0 if (song_moods & preferred_m) else 0.0

    if rule.fact_type in ("has_danceable", "has_voice_instrumental", "has_timbre"):
        if value is None:
            return 0.0
        target_str = (rule.target if isinstance(rule.target, str) else str(rule.target)).lower()
        return 1.0 if str(value).lower() == target_str else 0.0

    if rule.fact_type == "has_loudness":
        if value is None:
            return 0.0
        try:
            v = float(value)
            lo, hi = rule.target[0], rule.target[1]
            return 1.0 if lo <= v <= hi else 0.0
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_default_weights(rules: List[Rule], normalize: bool = True) -> Dict[str, float]:
    """
    Return equal weight per rule. If normalize is True, weights sum to 1.0.
    """
    if not rules:
        return {}
    n = len(rules)
    w = 1.0 / n if normalize else 1.0
    return {r.rule_id: w for r in rules}
