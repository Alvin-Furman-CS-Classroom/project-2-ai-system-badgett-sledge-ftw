"""
Rule-based scorer for Module 2: scores songs using logical rules and a weight vector.
"""

from typing import Dict, List, Tuple, TYPE_CHECKING

from preferences.rules import Rule, evaluate_rule, get_default_weights

if TYPE_CHECKING:
    from knowledge_base_wrapper import KnowledgeBase


class PreferenceScorer:
    """
    Scores songs by evaluating rule-based preferences against the knowledge base.
    Holds rules and weights; can use initial (equal) weights or refined weights from ratings.
    """

    def __init__(
        self,
        rules: List[Rule],
        weights: Dict[str, float],
    ) -> None:
        """
        Args:
            rules: List of Rule objects (e.g. from build_rules(profile)).
            weights: Dict mapping rule_id -> non-negative weight. Can be from get_default_weights(rules)
                     or refined from user ratings.
        """
        self.rules = rules
        self.weights = weights

    def score(self, song_mbid: str, kb: "KnowledgeBase") -> float:
        """
        Compute preference score for one song.
        Returns weighted sum of rule scores (0 or 1 per rule).
        """
        total = 0.0
        for rule in self.rules:
            w = self.weights.get(rule.rule_id, 0.0)
            total += w * evaluate_rule(rule, song_mbid, kb)
        return total

    def score_all(
        self,
        song_mbids: List[str],
        kb: "KnowledgeBase",
    ) -> List[Tuple[str, float]]:
        """
        Score multiple songs; returns list of (mbid, score) tuples.
        """
        return [(mbid, self.score(mbid, kb)) for mbid in song_mbids]
