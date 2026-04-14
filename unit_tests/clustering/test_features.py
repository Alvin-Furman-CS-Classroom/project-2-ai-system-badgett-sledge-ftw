import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from knowledge_base_wrapper import KnowledgeBase
from clustering.features import FeatureVectorSpec, build_feature_vectors


def test_build_feature_vectors_has_consistent_dim():
    kb_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    kb = KnowledgeBase(str(kb_path))

    mbids = ["test-mbid-001", "test-mbid-002", "test-mbid-003"]
    vectors, vocab = build_feature_vectors(kb, mbids, spec=FeatureVectorSpec())

    assert set(vectors.keys()) == set(mbids)
    assert isinstance(vocab, list)
    for m in mbids:
        assert len(vectors[m]) == len(vocab)


def test_build_feature_vectors_deterministic_vocab_order():
    kb_path = Path(__file__).parent.parent / "fixtures" / "test_knowledge_base.json"
    kb = KnowledgeBase(str(kb_path))
    mbids = ["test-mbid-001", "test-mbid-002", "test-mbid-003"]

    v1, vocab1 = build_feature_vectors(kb, mbids)
    v2, vocab2 = build_feature_vectors(kb, mbids)
    assert vocab1 == vocab2
    assert v1 == v2

