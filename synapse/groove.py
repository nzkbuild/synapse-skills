"""Synapse Groove — Outcome-based learning for skill routing.

Tracks whether routed skills were helpful, auto-adjusts future routing
weights based on accumulated outcomes. Per-skill, per-project tracking.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from synapse.config import (
    GROOVE_MAX_BOOST, GROOVE_MIN_RATINGS,
    get_outcomes_path, get_last_routing_path,
)


# ============================================================================
# Data persistence
# ============================================================================

def load_outcomes():
    """Load outcomes data from disk."""
    path = get_outcomes_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Warning: Failed to load outcomes: {e}", file=sys.stderr)
        return {}


def save_outcomes(data):
    """Persist outcomes data to disk."""
    path = get_outcomes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def save_last_routing(skill_ids, task_text):
    """Cache last routing result for --rate to reference."""
    path = get_last_routing_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "skills": skill_ids,
        "task": task_text,
        "timestamp": datetime.now().isoformat(),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_last_routing():
    """Load last routing result for --rate."""
    path = get_last_routing_path()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================================
# Outcome recording
# ============================================================================

def _detect_project():
    """Auto-detect project name from current directory."""
    cwd = Path.cwd()
    # Check for common project indicators
    for marker in ("pyproject.toml", "package.json", "Cargo.toml", ".git"):
        if (cwd / marker).exists():
            return cwd.name
    return None


def record_outcome(skill_ids, rating, project_name=None):
    """Record a routing outcome.

    Args:
        skill_ids: list of skill IDs that were routed
        rating: "good" or "bad"
        project_name: optional project name for per-project tracking
    """
    if rating not in ("good", "bad"):
        return

    outcomes = load_outcomes()
    today = datetime.now().strftime("%Y-%m-%d")

    for sid in skill_ids:
        if sid not in outcomes:
            outcomes[sid] = {
                "helpful": 0, "unhelpful": 0, "total": 0,
                "score": 0.0, "last_used": today,
                "by_project": {},
            }

        entry = outcomes[sid]
        entry["last_used"] = today
        entry["total"] += 1

        if rating == "good":
            entry["helpful"] += 1
        else:
            entry["unhelpful"] += 1

        # Recompute score
        total = entry["total"]
        if total > 0:
            entry["score"] = round((entry["helpful"] - entry["unhelpful"]) / total, 3)

        # Per-project tracking
        if project_name:
            if project_name not in entry["by_project"]:
                entry["by_project"][project_name] = {"helpful": 0, "unhelpful": 0}
            proj = entry["by_project"][project_name]
            if rating == "good":
                proj["helpful"] += 1
            else:
                proj["unhelpful"] += 1

    save_outcomes(outcomes)


# ============================================================================
# Groove scoring
# ============================================================================

def get_groove_scores(project_name=None):
    """Compute per-skill groove boosts/penalties.

    Returns: dict mapping skill_id → float score in [-GROOVE_MAX_BOOST, +GROOVE_MAX_BOOST]

    Project-specific outcomes are weighted 2× vs global.
    Scores only apply after GROOVE_MIN_RATINGS total ratings.
    """
    outcomes = load_outcomes()
    scores = {}

    for sid, entry in outcomes.items():
        total = entry.get("total", 0)
        if total < GROOVE_MIN_RATINGS:
            continue

        # Global score
        global_score = entry.get("score", 0.0)

        # Project-specific boost (weighted 2×)
        proj_score = 0.0
        if project_name and project_name in entry.get("by_project", {}):
            proj = entry["by_project"][project_name]
            proj_total = proj.get("helpful", 0) + proj.get("unhelpful", 0)
            if proj_total > 0:
                proj_score = (proj["helpful"] - proj["unhelpful"]) / proj_total

        # Weighted average: global + 2× project
        if proj_score != 0.0:
            combined = (global_score + 2 * proj_score) / 3
        else:
            combined = global_score

        # Scale to GROOVE_MAX_BOOST and clamp
        groove = combined * GROOVE_MAX_BOOST
        groove = max(-GROOVE_MAX_BOOST, min(GROOVE_MAX_BOOST, groove))

        if abs(groove) > 0.01:  # Skip negligible scores
            scores[sid] = round(groove, 2)

    return scores


# ============================================================================
# Stats
# ============================================================================

def get_stats(top_n=20):
    """Aggregate routing analytics.

    Returns dict with:
        - total_ratings: int
        - total_skills_rated: int
        - satisfaction_rate: float (0-1)
        - top_skills: list of (skill_id, helpful, unhelpful, total, score)
        - worst_skills: list of (skill_id, helpful, unhelpful, total, score)
    """
    outcomes = load_outcomes()
    if not outcomes:
        return {
            "total_ratings": 0,
            "total_skills_rated": 0,
            "satisfaction_rate": 0.0,
            "top_skills": [],
            "worst_skills": [],
        }

    total_helpful = sum(e.get("helpful", 0) for e in outcomes.values())
    total_unhelpful = sum(e.get("unhelpful", 0) for e in outcomes.values())
    total_ratings = total_helpful + total_unhelpful

    # Sort by score descending
    rated = [
        (sid, e.get("helpful", 0), e.get("unhelpful", 0),
         e.get("total", 0), e.get("score", 0.0))
        for sid, e in outcomes.items()
        if e.get("total", 0) >= GROOVE_MIN_RATINGS
    ]
    rated.sort(key=lambda x: x[4], reverse=True)

    return {
        "total_ratings": total_ratings,
        "total_skills_rated": len(outcomes),
        "satisfaction_rate": round(total_helpful / max(total_ratings, 1), 3),
        "top_skills": rated[:top_n],
        "worst_skills": list(reversed(rated[-top_n:])) if rated else [],
    }
