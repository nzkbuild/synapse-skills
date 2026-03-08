"""Tests for synapse.setup — First-run experience."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestDetectPlatform:
    """Test platform detection."""

    def test_returns_valid_platform(self):
        """Should return one of windows, macos, linux."""
        from synapse.setup import detect_platform
        result = detect_platform()
        assert result in ("windows", "macos", "linux")

    def test_windows_detection(self):
        """Should return 'windows' on Windows systems."""
        from synapse.setup import detect_platform
        with patch("synapse.setup.platform.system", return_value="Windows"):
            assert detect_platform() == "windows"

    def test_macos_detection(self):
        """Should return 'macos' on macOS (Darwin) systems."""
        from synapse.setup import detect_platform
        with patch("synapse.setup.platform.system", return_value="Darwin"):
            assert detect_platform() == "macos"

    def test_linux_detection(self):
        """Should return 'linux' on Linux systems."""
        from synapse.setup import detect_platform
        with patch("synapse.setup.platform.system", return_value="Linux"):
            assert detect_platform() == "linux"


class TestDetectIDE:
    """Test IDE detection."""

    def test_finds_gemini_marker(self, tmp_path):
        """Should detect Gemini IDE from .gemini/ directory."""
        from synapse.setup import detect_ide
        (tmp_path / ".gemini").mkdir()
        result = detect_ide(project_dir=tmp_path)
        assert "gemini" in result

    def test_finds_vscode_marker(self, tmp_path):
        """Should detect VS Code from .vscode/ directory."""
        from synapse.setup import detect_ide
        (tmp_path / ".vscode").mkdir()
        result = detect_ide(project_dir=tmp_path)
        assert "vscode" in result

    def test_finds_multiple_ides(self, tmp_path):
        """Should detect multiple IDEs simultaneously."""
        from synapse.setup import detect_ide
        (tmp_path / ".gemini").mkdir()
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".cursor").mkdir()
        result = detect_ide(project_dir=tmp_path)
        assert len(result) >= 3

    def test_no_markers_returns_empty(self, tmp_path):
        """Should return empty list when no IDE markers found."""
        from synapse.setup import detect_ide
        result = detect_ide(project_dir=tmp_path)
        assert result == []


class TestDownloadSkills:
    """Test skills download (mocked network)."""

    def test_skips_if_already_installed(self, tmp_path):
        """Should skip download when skills_index.json exists and force=False."""
        from synapse.setup import download_skills
        index = tmp_path / "skills_index.json"
        index.write_text("{}", encoding="utf-8")
        result = download_skills(tmp_path, force=False)
        assert result is True

    def test_force_redownloads(self, tmp_path):
        """Should attempt download even if index exists when force=True."""
        from synapse.setup import download_skills
        index = tmp_path / "skills_index.json"
        index.write_text("{}", encoding="utf-8")
        # Mock urllib to fail gracefully
        with patch("synapse.setup.urllib.request.urlretrieve", side_effect=Exception("offline")):
            result = download_skills(tmp_path, force=True)
        # Should fail gracefully (returns False since both download attempts fail)
        assert result is False

    def test_handles_offline_gracefully(self, tmp_path):
        """Should not crash when network is unavailable."""
        from synapse.setup import download_skills
        with patch("synapse.setup.urllib.request.urlretrieve", side_effect=Exception("offline")):
            result = download_skills(tmp_path)
        assert result is False  # Failed but didn't crash


class TestInstallTemplates:
    """Test template installation."""

    def test_copies_template_files(self, tmp_path):
        """Should copy templates to target directory."""
        from synapse.setup import install_templates

        # Create a fake templates dir
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "master-memory.md").write_text("# Memory", encoding="utf-8")

        target = tmp_path / "target"
        target.mkdir()

        with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "synapse"):
            # PACKAGE_ROOT.parent / "templates" → tmp_path / "templates"
            (tmp_path / "synapse").mkdir(exist_ok=True)
            install_templates(target)

        assert (target / "master-memory.md").exists()

    def test_does_not_overwrite_existing(self, tmp_path):
        """Should not overwrite existing template files."""
        from synapse.setup import install_templates

        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "master-memory.md").write_text("# New", encoding="utf-8")

        target = tmp_path / "target"
        target.mkdir()
        (target / "master-memory.md").write_text("# Existing", encoding="utf-8")

        with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "synapse"):
            (tmp_path / "synapse").mkdir(exist_ok=True)
            install_templates(target)

        assert (target / "master-memory.md").read_text() == "# Existing"


class TestRunSetup:
    """Test the main setup orchestrator."""

    def test_setup_returns_zero(self, tmp_path):
        """Setup should return 0 on success."""
        from synapse.setup import run_setup

        with patch("synapse.setup.get_skills_root", return_value=tmp_path / "skills"):
            with patch("synapse.setup.download_skills", return_value=True):
                with patch("synapse.setup.install_templates"):
                    result = run_setup()

        assert result == 0
