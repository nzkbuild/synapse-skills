"""Synapse Router — Core skill matching and selection engine.

Features:
- Drift: Invisible skill routing
- Fuse: Hybrid keyword + semantic scoring (semantic in embeddings.py)
- Marq: Project profile integration
- Tracer: Memory integration
"""
import json
import re
import sys
from pathlib import Path

from synapse.config import (
    DEFAULT_BUNDLES, DEFAULT_MAX_SKILLS, FEEDBACK_CAP, HEAVY_SKILLS,
    MAX_SKILLS, MIN_SCORE, RELATIVE_THRESHOLD, SEMANTIC_WEIGHT,
    get_bundles_path, get_feedback_path, get_skills_root,
)

# ============================================================================
# Text Processing
# ============================================================================

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def tokenize(text):
    return [t for t in normalize(text).split() if t]


SYNONYM_MAP = {
    "auth": "authentication", "oauth": "authentication", "login": "authentication",
    "db": "database", "sql": "database",
    "ui": "frontend", "ux": "frontend",
    "perf": "performance", "opt": "optimization",
    "ops": "devops", "k8s": "kubernetes",
    "sec": "security", "cli": "command",
}

SECURITY_KEYWORDS = {
    "security", "vulnerability", "pentest", "penetration", "red-team", "redteam",
    "xss", "sqli", "sql-injection", "csrf", "bug-bounty", "owasp", "audit",
}

UI_KEYWORDS = {
    "ui", "ux", "design", "landing", "frontend", "website", "page", "component",
    "css", "style", "layout",
}

CATEGORY_FALLBACKS = {
    "security": "security-review",
    "frontend": "frontend-design",
    "backend": "api-patterns",
    "database": "database-design",
    "devops": "docker-expert",
    "testing": "test-driven-development",
    "default": "brainstorming",
}

CATEGORY_KEYWORDS = {
    "security": SECURITY_KEYWORDS,
    "frontend": UI_KEYWORDS,
    "backend": {"api", "server", "endpoint", "rest", "graphql", "backend", "microservice"},
    "database": {"database", "db", "sql", "postgres", "mongo", "redis", "schema", "migration"},
    "devops": {"docker", "kubernetes", "k8s", "deploy", "ci", "cd", "pipeline", "terraform", "aws"},
    "testing": {"test", "tdd", "qa", "playwright", "jest", "pytest", "coverage"},
}


def expand_tokens(tokens):
    expanded = list(tokens)
    for token in tokens:
        mapped = SYNONYM_MAP.get(token)
        if mapped and mapped not in expanded:
            expanded.append(mapped)
    return expanded


# ============================================================================
# Skill ID & Loading
# ============================================================================

def get_skill_id(skill):
    """Extract the canonical ID from a skill dict."""
    return skill.get("id") or skill.get("name") or ""


def load_bundles():
    """Load bundles from JSON file or return defaults."""
    bundles_file = get_bundles_path()
    if bundles_file.exists():
        try:
            with bundles_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"Warning: Failed to load bundles.json: {e}", file=sys.stderr)
    return DEFAULT_BUNDLES


def load_index(index_path):
    """Load skills index from JSON file, merging custom skills."""
    try:
        with index_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and "skills" in data:
            skills = data["skills"]
        elif isinstance(data, list):
            skills = data
        else:
            skills = []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in skills_index.json: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error: Failed to load skills index: {e}", file=sys.stderr)
        return []

    # Merge custom skills from .agent/skills/custom/
    custom_dir = Path.cwd() / ".agent" / "skills" / "custom"
    if custom_dir.exists():
        for skill_dir in custom_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skill_id = skill_dir.name
                    if not any(get_skill_id(s) == skill_id for s in skills):
                        desc = _parse_skill_description(skill_md)
                        skills.append({
                            "id": skill_id, "name": skill_id,
                            "description": desc, "path": str(skill_dir),
                            "category": "Custom", "source": "local",
                        })
    return skills


def _parse_skill_description(skill_md_path):
    """Extract description from SKILL.md frontmatter."""
    try:
        content = skill_md_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                frontmatter = content[3:end]
                for line in frontmatter.splitlines():
                    if line.strip().startswith("description:"):
                        return line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "Custom skill (no description)"


# ============================================================================
# Feedback
# ============================================================================

def load_feedback():
    """Load feedback scores from disk."""
    feedback_file = get_feedback_path()
    if not feedback_file.exists():
        return {}
    try:
        with feedback_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"Warning: Failed to load feedback: {e}", file=sys.stderr)
    return {}


def save_feedback(feedback):
    """Save feedback scores to disk."""
    feedback_file = get_feedback_path()
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    with feedback_file.open("w", encoding="utf-8") as handle:
        json.dump(feedback, handle, indent=2, sort_keys=True)


# ============================================================================
# Scoring (Fuse — keyword layer)
# ============================================================================

def should_filter_security(task_tokens, skill_name):
    """Filter security skills from non-security tasks."""
    task_has_security = any(t in SECURITY_KEYWORDS for t in task_tokens)
    if task_has_security:
        return False
    name = (skill_name or "").lower()
    return any(k in name for k in SECURITY_KEYWORDS)


def detect_task_category(task_tokens):
    """Detect dominant task category for smart fallback."""
    best_cat, best_count = "default", 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        overlap = sum(1 for t in task_tokens if t in keywords)
        if overlap > best_count:
            best_count = overlap
            best_cat = category
    return best_cat if best_count > 0 else "default"


