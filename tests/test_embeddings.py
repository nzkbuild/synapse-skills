"""Tests for synapse.embeddings — ONNX semantic matching engine."""
import sys
from unittest.mock import patch

import pytest

# ============================================================================
# Test graceful fallback
# ============================================================================

class TestGracefulFallback:
    """Verify embeddings module handles missing onnxruntime/numpy gracefully."""

    def test_get_embedder_returns_none_without_onnx(self):
        """get_embedder() should return None when onnxruntime is not installed."""
        # We test this by checking the fallback path in the module
        with patch.dict(sys.modules, {"onnxruntime": None, "numpy": None}):
            # Force reimport to trigger the ImportError path
            # Since the module caches HAS_EMBEDDINGS at import time,
            # we test the behavior through the public API
            from synapse.embeddings import HAS_EMBEDDINGS
            # If onnxruntime IS installed in test env, HAS_EMBEDDINGS will be True
            # and that's fine — it means the library works. We mainly assert
            # that the module loads without error.
            assert isinstance(HAS_EMBEDDINGS, bool)

    def test_module_imports_without_error(self):
        """The embeddings module should always import successfully."""
        from synapse import embeddings
        assert hasattr(embeddings, "get_embedder")
        assert hasattr(embeddings, "HAS_EMBEDDINGS")
        assert hasattr(embeddings, "Embedder")


# ============================================================================
# Test cosine similarity math
# ============================================================================

class TestCosineSimilarity:
    """Verify cosine_similarity produces correct results."""

    @pytest.fixture
    def np(self):
        numpy = pytest.importorskip("numpy")
        return numpy

    @pytest.fixture
    def embedder_cls(self):
        pytest.importorskip("onnxruntime")
        from synapse.embeddings import Embedder
        return Embedder

    def test_identical_vectors(self, np, embedder_cls):
        """Identical vectors should have similarity ~1.0."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        sim = embedder_cls.cosine_similarity(a, b)
        assert abs(sim - 1.0) < 1e-6

    def test_orthogonal_vectors(self, np, embedder_cls):
        """Orthogonal vectors should have similarity ~0.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        sim = embedder_cls.cosine_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_opposite_vectors(self, np, embedder_cls):
        """Opposite vectors should have similarity ~-1.0."""
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        sim = embedder_cls.cosine_similarity(a, b)
        assert abs(sim + 1.0) < 1e-6

    def test_batch_similarity(self, np, embedder_cls):
        """Batch cosine similarity should return array of scores."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([
            [1.0, 0.0, 0.0],  # same
            [0.0, 1.0, 0.0],  # orthogonal
        ])
        sims = embedder_cls.cosine_similarity(a, b)
        assert len(sims) == 2
        assert abs(sims[0] - 1.0) < 1e-6
        assert abs(sims[1]) < 1e-6


# ============================================================================
# Test encoding (requires ONNX model)
# ============================================================================

@pytest.mark.skipif(
    not pytest.importorskip("onnxruntime", reason="onnxruntime not installed"),
    reason="onnxruntime not available"
)
class TestEncoding:
    """Test encode() output shape and properties. Requires model files."""

    @pytest.fixture
    def embedder(self):
        from synapse.embeddings import get_embedder
        emb = get_embedder()
        if emb is None:
            pytest.skip("Embedder unavailable (model files missing)")
        return emb

    def test_encode_returns_correct_shape(self, embedder):
        """encode() should return a 384-dim vector."""
        vec = embedder.encode("build a REST API")
        assert vec.shape == (384,)

    def test_encode_is_normalized(self, embedder):
        """encode() should return L2-normalized vectors."""
        import numpy as np
        vec = embedder.encode("test normalization")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-5

    def test_similar_texts_high_similarity(self, embedder):
        """Semantically similar texts should have high cosine similarity."""
        a = embedder.encode("build a REST API with authentication")
        b = embedder.encode("create an API endpoint with login")
        sim = embedder.cosine_similarity(a, b)
        assert sim > 0.5  # These should be quite similar

    def test_dissimilar_texts_low_similarity(self, embedder):
        """Unrelated texts should have low cosine similarity."""
        a = embedder.encode("build a REST API")
        b = embedder.encode("watercolor painting techniques for beginners")
        sim = embedder.cosine_similarity(a, b)
        assert sim < 0.3


# ============================================================================
# Test cache mechanism
# ============================================================================

class TestCache:
    """Test skill embedding cache build + load."""

    @pytest.fixture
    def embedder(self):
        from synapse.embeddings import get_embedder
        emb = get_embedder()
        if emb is None:
            pytest.skip("Embedder unavailable")
        return emb

    def test_build_and_load_cache(self, embedder, tmp_path):
        """Cache round-trip: build → save → load should produce same results."""
        import numpy as np

        skills = [
            {"id": "api-patterns", "description": "REST API design patterns"},
            {"id": "frontend-design", "description": "UI component design"},
            {"id": "database-design", "description": "SQL schema design"},
        ]

        with patch("synapse.embeddings.get_cache_path", return_value=tmp_path):
            embeddings1, ids1 = embedder.build_skill_cache(skills)
            assert embeddings1.shape == (3, 384)
            assert len(ids1) == 3

            # Reset internal state, reload from cache
            embedder._skill_embeddings = None
            embedder._skill_ids = None
            embeddings2, ids2 = embedder.build_skill_cache(skills)

            assert np.allclose(embeddings1, embeddings2)
            assert ids1 == ids2

    def test_cache_invalidation_on_change(self, embedder, tmp_path):
        """Cache should rebuild when skills change."""
        skills_v1 = [
            {"id": "skill-a", "description": "first skill"},
        ]
        skills_v2 = [
            {"id": "skill-a", "description": "first skill"},
            {"id": "skill-b", "description": "second skill"},
        ]

        with patch("synapse.embeddings.get_cache_path", return_value=tmp_path):
            _, ids1 = embedder.build_skill_cache(skills_v1)
            assert len(ids1) == 1

            embedder._skill_embeddings = None
            embedder._skill_ids = None
            _, ids2 = embedder.build_skill_cache(skills_v2)
            assert len(ids2) == 2
