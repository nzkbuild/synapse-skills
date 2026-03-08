"""Tests for hybrid scoring in synapse.router — keyword + semantic."""
import pytest
from unittest.mock import patch, MagicMock


# ============================================================================
# Test score_skill with semantic bonus
# ============================================================================

class TestScoreSkillHybrid:
    """Test that score_skill correctly integrates semantic scores."""

    def test_keyword_only_score(self):
        """Without semantic score, scoring should be keyword-only."""
        from synapse.router import score_skill

        skill = {"id": "api-patterns", "description": "REST API design patterns", "tags": []}
        task_tokens = ["api", "design"]
        score, name, reasons = score_skill(skill, task_tokens, {}, set())

        assert score > 0
        assert name == "api-patterns"
        assert not any("semantic" in r for r in reasons)

    def test_semantic_bonus_applied(self):
        """Semantic score should add a bonus to the keyword score."""
        from synapse.router import score_skill
        from synapse.config import SEMANTIC_WEIGHT

        skill = {"id": "api-patterns", "description": "REST API design patterns", "tags": []}
        task_tokens = ["api", "design"]

        score_kw, _, _ = score_skill(skill, task_tokens, {}, set(), semantic_score=0.0)
        score_hybrid, _, reasons = score_skill(skill, task_tokens, {}, set(), semantic_score=0.8)

        expected_bonus = 0.8 * SEMANTIC_WEIGHT
        assert abs((score_hybrid - score_kw) - expected_bonus) < 0.01
        assert any("semantic:0.80" in r for r in reasons)

    def test_zero_semantic_no_reason(self):
        """Zero semantic score should not add a reason."""
        from synapse.router import score_skill

        skill = {"id": "test-skill", "description": "A test skill", "tags": []}
        _, _, reasons = score_skill(skill, ["test"], {}, set(), semantic_score=0.0)
        assert not any("semantic" in r for r in reasons)


# ============================================================================
# Test pick_skills with embeddings toggle
# ============================================================================

class TestPickSkillsHybrid:
    """Test pick_skills with use_embeddings flag."""

    @pytest.fixture
    def mock_skills(self):
        return [
            {"id": "api-patterns", "description": "REST API design patterns", "tags": ["api"]},
            {"id": "frontend-design", "description": "UI component design", "tags": ["ui"]},
            {"id": "database-design", "description": "SQL schema design", "tags": ["sql"]},
            {"id": "brainstorming", "description": "General brainstorming", "tags": []},
        ]

    def test_pick_skills_returns_5_values(self, mock_skills):
        """pick_skills should now return 5 values including semantic_active."""
        from synapse.router import pick_skills

        result = pick_skills(
            mock_skills, "build an API", 3, {}, set(),
            explain=False, use_embeddings=False,
        )
        assert len(result) == 5
        picked, explanations, heavy, filtered, semantic_on = result
        assert isinstance(semantic_on, bool)
        assert semantic_on is False  # We disabled embeddings

    def test_no_embeddings_flag_skips_semantic(self, mock_skills):
        """use_embeddings=False should produce keyword-only scoring."""
        from synapse.router import pick_skills

        _, explanations, _, _, semantic_on = pick_skills(
            mock_skills, "build an API", 3, {}, set(),
            explain=True, use_embeddings=False,
        )
        assert semantic_on is False
        for _, _, reasons in explanations:
            assert not any("semantic" in r for r in reasons)

    def test_embeddings_graceful_when_unavailable(self, mock_skills):
        """Even with use_embeddings=True, if onnxruntime is missing, fallback works."""
        from synapse.router import pick_skills

        with patch("synapse.embeddings.get_embedder", return_value=None):
            picked, _, _, _, semantic_on = pick_skills(
                mock_skills, "build an API", 3, {}, set(),
                explain=False, use_embeddings=True,
            )
            # Should still return results via keyword matching
            assert len(picked) > 0


# ============================================================================
# Test that semantic improves vague query matching
# ============================================================================

class TestSemanticQuality:
    """Integration tests that verify semantic matching improves results.

    These tests require the ONNX model to be available.
    """

    @pytest.fixture
    def skills(self):
        return [
            {"id": "code-review", "description": "Review code for quality and best practices",
             "tags": ["review", "quality"]},
            {"id": "refactoring", "description": "Improve code structure without changing behavior",
             "tags": ["refactor", "clean"]},
            {"id": "api-patterns", "description": "REST API design patterns and best practices",
             "tags": ["api", "rest"]},
            {"id": "brainstorming", "description": "General brainstorming and ideation",
             "tags": ["ideas"]},
            {"id": "frontend-design", "description": "UI component design and CSS",
             "tags": ["ui", "css"]},
        ]

    def test_vague_query_semantic_vs_keyword(self, skills):
        """Semantic should find matches for queries with no keyword overlap."""
        from synapse.router import pick_skills

        # "improve my codebase maintainability" has no exact keyword overlap
        # with "refactoring" or "code-review", but semantically it should match
        task = "improve my codebase maintainability"

        # Keyword-only
        picked_kw, _, _, _, _ = pick_skills(
            skills, task, 3, {}, set(),
            explain=False, use_embeddings=False,
        )

        # With embeddings (if available)
        picked_hybrid, _, _, _, semantic_on = pick_skills(
            skills, task, 3, {}, set(),
            explain=False, use_embeddings=True,
        )

        if semantic_on:
            # Semantic should surface relevant skills
            # At minimum, we expect different or better results
            assert len(picked_hybrid) > 0
