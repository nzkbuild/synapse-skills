"""Synapse Profiles (Marq) — Auto-detect project type and boost skills."""
import json
import os
from pathlib import Path

MAX_PROFILES = 10

PROJECT_MARKERS = {
    "package.json": ("node", ["frontend-design", "react-best-practices", "test-driven-development"]),
    "tsconfig.json": ("typescript", ["typescript-expert", "react-best-practices"]),
    "go.mod": ("go", ["api-patterns", "test-driven-development"]),
    "Cargo.toml": ("rust", ["test-driven-development"]),
    "pyproject.toml": ("python", ["test-driven-development"]),
    "requirements.txt": ("python", ["test-driven-development"]),
    "setup.py": ("python", ["test-driven-development"]),
    "Gemfile": ("ruby", ["test-driven-development"]),
    "pom.xml": ("java", ["test-driven-development"]),
    "docker-compose.yml": ("docker", ["docker-expert"]),
    "Dockerfile": ("docker", ["docker-expert"]),
    ".terraform": ("terraform", ["terraform-expert"]),
}

SECONDARY_MARKERS = {
    "next.config.js": "nextjs", "next.config.ts": "nextjs", "next.config.mjs": "nextjs",
    "vite.config.ts": "vite", "vite.config.js": "vite",
    "angular.json": "angular", "vue.config.js": "vue", "svelte.config.js": "svelte",
}


def get_profiles_path():
    codex_home = os.getenv("CODEX_HOME", "").strip()
    if codex_home:
        return Path(codex_home) / ".project_profiles.json"
    return Path.home() / ".codex" / ".project_profiles.json"


def load_profiles():
    path = get_profiles_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_profiles(profiles):
    path = get_profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(profiles) > MAX_PROFILES:
        sorted_keys = sorted(profiles.keys(), key=lambda k: profiles[k].get("last_used", 0), reverse=True)
        profiles = {k: profiles[k] for k in sorted_keys[:MAX_PROFILES]}
    with path.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, sort_keys=True)


def detect_project_type(project_dir=None):
    """Detect project type by scanning marker files (Marq)."""
    cwd = Path(project_dir) if project_dir else Path.cwd()
    detected_type, preferred_skills = "unknown", []

    for marker, (ptype, skills) in PROJECT_MARKERS.items():
        if (cwd / marker).exists():
            detected_type = ptype
            preferred_skills = list(skills)
            break

    for marker, framework in SECONDARY_MARKERS.items():
        if (cwd / marker).exists():
            detected_type = framework
            break

    if detected_type in ("node", "nextjs", "vite"):
        pkg_json = cwd / "package.json"
        if pkg_json.exists():
            try:
                with pkg_json.open("r", encoding="utf-8") as f:
                    pkg = json.load(f)
                deps = {}
                deps.update(pkg.get("dependencies", {}))
                deps.update(pkg.get("devDependencies", {}))
                if "react" in deps and "react-best-practices" not in preferred_skills:
                    preferred_skills.append("react-best-practices")
                if "vue" in deps:
                    detected_type = "vue"
                if "next" in deps:
                    detected_type = "nextjs"
                    if "nextjs-app-router-patterns" not in preferred_skills:
                        preferred_skills.append("nextjs-app-router-patterns")
            except Exception:
                pass

    return detected_type, preferred_skills


def get_project_profile(project_dir=None):
    import time
    cwd = str(Path(project_dir) if project_dir else Path.cwd())
    profiles = load_profiles()
    if cwd in profiles:
        profiles[cwd]["last_used"] = int(time.time())
        save_profiles(profiles)
        return profiles[cwd]
    project_type, preferred_skills = detect_project_type(project_dir)
    profile = {"type": project_type, "preferred_skills": preferred_skills,
               "last_used": int(time.time()), "feedback": {}}
    profiles[cwd] = profile
    save_profiles(profiles)
    return profile


def get_profile_boost_set(project_dir=None):
    """Return set of skill IDs to boost for this project (Marq)."""
    profile = get_project_profile(project_dir)
    return set(profile.get("preferred_skills", []))
