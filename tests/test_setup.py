"""Tests for synapse.setup — First-run experience."""
from unittest.mock import patch


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
        # Mock git clone to fail, then HTTP to fail
        with patch("synapse.setup.clone_skills_from_sources", return_value=False):
            with patch("synapse.setup.urllib.request.urlretrieve", side_effect=Exception("offline")):
                result = download_skills(tmp_path, force=True)
        # Should fail gracefully (returns False since both download attempts fail)
        assert result is False

    def test_handles_offline_gracefully(self, tmp_path):
        """Should not crash when network is unavailable."""
        from synapse.setup import download_skills
        with patch("synapse.setup.clone_skills_from_sources", return_value=False):
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


class TestInstallRules:
    """Test rules injection into GEMINI.md."""

    def test_creates_gemini_md_if_missing(self, tmp_path):
        """Should create ~/.gemini/GEMINI.md if it doesn't exist."""
        from synapse.setup import SYNAPSE_RULES_VERSION, install_rules

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "GEMINI_RULES.md").write_text("# Synapse Rules\nUse synapse.", encoding="utf-8")

        with patch("synapse.setup.Path.home", return_value=fake_home):
            with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "synapse"):
                (tmp_path / "synapse").mkdir(exist_ok=True)
                install_rules()

        gemini_md = fake_home / ".gemini" / "GEMINI.md"
        assert gemini_md.exists()
        content = gemini_md.read_text(encoding="utf-8")
        assert f"SYNAPSE_VERSION:{SYNAPSE_RULES_VERSION}" in content
        assert "# Synapse Rules" in content

    def test_replaces_old_synapse_block(self, tmp_path):
        """Should replace existing Synapse rules block with new version."""
        from synapse.setup import SYNAPSE_RULES_VERSION, install_rules

        fake_home = tmp_path / "home"
        gemini_dir = fake_home / ".gemini"
        gemini_dir.mkdir(parents=True)
        gemini_md = gemini_dir / "GEMINI.md"
        gemini_md.write_text(
            "# My Rules\n\n<!-- SYNAPSE_VERSION:1.0.0 -->\nOld rules\n<!-- /SYNAPSE_RULES -->\n",
            encoding="utf-8",
        )

        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "GEMINI_RULES.md").write_text("# New Rules v3", encoding="utf-8")

        with patch("synapse.setup.Path.home", return_value=fake_home):
            with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "synapse"):
                (tmp_path / "synapse").mkdir(exist_ok=True)
                install_rules()

        content = gemini_md.read_text(encoding="utf-8")
        assert "Old rules" not in content
        assert f"SYNAPSE_VERSION:{SYNAPSE_RULES_VERSION}" in content
        assert "# New Rules v3" in content
        assert "# My Rules" in content  # Preserves user's existing content

    def test_migrates_old_antigravity_block(self, tmp_path):
        """Should remove old ANTIGRAVITY_OPTIMIZER_VERSION block."""
        from synapse.setup import install_rules

        fake_home = tmp_path / "home"
        gemini_dir = fake_home / ".gemini"
        gemini_dir.mkdir(parents=True)
        gemini_md = gemini_dir / "GEMINI.md"
        gemini_md.write_text(
            "# Rules\n\n<!-- ANTIGRAVITY_OPTIMIZER_VERSION:2.0 -->\nOld AG rules\n<!-- /ANTIGRAVITY_RULES -->\n",
            encoding="utf-8",
        )

        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "GEMINI_RULES.md").write_text("# Synapse", encoding="utf-8")

        with patch("synapse.setup.Path.home", return_value=fake_home):
            with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "synapse"):
                (tmp_path / "synapse").mkdir(exist_ok=True)
                install_rules()

        content = gemini_md.read_text(encoding="utf-8")
        assert "ANTIGRAVITY_OPTIMIZER_VERSION" not in content
        assert "Old AG rules" not in content


