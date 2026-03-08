"""Synapse configuration — paths, constants, defaults."""
import os
import sys
from pathlib import Path

# Version check
if sys.version_info < (3, 8):
    print("Error: Python 3.8+ required. You have {}.{}.{}".format(*sys.version_info[:3]), file=sys.stderr)
    sys.exit(1)

# Constants
DEFAULT_MAX_SKILLS = 3
MAX_SKILLS = 5
MAX_TASK_LENGTH = 2000
FEEDBACK_CAP = 10
MIN_SCORE = 2
RELATIVE_THRESHOLD = 0.7
HEAVY_SKILLS = {"loki-mode"}

# Semantic embedding constants
SEMANTIC_WEIGHT = 8       # Multiplier for semantic similarity score (0-8 bonus)
SEMANTIC_THRESHOLD = 0.25  # Minimum cosine similarity to count as a match
ONNX_MODEL_NAME = "all-MiniLM-L6-v2"
ONNX_MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"

# Groove (outcome-based learning) constants
GROOVE_MAX_BOOST = 5      # Max ±adjustment from outcomes
GROOVE_MIN_RATINGS = 3    # Minimum ratings before score takes effect

# Paths
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent


def get_synapse_home():
    """Return Synapse data directory (~/.codex/.synapse/)."""
    codex_home = os.getenv("CODEX_HOME", "").strip()
    if codex_home:
        return Path(codex_home) / ".synapse"
    return Path.home() / ".codex" / ".synapse"


def get_skills_root():
    """Resolve skills root directory."""
    # 1. Environment variable
    for env_var in ("SYNAPSE_SKILLS_ROOT", "ANTIGRAVITY_SKILLS_ROOT"):
        env_root = os.getenv(env_var, "").strip()
        if env_root:
            env_path = Path(env_root)
            if (env_path / "skills_index.json").exists():
                return env_path

    # 2. Repo .agent/skills
    repo_skills = REPO_ROOT / ".agent" / "skills"
    if (repo_skills / "skills_index.json").exists():
        return repo_skills

    # 3. CWD .agent/skills
    cwd_skills = Path.cwd() / ".agent" / "skills"
    if (cwd_skills / "skills_index.json").exists():
        return cwd_skills

    # 4. Default codex location
    codex_home = os.getenv("CODEX_HOME", "").strip()
    if not codex_home:
        codex_home = str(Path.home() / ".codex")
    codex_skills = Path(codex_home) / "skills"
    if (codex_skills / "skills_index.json").exists():
        return codex_skills

    return repo_skills


def get_feedback_path():
    """Return path to feedback JSON file."""
    return Path.home() / ".codex" / ".router_feedback.json"


def get_bundles_path():
    """Return path to bundles.json."""
    # Check package data/ directory first
    pkg_bundles = PACKAGE_ROOT.parent / "data" / "bundles.json"
    if pkg_bundles.exists():
        return pkg_bundles
    # Fallback to repo root
    return REPO_ROOT / "bundles.json"


def get_models_path():
    """Return path to bundled ONNX models directory."""
    return PACKAGE_ROOT / "models"


def get_cache_path():
    """Return path to Synapse cache directory (~/.codex/.synapse/cache/)."""
    cache_dir = get_synapse_home() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_outcomes_path():
    """Return path to Groove outcomes file (~/.codex/.synapse/outcomes.json)."""
    return get_synapse_home() / "outcomes.json"


def get_last_routing_path():
    """Return path to last routing result cache (for --rate)."""
    return get_synapse_home() / "last_routing.json"


DEFAULT_BUNDLES = {
    "frontend": ["frontend-design", "ui-ux-pro-max", "react-best-practices", "web-accessibility"],
    "backend": ["backend-dev-guidelines", "api-patterns", "database-design"],
    "marketing": ["copywriting", "page-cro", "seo-audit"],
    "security": ["vulnerability-scanner", "security-review", "api-security-best-practices"],
    "product": ["ai-product", "product-requirements", "brainstorming"],
    "fullstack": ["frontend-design", "backend-dev-guidelines", "database-design", "api-patterns"],
    "devops": ["devops-troubleshooter", "cicd-automation-workflow-automate", "docker-expert",
               "kubernetes-architect", "deployment-pipeline-design"],
    "testing": ["test-driven-development", "playwright-expert", "e2e-testing"],
    "data-science": ["data-analysis", "machine-learning", "python-expert"],
    "mobile": ["react-native-expert", "mobile-ux"],
    "documentation": ["technical-writing", "api-documentation"],
    "performance": ["performance-optimization", "web-performance"],
    "ai-engineering": ["ai-product", "machine-learning", "python-expert", "data-analysis"],
    "architecture": ["system-design", "backend-dev-guidelines", "database-design", "api-patterns"],
    "startup": ["brainstorming", "product-requirements", "frontend-design", "backend-dev-guidelines"],
    "refactoring": ["code-quality", "test-driven-development", "performance-optimization"],
}
