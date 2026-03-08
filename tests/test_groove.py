"""Tests for synapse.groove — Outcome-based learning."""
import json
import pytest
from unittest.mock import patch
from pathlib import Path


# ============================================================================
# Test outcome recording
# ============================================================================

class TestRecordOutcome:
    """Test record_outcome() data persistence."""

    def test_record_good_outcome(self, tmp_path):
        """Recording a good outcome should increment helpful count."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["api-patterns"], "good")
            data = load_outcomes()

        assert "api-patterns" in data
        assert data["api-patterns"]["helpful"] == 1
        assert data["api-patterns"]["unhelpful"] == 0
        assert data["api-patterns"]["total"] == 1
        assert data["api-patterns"]["score"] == 1.0

    def test_record_bad_outcome(self, tmp_path):
        """Recording a bad outcome should increment unhelpful count."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["frontend-design"], "bad")
            data = load_outcomes()

        assert data["frontend-design"]["unhelpful"] == 1
        assert data["frontend-design"]["score"] == -1.0

    def test_record_multiple_skills(self, tmp_path):
        """Recording should apply to all skill IDs in the list."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["skill-a", "skill-b", "skill-c"], "good")
            data = load_outcomes()

        assert len(data) == 3
        for sid in ("skill-a", "skill-b", "skill-c"):
            assert data[sid]["helpful"] == 1

    def test_record_accumulates(self, tmp_path):
        """Multiple recordings should accumulate correctly."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["skill-a"], "good")
            record_outcome(["skill-a"], "good")
            record_outcome(["skill-a"], "bad")
            data = load_outcomes()

        assert data["skill-a"]["helpful"] == 2
        assert data["skill-a"]["unhelpful"] == 1
        assert data["skill-a"]["total"] == 3
        assert abs(data["skill-a"]["score"] - 0.333) < 0.01

    def test_per_project_tracking(self, tmp_path):
        """Project-specific outcomes should be tracked separately."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["skill-a"], "good", project_name="my-project")
            data = load_outcomes()

        assert "my-project" in data["skill-a"]["by_project"]
        assert data["skill-a"]["by_project"]["my-project"]["helpful"] == 1

    def test_invalid_rating_ignored(self, tmp_path):
        """Invalid ratings should be silently ignored."""
        from synapse.groove import record_outcome, load_outcomes

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["skill-a"], "maybe")
            data = load_outcomes()

        assert data == {}


# ============================================================================
# Test groove scoring
# ============================================================================

class TestGrooveScoring:
    """Test get_groove_scores() computation."""

    def test_no_scores_below_min_ratings(self, tmp_path):
        """Skills with fewer than GROOVE_MIN_RATINGS should not get a score."""
        from synapse.groove import record_outcome, get_groove_scores

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            record_outcome(["skill-a"], "good")  # Only 1 rating
            record_outcome(["skill-a"], "good")  # Only 2 ratings
            scores = get_groove_scores()

        assert "skill-a" not in scores  # Need 3 minimum

    def test_positive_score_after_threshold(self, tmp_path):
        """Skills exceeding min ratings with good outcomes should get positive score."""
        from synapse.groove import record_outcome, get_groove_scores
        from synapse.config import GROOVE_MAX_BOOST

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            for _ in range(3):
                record_outcome(["skill-a"], "good")
            scores = get_groove_scores()

        assert "skill-a" in scores
        assert scores["skill-a"] > 0
        assert scores["skill-a"] <= GROOVE_MAX_BOOST

    def test_negative_score_for_bad_skills(self, tmp_path):
        """Skills with mostly bad outcomes should get negative score."""
        from synapse.groove import record_outcome, get_groove_scores

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            for _ in range(3):
                record_outcome(["skill-a"], "bad")
            scores = get_groove_scores()

        assert scores["skill-a"] < 0

    def test_project_specific_weighting(self, tmp_path):
        """Project-specific outcomes should be weighted 2x vs global."""
        from synapse.groove import record_outcome, get_groove_scores

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            # 3 good globally
            for _ in range(3):
                record_outcome(["skill-a"], "good", project_name="proj-a")

            score_with_project = get_groove_scores(project_name="proj-a")
            score_without_project = get_groove_scores(project_name="other-proj")

        # Both should be positive but project-specific should have same or higher boost
        assert score_with_project.get("skill-a", 0) >= score_without_project.get("skill-a", 0)


# ============================================================================
# Test stats
# ============================================================================

class TestStats:
    """Test get_stats() aggregation."""

    def test_empty_stats(self, tmp_path):
        """Stats with no data should return zeroed values."""
        from synapse.groove import get_stats

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            stats = get_stats()

        assert stats["total_ratings"] == 0
        assert stats["total_skills_rated"] == 0
        assert stats["satisfaction_rate"] == 0.0

    def test_stats_with_data(self, tmp_path):
        """Stats should compute correct aggregates."""
        from synapse.groove import record_outcome, get_stats

        outcomes_path = tmp_path / "outcomes.json"
        with patch("synapse.groove.get_outcomes_path", return_value=outcomes_path):
            for _ in range(4):
                record_outcome(["skill-a"], "good")
            record_outcome(["skill-a"], "bad")
            stats = get_stats()

        assert stats["total_ratings"] == 5
        assert stats["total_skills_rated"] == 1
        assert stats["satisfaction_rate"] == 0.8


# ============================================================================
# Test last routing cache
# ============================================================================

class TestLastRouting:
    """Test save/load last routing for --rate."""

    def test_round_trip(self, tmp_path):
        """Save and load should produce the same data."""
        from synapse.groove import save_last_routing, load_last_routing

        last_path = tmp_path / "last_routing.json"
        with patch("synapse.groove.get_last_routing_path", return_value=last_path):
            save_last_routing(["skill-a", "skill-b"], "build an API")
            result = load_last_routing()

        assert result["skills"] == ["skill-a", "skill-b"]
        assert result["task"] == "build an API"
        assert "timestamp" in result

    def test_load_missing_file(self, tmp_path):
        """Loading when no file exists should return None."""
        from synapse.groove import load_last_routing

        last_path = tmp_path / "nonexistent.json"
        with patch("synapse.groove.get_last_routing_path", return_value=last_path):
            result = load_last_routing()

        assert result is None


# ============================================================================
# Test router integration
# ============================================================================

class TestRouterGrooveIntegration:
    """Test that groove scores flow through the router correctly."""

    def test_groove_bonus_applied_in_score_skill(self):
        """Groove score should be added to final skill score."""
        from synapse.router import score_skill

        skill = {"id": "api-patterns", "description": "REST API design", "tags": []}
        score_base, _, _ = score_skill(skill, ["api"], {}, set(), groove_score=0.0)
        score_boosted, _, reasons = score_skill(skill, ["api"], {}, set(), groove_score=3.5)

        assert abs((score_boosted - score_base) - 3.5) < 0.01
        assert any("groove:+3.5" in r for r in reasons)

    def test_groove_penalty_in_reasons(self):
        """Negative groove score should show as penalty in reasons."""
        from synapse.router import score_skill

        skill = {"id": "test-skill", "description": "A test", "tags": []}
        _, _, reasons = score_skill(skill, ["test"], {}, set(), groove_score=-2.0)

        assert any("groove:-2.0" in r for r in reasons)