def score_skill(skill, task_tokens, feedback, bundle_set,
                semantic_score=0.0, groove_score=0.0):
    """Score a skill against task tokens (Fuse: keyword + semantic + groove)."""
    name = get_skill_id(skill)
    description = skill.get("description") or ""
    path = skill.get("path") or ""
    tags = skill.get("tags") or []
    name_tokens = set(tokenize(name))
    desc_tokens = set(tokenize(description))
    path_tokens = set(tokenize(path))
    tag_tokens = set(t.lower() for t in tags)
    task_set = set(task_tokens)

    # Weighted overlap scoring
    name_overlap = len(task_set & (name_tokens | path_tokens))
    desc_overlap = len(task_set & desc_tokens)
    tag_overlap = len(task_set & tag_tokens)
    raw = (name_overlap * 3) + (desc_overlap * 1) + (tag_overlap * 2)

    # Normalize by skill token count to prevent length bias
    total_skill_tokens = len(name_tokens | desc_tokens | tag_tokens) or 1
    score = (raw / total_skill_tokens) * 10

    reasons = []
    for token in task_tokens:
        if token in name_tokens or token in path_tokens:
            if f"token:{token}" not in reasons:
                reasons.append(f"token:{token}")
        if token in desc_tokens:
            if f"desc:{token}" not in reasons:
                reasons.append(f"desc:{token}")
        if token in tag_tokens:
            if f"tag:{token}" not in reasons:
                reasons.append(f"tag:{token}")

    # Semantic similarity bonus (Fuse semantic layer)
    if semantic_score > 0:
        semantic_bonus = semantic_score * SEMANTIC_WEIGHT
        score += semantic_bonus
        reasons.append(f"semantic:{semantic_score:.2f}")

    # Groove outcome bonus/penalty
    if abs(groove_score) > 0.01:
        score += groove_score
        reasons.append(f"groove:{groove_score:+.1f}")

    if name in bundle_set:
        score += 5
        reasons.append("bundle:+5")

    boost = feedback.get(name)
    if isinstance(boost, (int, float)):
        score += min(max(boost, -FEEDBACK_CAP), FEEDBACK_CAP)
        reasons.append(f"feedback:+{boost}")
    return score, name, reasons


def allow_heavy_skill(task_text):
    """Check if task explicitly requests heavy skills."""
    task_text = (task_text or "").lower()
    keywords = ["loki", "autonomous", "multi-agent", "multi agent", "agents", "swarm"]
    return any(k in task_text for k in keywords)


# ============================================================================
# Skill Selection (Drift)
# ============================================================================

def pick_skills(skills, task, max_skills, feedback, bundle_set,
                explain=False, use_embeddings=True, use_groove=True):
    """Select best skills for a task (Drift engine).

    Args:
        use_embeddings: If True, try loading semantic embeddings for hybrid scoring.
        use_groove: If True, apply Groove outcome-based score adjustments.
    """
    task_tokens = expand_tokens(tokenize(task))
    allow_heavy = allow_heavy_skill(task)
    scored, skipped_heavy, skipped_filtered = [], [], []

    # Try loading semantic scores (Fuse semantic layer)
    semantic_scores = {}
    semantic_active = False
    if use_embeddings:
        try:
            from synapse.embeddings import get_embedder
            embedder = get_embedder()
            if embedder:
                semantic_scores = embedder.score_skills_semantic(task, skills)
                semantic_active = True
        except Exception:
            pass  # Graceful degradation to keyword-only

    # Try loading Groove scores (outcome learning)
    groove_scores = {}
    if use_groove:
        try:
            from synapse.groove import get_groove_scores, _detect_project
            groove_scores = get_groove_scores(project_name=_detect_project())
        except Exception:
            pass

    for skill in skills:
        name = get_skill_id(skill)
        if (name in HEAVY_SKILLS) and (not allow_heavy):
            skipped_heavy.append(name)
            continue
        if should_filter_security(task_tokens, name):
            skipped_filtered.append(name)
            continue
        sem_score = semantic_scores.get(name, 0.0)
        grv_score = groove_scores.get(name, 0.0)
        score, skill_name, reasons = score_skill(
            skill, task_tokens, feedback, bundle_set,
            semantic_score=sem_score, groove_score=grv_score,
        )
        scored.append((score, skill_name, reasons))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_score = scored[0][0] if scored else 0

    picked, explanations = [], []
    for score, name, reasons in scored:
        if len(picked) >= max_skills:
            break
        if score <= 0:
            continue
        if score >= max(MIN_SCORE, int(top_score * RELATIVE_THRESHOLD)):
            picked.append(name)
            if explain:
                explanations.append((name, score, reasons))

    if not picked:
        category = detect_task_category(task_tokens)
        fallback_name = CATEGORY_FALLBACKS.get(category, "brainstorming")
        fallback = next((get_skill_id(s) for s in skills if get_skill_id(s) == fallback_name), None)
        if not fallback:
            fallback = next((get_skill_id(s) for s in skills if get_skill_id(s) == "brainstorming"), None)
        if fallback:
            picked = [fallback]
        else:
            picked = [scored[0][1]] if scored else []

    return picked, explanations, skipped_heavy, skipped_filtered, semantic_active
