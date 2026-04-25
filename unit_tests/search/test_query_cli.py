"""
Unit tests for Module 3 query CLI algorithm switching.

These tests validate that the CLI's --algorithm switch routes to:
- UCS path (find_similar)
- Beam path (beam_topk + pipeline blend)

We avoid interactive input by testing the extracted helper
`search.query_cli._retrieve_results(...)`.
"""

from __future__ import annotations

import sys
import builtins
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from search import query_cli
from search.pipeline import SearchResult


class StubScorer:
    """Minimal scorer for pipeline blending tests."""

    def __init__(self, scores: Dict[str, float]):
        self._scores = scores

    def score(self, mbid: str, kb: Any) -> float:
        return self._scores.get(mbid, 0.0)


class DummyKB:
    """Placeholder KB object; not used by our monkeypatched retrieval functions."""

    pass


def test_algorithm_switch_uses_find_similar(monkeypatch: pytest.MonkeyPatch) -> None:
    kb = DummyKB()
    scorer = StubScorer({"x": 0.7})
    args = SimpleNamespace(
        algorithm="ucs",
        k=1,
        alpha=1.0,
        beta=1.0,
        max_degree=10,
        beam_width=5,
        beam_depth=3,
    )

    called = {"find_similar": 0, "beam_topk": 0}

    def fake_find_similar(*, kb: Any, query_mbid: str, scorer: Any, k: int, alpha: float, beta: float, max_degree: int):
        called["find_similar"] += 1
        return [
            SearchResult(
                mbid="x",
                path_cost=0.2,
                preference_score=0.7,
                combined_score=0.9,
            )
        ]

    def fake_beam_topk(*args: Any, **kwargs: Any):
        called["beam_topk"] += 1
        raise AssertionError("beam_topk should not be called in UCS mode")

    monkeypatch.setattr(query_cli, "find_similar", fake_find_similar)
    monkeypatch.setattr(query_cli, "beam_topk", fake_beam_topk)

    out = query_cli._retrieve_results(kb, scorer, "query-mbid", args)

    assert called["find_similar"] == 1
    assert called["beam_topk"] == 0
    assert len(out) == 1
    assert isinstance(out[0], SearchResult)
    assert out[0].mbid == "x"


def test_algorithm_switch_uses_beam_topk(monkeypatch: pytest.MonkeyPatch) -> None:
    kb = DummyKB()
    scorer = StubScorer({"a": 0.2, "b": 0.9})
    args = SimpleNamespace(
        algorithm="beam",
        k=2,
        alpha=1.0,
        beta=1.0,
        max_degree=10,
        beam_width=4,
        beam_depth=2,
    )

    called = {"find_similar": 0, "beam_topk": 0}

    def fake_find_similar(*args: Any, **kwargs: Any):
        called["find_similar"] += 1
        raise AssertionError("find_similar should not be called in Beam mode")

    def fake_beam_topk(*, kb: Any, query_mbid: str, k: int, beam_width: int, max_depth: int, max_degree: int):
        called["beam_topk"] += 1
        # Return raw (mbid, path_cost) candidates; ranking helper will blend with scorer.
        return [("a", 0.3), ("b", 0.1)]

    monkeypatch.setattr(query_cli, "find_similar", fake_find_similar)
    monkeypatch.setattr(query_cli, "beam_topk", fake_beam_topk)

    out = query_cli._retrieve_results(kb, scorer, "query-mbid", args)

    assert called["beam_topk"] == 1
    assert called["find_similar"] == 0
    assert len(out) <= 2
    assert all(isinstance(r, SearchResult) for r in out)
    assert all(isinstance(r.combined_score, float) for r in out)


def test_beam_mode_blends_and_sorts_by_combined_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    With known raw path costs and known preference scores, ensure the CLI's
    beam-mode ranking uses the blend formula and returns the expected order.
    """
    kb = DummyKB()
    # Preference scores chosen so b should be preferred.
    scorer = StubScorer({"a": 0.2, "b": 0.9})
    args = SimpleNamespace(
        algorithm="beam",
        k=2,
        alpha=1.0,
        beta=1.0,
        max_degree=10,
        beam_width=4,
        beam_depth=2,
    )

    def fake_find_similar(*args: Any, **kwargs: Any):
        raise AssertionError("find_similar should not be called in Beam mode")

    def fake_beam_topk(*, kb: Any, query_mbid: str, k: int, beam_width: int, max_depth: int, max_degree: int):
        # costs: a higher than b (0.3 vs 0.1)
        return [("a", 0.3), ("b", 0.1)]

    monkeypatch.setattr(query_cli, "find_similar", fake_find_similar)
    monkeypatch.setattr(query_cli, "beam_topk", fake_beam_topk)

    out = query_cli._retrieve_results(kb, scorer, "query-mbid", args)

    assert len(out) == 2
    # Expected combined:
    # costs normalized: a=1.0, b=0.0 ; prefs normalized: a=0.0, b=1.0
    # combined = -alpha*c_norm + beta*p_norm => a = -1.0, b = +1.0 => b ranks first.
    assert out[0].mbid == "b"
    assert out[1].mbid == "a"


def test_resolve_query_uses_get_mbid_by_song_when_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    If get_mbid_by_song resolves the song, _resolve_query_to_mbid should return it
    without calling find_songs_by_name.
    """

    class KB:
        def __init__(self):
            self.find_calls = 0

        def get_mbid_by_song(self, track_name: str, artist_name: Any = None) -> str:
            return "mbid-123"

        def get_song(self, mbid: str) -> Dict[str, str]:
            return {"artist": "ArtistX", "track": "TrackY"}

        def find_songs_by_name(self, track_name: str, artist_name: Any = None) -> list[str]:
            self.find_calls += 1
            return []

    kb = KB()
    inputs = iter(["My Track", "My Artist"])

    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))

    resolved = query_cli._resolve_query_to_mbid(kb)  # type: ignore[arg-type]
    assert resolved is not None
    mbid, artist, track = resolved
    assert mbid == "mbid-123"
    assert artist == "ArtistX"
    assert track == "TrackY"
    assert kb.find_calls == 0


def test_resolve_query_prompts_when_multiple_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    If get_mbid_by_song returns None and multiple candidates exist, the function
    should prompt for a pick and return the chosen MBID.
    """

    class KB:
        def __init__(self):
            self.choices = []

        def get_mbid_by_song(self, track_name: str, artist_name: Any = None) -> Any:
            return None

        def find_songs_by_name(self, track_name: str, artist_name: Any = None) -> list[str]:
            return ["cand-1", "cand-2"]

        def get_song(self, mbid: str) -> Dict[str, str]:
            # Make KB metadata empty so it falls back to user input.
            return {"artist": "", "track": ""}

    kb = KB()
    # User inputs: track, artist, pick number.
    inputs = iter(["Ms Jack", "Outkast", "2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))

    resolved = query_cli._resolve_query_to_mbid(kb)  # type: ignore[arg-type]
    assert resolved is not None
    mbid, artist, track = resolved
    assert mbid == "cand-2"
    assert artist == "Outkast"
    assert track == "Ms Jack"

