"""
Unit tests for Beam Search (optional Module 3 variant).
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from knowledge_base_wrapper import KnowledgeBase
from search.beam import beam_topk
from search.costs import DissimilarityWeights
from search.ucs import ucs_topk


@pytest.fixture
def kb_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    return KnowledgeBase(str(fixture_path))


@pytest.fixture
def kb_linear_loudness():
    minimal = {
        "songs": {"q": {}, "a": {}, "b": {}, "c": {}},
        "facts": {
            "has_genre": {
                "q": ["rock"],
                "a": ["rock"],
                "b": ["rock"],
                "c": ["rock"],
            },
            "has_loudness": {"q": -10.0, "a": -10.0, "b": -5.0, "c": -20.0},
        },
        "indexes": {
            "by_genre": {"rock": ["q", "a", "b", "c"]},
            "by_danceable": {},
            "by_voice_instrumental": {},
            "by_timbre": {},
            "by_mood": {},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(minimal, f)
        path = f.name
    try:
        yield KnowledgeBase(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestBeamTopk:
    def test_excludes_query(self, kb_fixture):
        out = beam_topk(kb_fixture, "test-mbid-001", k=3)
        assert "test-mbid-001" not in [m for m, _ in out]

    def test_length_at_most_k(self, kb_fixture):
        assert len(beam_topk(kb_fixture, "test-mbid-001", k=2)) <= 2

    def test_cost_ordering(self, kb_fixture):
        out = beam_topk(kb_fixture, "test-mbid-001", k=4)
        costs = [c for _, c in out]
        assert costs == sorted(costs)

    def test_deterministic(self, kb_fixture):
        a = beam_topk(kb_fixture, "test-mbid-001", k=3, beam_width=3, max_depth=4)
        b = beam_topk(kb_fixture, "test-mbid-001", k=3, beam_width=3, max_depth=4)
        assert a == b

    def test_k_zero_empty(self, kb_fixture):
        assert beam_topk(kb_fixture, "test-mbid-001", k=0) == []

    def test_invalid_query_raises(self, kb_fixture):
        with pytest.raises(ValueError, match="Unknown"):
            beam_topk(kb_fixture, "missing", k=1)

    def test_invalid_beam_width_raises(self, kb_fixture):
        with pytest.raises(ValueError, match="beam_width"):
            beam_topk(kb_fixture, "test-mbid-001", k=1, beam_width=0)

    def test_invalid_max_depth_raises(self, kb_fixture):
        with pytest.raises(ValueError, match="max_depth"):
            beam_topk(kb_fixture, "test-mbid-001", k=1, max_depth=-1)

    def test_matches_ucs_on_simple_clique(self, kb_linear_loudness):
        w = DissimilarityWeights()
        u = ucs_topk(kb_linear_loudness, "q", k=3, weights=w)
        b = beam_topk(kb_linear_loudness, "q", k=3, beam_width=10, max_depth=3, weights=w)
        assert b == u
