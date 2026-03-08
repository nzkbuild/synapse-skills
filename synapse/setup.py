"""Synapse Setup — Zero-question first-run experience.

Detects platform, IDE, downloads skills via git clone, installs rules
and workflows automatically. Users should never need to answer questions.

Usage: synapse setup [--force]
"""
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from synapse.config import PACKAGE_ROOT, get_skills_root

# Skills archive URL (GitHub releases — fallback)
SKILLS_ARCHIVE_URL = (
    "https://github.com/nzkbuild/synapse-skills/releases/latest/download/skills.tar.gz"
)
SKILLS_INDEX_URL = (
    "https://github.com/nzkbuild/synapse-skills/releases/latest/download/skills_index.json"
)

# Synapse rules version (bumped when rules content changes)
SYNAPSE_RULES_VERSION = "3.0.0"

# IDE markers
IDE_MARKERS = {
    "gemini": [".gemini"],
    "cursor": [".cursor", ".cursorrc"],
    "vscode": [".vscode"],
    "jetbrains": [".idea"],
    "windsurf": [".windsurf"],
    "codex": [".codex"],
}


# ============================================================================
# Detection
# ============================================================================

def detect_platform():
    """Detect the operating system.

    Returns: "windows", "macos", or "linux"
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def detect_ide(project_dir=None):
    """Detect IDEs by scanning for marker files/directories.

    Args:
        project_dir: Directory to scan (defaults to CWD)

    Returns: list of IDE names found (e.g. ["gemini", "vscode"])
    """
    project_dir = Path(project_dir or os.getcwd())
    found = []
    for ide_name, markers in IDE_MARKERS.items():
        for marker in markers:
            if (project_dir / marker).exists():
                found.append(ide_name)
                break
    return found


# ============================================================================
# Skills Download (git-based, with HTTP fallback)
# ============================================================================

def _load_skills_sources():
    """Load skills_sources.json from data/ directory."""
    sources_path = PACKAGE_ROOT.parent / "data" / "skills_sources.json"
    if not sources_path.exists():
        return []
    try:
        with sources_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sources", [])
    except Exception:
        return []


def _git_clone_source(source, target_dir):
    """Clone a single skill source via git sparse-checkout.

    Args:
        source: dict from skills_sources.json
        target_dir: Where to install skills (e.g. .agent/skills/)

    Returns: number of skills copied, or 0 on failure
    """
    repo = source["repo"]
    branch = source.get("branch", "main")
    skills_subdir = source.get("path", "skills/").rstrip("/")
    repo_url = f"https://github.com/{repo}.git"

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Shallow clone with sparse-checkout
            subprocess.run(
                ["git", "clone", "--depth", "1", "--filter=blob:none",
                 "--sparse", "-b", branch, repo_url, tmp_dir],
                check=True, capture_output=True, timeout=120,
            )
            subprocess.run(
                ["git", "sparse-checkout", "set", skills_subdir],
                cwd=tmp_dir, check=True, capture_output=True, timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return 0

        # Copy skills into target
        src_skills = Path(tmp_dir) / skills_subdir
        if not src_skills.exists():
            return 0

        count = 0
        skills_dest = target_dir / "skills"
        skills_dest.mkdir(parents=True, exist_ok=True)

        for item in src_skills.iterdir():
            if item.is_dir():
                dest = skills_dest / item.name
                if not dest.exists():
                    shutil.copytree(str(item), str(dest))
                    count += 1
            elif item.is_file() and item.name == "skills_index.json":
                # Merge or copy skills_index.json to root
                dest = target_dir / "skills_index.json"
                if not dest.exists():
                    shutil.copy2(str(item), str(dest))

        return count


def clone_skills_from_sources(target_dir, force=False):
    """Clone skills from all configured upstream sources.

    Args:
        target_dir: Where to install skills (e.g. .agent/skills/)
        force: If True, remove and re-clone

    Returns: True if any skills were installed
    """
    target_dir = Path(target_dir)
    index_path = target_dir / "skills_index.json"

    if index_path.exists() and not force:
        return True

    if force and target_dir.exists():
        # Only remove skills/ subfolder, keep other data
        skills_sub = target_dir / "skills"
        if skills_sub.exists():
            shutil.rmtree(str(skills_sub))
        if index_path.exists():
            index_path.unlink()

    sources = _load_skills_sources()
    if not sources:
        return False

    target_dir.mkdir(parents=True, exist_ok=True)
    total = 0

    for source in sorted(sources, key=lambda s: s.get("priority", 99)):
        name = source.get("name", source["repo"])
        print(f"  Cloning {name}...", end=" ", flush=True)
        count = _git_clone_source(source, target_dir)
        if count > 0:
            print(f"{count} skills")
            total += count
        else:
            print("skipped (clone failed or empty)")

    return total > 0


def download_skills_http(target_dir, force=False):
    """Download and extract skills archive from GitHub releases (fallback).

    Args:
        target_dir: Where to install skills (e.g. .agent/skills/)
        force: If True, re-download even if already exists

    Returns: True if successful, False if failed (offline, etc.)
    """
    target_dir = Path(target_dir)
    index_path = target_dir / "skills_index.json"

    if index_path.exists() and not force:
        return True

    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("  Downloading skills archive...", end=" ", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            urllib.request.urlretrieve(SKILLS_ARCHIVE_URL, tmp_path)

        print("extracting...", end=" ", flush=True)
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(str(target_dir))

        print("done.")
        return True

    except Exception as e:
        print(f"failed ({e})")
        try:
            print("  Trying index-only download...", end=" ", flush=True)
            urllib.request.urlretrieve(SKILLS_INDEX_URL, str(index_path))
            print("done.")
            return True
        except Exception:
            print("failed.")
            return False

    finally:
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except Exception:
            pass


def download_skills(target_dir, force=False):
    """Download skills — tries git clone first, HTTP fallback.

    Args:
        target_dir: Where to install skills
        force: Re-download even if present

    Returns: True if skills are available
    """
    # Primary: git sparse-checkout from upstream sources
    if clone_skills_from_sources(target_dir, force=force):
        return True

    # Fallback: HTTP download from GitHub Releases
    print("  Git clone failed, trying HTTP fallback...")
    return download_skills_http(target_dir, force=force)


# ============================================================================
# Templates
# ============================================================================

def install_templates(target_dir):
    """Copy starter templates (master-memory.md) to .agent/.

    Args:
        target_dir: The .agent/ directory
    """
    target_dir = Path(target_dir)
    templates_dir = PACKAGE_ROOT.parent / "templates"

    if not templates_dir.exists():
        return

    for template in templates_dir.iterdir():
        if template.is_file():
            dest = target_dir / template.name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(template), str(dest))


# ============================================================================
# Rules Injection
# ============================================================================

def install_rules():
    """Inject Synapse rules block into ~/.gemini/GEMINI.md.

    Creates the file if it doesn't exist. Uses version markers to detect
    and replace existing blocks. Migrates old ANTIGRAVITY_OPTIMIZER_VERSION
    blocks automatically.
    """
    gemini_dir = Path.home() / ".gemini"
    gemini_md = gemini_dir / "GEMINI.md"

    # Load rules template
    rules_template = PACKAGE_ROOT.parent / "templates" / "GEMINI_RULES.md"
    if not rules_template.exists():
        print("  Rules template not found, skipping.")
        return

    rules_content = rules_template.read_text(encoding="utf-8").strip()

    # Build the versioned block
    start_marker = f"<!-- SYNAPSE_VERSION:{SYNAPSE_RULES_VERSION} -->"
    end_marker = "<!-- /SYNAPSE_RULES -->"
    block = f"{start_marker}\n{rules_content}\n{end_marker}"

    gemini_dir.mkdir(parents=True, exist_ok=True)

    if gemini_md.exists():
        existing = gemini_md.read_text(encoding="utf-8")

        # Check if current version already present
        if f"SYNAPSE_VERSION:{SYNAPSE_RULES_VERSION}" in existing:
            print("  Rules already up-to-date.")
            return

        # Remove old Synapse block if present
        import re
        existing = re.sub(
            r"<!-- SYNAPSE_VERSION:.*?-->.*?<!-- /SYNAPSE_RULES -->",
            "", existing, flags=re.DOTALL,
        ).strip()

        # Migrate old Antigravity block if present
        existing = re.sub(
            r"<!-- ANTIGRAVITY_OPTIMIZER_VERSION:.*?-->.*?<!-- /ANTIGRAVITY_RULES -->",
            "", existing, flags=re.DOTALL,
        ).strip()

        # Append new block
        content = f"{existing}\n\n{block}\n"
    else:
        content = f"# Gemini Rules\n\n{block}\n"

    gemini_md.write_text(content, encoding="utf-8")
    print(f"  Rules injected (v{SYNAPSE_RULES_VERSION}).")


# ============================================================================
# Workflow Deployment
# ============================================================================

def deploy_workflows(target_dir=None, force=False):
    """Copy workflow files to user's project .agent/workflows/.

    Args:
        target_dir: Target .agent/workflows/ dir (defaults to CWD/.agent/workflows/)
        force: Overwrite existing files
    """
    if target_dir is None:
        target_dir = Path.cwd() / ".agent" / "workflows"

    target_dir = Path(target_dir)
    source_dir = PACKAGE_ROOT.parent / ".agent" / "workflows"

    if not source_dir.exists():
        print("  No bundled workflows found, skipping.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    deployed = 0

    for wf in source_dir.iterdir():
        if wf.is_file() and wf.suffix == ".md":
            dest = target_dir / wf.name
            if not dest.exists() or force:
                shutil.copy2(str(wf), str(dest))
                deployed += 1

    if deployed:
        print(f"  Deployed {deployed} workflow(s).")
    else:
        print("  Workflows already installed.")


# ============================================================================
# Main Setup
# ============================================================================

def run_setup(force=False):
    """Run the full zero-question setup.

    Steps:
    1. Detect platform
    2. Detect IDE
    3. Download skills
    4. Install templates
    5. Install rules
    6. Deploy workflows
    7. Verify installation

    Returns: 0 on success, 1 on failure
    """
    print("=" * 50)
    print("SYNAPSE SETUP")
    print("=" * 50)

    # Step 1: Platform
    print("\n[1/7] Detecting platform...")
    plat = detect_platform()
    print(f"  Platform: {plat}")

    # Step 2: IDE
    print("\n[2/7] Detecting IDE...")
    ides = detect_ide()
    if ides:
        print(f"  Found: {', '.join(ides)}")
    else:
        print("  No IDE markers found (that's fine)")

    # Step 3: Download skills
    print("\n[3/7] Installing skills...")
    skills_root = get_skills_root()
    index_exists = (skills_root / "skills_index.json").exists()
    if index_exists and not force:
        print("  Skills already installed. Use --force to re-download.")
        download_ok = True
    else:
        download_ok = download_skills(skills_root, force=force)

    # Step 4: Templates
    print("\n[4/7] Installing templates...")
    agent_dir = Path.cwd() / ".agent"
    install_templates(agent_dir)
    print("  Templates ready.")

    # Step 5: Rules
    print("\n[5/7] Installing rules...")
    install_rules()

    # Step 6: Workflows
    print("\n[6/7] Deploying workflows...")
    deploy_workflows(force=force)

    # Step 7: Verify
    print("\n[7/7] Verifying installation...")
    index_path = skills_root / "skills_index.json"
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "skills" in data:
                count = len(data["skills"])
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 0
            print(f"  Skills index: {count} skills")
        except Exception:
            print("  Skills index: present but unreadable")
    else:
        if download_ok:
            print("  Skills index: not found (using local)")
        else:
            print("  \u26a0\ufe0f Skills index: not found. You can install skills manually.")

    # Summary
    print(f"\n{'=' * 50}")
    print("SETUP COMPLETE")
    print(f"{'=' * 50}")
    print(f"  Platform:  {plat}")
    print(f"  IDEs:      {', '.join(ides) if ides else 'none detected'}")
    print(f"  Skills:    {skills_root}")
    print("\n  Run: synapse \"your task\" to get started!")
    print(f"{'=' * 50}")

    return 0
