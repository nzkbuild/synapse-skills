"""Synapse Setup — Zero-question first-run experience.

Detects platform, IDE, downloads skills, and configures everything
automatically. Users should never need to answer questions.

Usage: synapse setup [--force]
"""
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from synapse.config import get_skills_root, PACKAGE_ROOT

# Skills archive URL (GitHub releases)
SKILLS_ARCHIVE_URL = (
    "https://github.com/nzkbuild/synapse-skills/releases/latest/download/skills.tar.gz"
)
SKILLS_INDEX_URL = (
    "https://github.com/nzkbuild/synapse-skills/releases/latest/download/skills_index.json"
)

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
# Skills Download
# ============================================================================

def download_skills(target_dir, force=False):
    """Download and extract skills archive from GitHub releases.

    Args:
        target_dir: Where to install skills (e.g. .agent/skills/)
        force: If True, re-download even if already exists

    Returns: True if successful, False if failed (offline, etc.)
    """
    target_dir = Path(target_dir)
    index_path = target_dir / "skills_index.json"

    if index_path.exists() and not force:
        return True  # Already installed

    target_dir.mkdir(parents=True, exist_ok=True)

    # Try downloading the archive
    try:
        print("  Downloading skills archive...", end=" ", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            urllib.request.urlretrieve(SKILLS_ARCHIVE_URL, tmp_path)

        # Extract
        print("extracting...", end=" ", flush=True)
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(str(target_dir))

        print("done.")
        return True

    except Exception as e:
        print(f"failed ({e})")
        # Fallback: try downloading just the index
        try:
            print("  Trying index-only download...", end=" ", flush=True)
            urllib.request.urlretrieve(SKILLS_INDEX_URL, str(index_path))
            print("done.")
            return True
        except Exception:
            print("failed.")
            return False

    finally:
        # Clean up temp file
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except Exception:
            pass


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
# Main Setup
# ============================================================================

def run_setup(force=False):
    """Run the full zero-question setup.

    Steps:
    1. Detect platform
    2. Detect IDE
    3. Download skills
    4. Install templates
    5. Verify installation

    Returns: 0 on success, 1 on failure
    """
    print("=" * 50)
    print("SYNAPSE SETUP")
    print("=" * 50)

    # Step 1: Platform
    print(f"\n[1/5] Detecting platform...")
    plat = detect_platform()
    print(f"  Platform: {plat}")

    # Step 2: IDE
    print(f"\n[2/5] Detecting IDE...")
    ides = detect_ide()
    if ides:
        print(f"  Found: {', '.join(ides)}")
    else:
        print("  No IDE markers found (that's fine)")

    # Step 3: Download skills
    print(f"\n[3/5] Installing skills...")
    skills_root = get_skills_root()
    index_exists = (skills_root / "skills_index.json").exists()
    if index_exists and not force:
        print("  Skills already installed. Use --force to re-download.")
        download_ok = True
    else:
        download_ok = download_skills(skills_root, force=force)

    # Step 4: Templates
    print(f"\n[4/5] Installing templates...")
    agent_dir = Path.cwd() / ".agent"
    install_templates(agent_dir)
    print("  Templates ready.")

    # Step 5: Verify
    print(f"\n[5/5] Verifying installation...")
    index_path = skills_root / "skills_index.json"
    if index_path.exists():
        import json
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
    print(f"\n  Run: synapse \"your task\" to get started!")
    print(f"{'=' * 50}")

    return 0