class TestDeployWorkflows:
    """Test workflow deployment."""

    def test_copies_workflow_files(self, tmp_path):
        """Should copy workflow .md files to target directory."""
        from synapse.setup import deploy_workflows

        source = tmp_path / "repo" / ".agent" / "workflows"
        source.mkdir(parents=True)
        (source / "activate-skills.md").write_text("# Activate", encoding="utf-8")
        (source / "update-synapse.md").write_text("# Update", encoding="utf-8")

        target = tmp_path / "project" / ".agent" / "workflows"

        with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "repo" / "synapse"):
            (tmp_path / "repo" / "synapse").mkdir(exist_ok=True)
            deploy_workflows(target_dir=target)

        assert (target / "activate-skills.md").exists()
        assert (target / "update-synapse.md").exists()

    def test_does_not_overwrite_existing(self, tmp_path):
        """Should not overwrite existing workflows unless force=True."""
        from synapse.setup import deploy_workflows

        source = tmp_path / "repo" / ".agent" / "workflows"
        source.mkdir(parents=True)
        (source / "activate-skills.md").write_text("# New", encoding="utf-8")

        target = tmp_path / "project" / ".agent" / "workflows"
        target.mkdir(parents=True)
        (target / "activate-skills.md").write_text("# Existing", encoding="utf-8")

        with patch("synapse.setup.PACKAGE_ROOT", tmp_path / "repo" / "synapse"):
            (tmp_path / "repo" / "synapse").mkdir(exist_ok=True)
            deploy_workflows(target_dir=target)

        assert (target / "activate-skills.md").read_text() == "# Existing"


class TestRunSetup:
    """Test the main setup orchestrator."""

    def test_setup_returns_zero(self, tmp_path):
        """Setup should return 0 on success."""
        from synapse.setup import run_setup

        with patch("synapse.setup.get_skills_root", return_value=tmp_path / "skills"):
            with patch("synapse.setup.download_skills", return_value=True):
                with patch("synapse.setup.install_templates"):
                    with patch("synapse.setup.install_rules"):
                        with patch("synapse.setup.deploy_workflows"):
                            result = run_setup()

        assert result == 0

    def test_full_isolated_setup(self, tmp_path):
        """Full integration test: run_setup with all I/O in tmp_path."""
        from synapse.setup import run_setup

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        # Pre-create skills_index.json so download is skipped
        (skills_dir / "skills_index.json").write_text(
            '{"skills": [{"id": "test-skill"}]}', encoding="utf-8"
        )

        # Create templates and workflows in fake package root
        fake_pkg = tmp_path / "pkg" / "synapse"
        fake_pkg.mkdir(parents=True)
        templates = tmp_path / "pkg" / "templates"
        templates.mkdir()
        (templates / "GEMINI_RULES.md").write_text("# Synapse Rules", encoding="utf-8")
        (templates / "master-memory.md").write_text("# Memory", encoding="utf-8")
        wf_source = tmp_path / "pkg" / ".agent" / "workflows"
        wf_source.mkdir(parents=True)
        (wf_source / "activate-skills.md").write_text("# Activate", encoding="utf-8")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("synapse.setup.get_skills_root", return_value=skills_dir):
            with patch("synapse.setup.PACKAGE_ROOT", fake_pkg):
                with patch("synapse.setup.Path.home", return_value=fake_home):
                    with patch("synapse.setup.os.getcwd", return_value=str(project_dir)):
                        with patch("synapse.setup.Path.cwd", return_value=project_dir):
                            result = run_setup()

        assert result == 0
        # Verify rules were injected
        gemini_md = fake_home / ".gemini" / "GEMINI.md"
        assert gemini_md.exists()
        assert "SYNAPSE_VERSION" in gemini_md.read_text(encoding="utf-8")
        # Verify templates were installed
        assert (project_dir / ".agent" / "master-memory.md").exists()
        # Verify workflows were deployed
        assert (project_dir / ".agent" / "workflows" / "activate-skills.md").exists()
