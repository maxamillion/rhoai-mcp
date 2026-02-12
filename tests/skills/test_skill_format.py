"""Tests for SKILL.md file format validation."""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

REQUIRED_FRONTMATTER_FIELDS = {"name", "description"}
TOOL_PREFIX = "mcp__rhoai__"
MAX_SKILL_LINES = 500


def _get_skill_paths() -> list[Path]:
    """Get all SKILL.md file paths."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _parse_frontmatter(content: str) -> dict[str, str | list[str] | bool]:
    """Parse YAML frontmatter from SKILL.md content."""
    if not content.startswith("---"):
        return {}

    end_idx = content.index("---", 3)
    frontmatter_text = content[3:end_idx].strip()

    result: dict[str, str | list[str] | bool] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in frontmatter_text.split("\n"):
        stripped = line.strip()

        # List continuation
        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip())
            continue

        # Save previous list if any
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")

            if not value:
                # Could be a list following
                current_key = key
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            else:
                result[key] = value

    # Save final list
    if current_key and current_list:
        result[current_key] = current_list

    return result


class TestSkillFilesExist:
    """Verify all expected skill files exist."""

    def test_skills_directory_exists(self) -> None:
        assert SKILLS_DIR.is_dir(), f"Skills directory not found: {SKILLS_DIR}"

    def test_all_21_skills_exist(self) -> None:
        paths = _get_skill_paths()
        assert len(paths) == 21, f"Expected 21 skills, found {len(paths)}"

    @pytest.mark.parametrize(
        "skill_name",
        [
            "train-model",
            "monitor-training",
            "resume-training",
            "deploy-model",
            "deploy-llm",
            "test-endpoint",
            "scale-model",
            "explore-cluster",
            "explore-project",
            "find-gpus",
            "whats-running",
            "troubleshoot-training",
            "troubleshoot-workbench",
            "troubleshoot-model",
            "analyze-oom",
            "setup-training-project",
            "setup-inference-project",
            "add-data-connection",
            "prepare-training",
            "prepare-deployment",
            "diagnose-resource",
        ],
    )
    def test_skill_exists(self, skill_name: str) -> None:
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_path.exists(), f"Missing skill: {skill_path}"


class TestSkillFrontmatter:
    """Validate YAML frontmatter in each SKILL.md."""

    @pytest.fixture(params=_get_skill_paths(), ids=lambda p: p.parent.name)
    def skill_content(self, request: pytest.FixtureRequest) -> tuple[Path, str]:
        path: Path = request.param
        return path, path.read_text()

    def test_has_frontmatter(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        assert content.startswith("---"), f"{path.parent.name}: Missing YAML frontmatter"

    def test_has_required_fields(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        fm = _parse_frontmatter(content)
        for field in REQUIRED_FRONTMATTER_FIELDS:
            assert field in fm, f"{path.parent.name}: Missing required field '{field}'"

    def test_name_matches_directory(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        fm = _parse_frontmatter(content)
        assert fm.get("name") == path.parent.name, (
            f"Skill name '{fm.get('name')}' doesn't match directory '{path.parent.name}'"
        )

    def test_description_nonempty(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        fm = _parse_frontmatter(content)
        desc = fm.get("description", "")
        assert isinstance(desc, str) and len(desc) > 10, (
            f"{path.parent.name}: Description too short or missing"
        )

    def test_allowed_tools_pattern(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        fm = _parse_frontmatter(content)
        tools = fm.get("allowed-tools", [])
        if isinstance(tools, list):
            for tool in tools:
                assert tool.startswith(TOOL_PREFIX), (
                    f"{path.parent.name}: Tool '{tool}' doesn't start with '{TOOL_PREFIX}'"
                )


class TestSkillContent:
    """Validate SKILL.md content quality."""

    @pytest.fixture(params=_get_skill_paths(), ids=lambda p: p.parent.name)
    def skill_content(self, request: pytest.FixtureRequest) -> tuple[Path, str]:
        path: Path = request.param
        return path, path.read_text()

    def test_under_max_lines(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        lines = content.count("\n") + 1
        assert lines <= MAX_SKILL_LINES, (
            f"{path.parent.name}: {lines} lines exceeds max of {MAX_SKILL_LINES}"
        )

    def test_has_markdown_heading(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        assert "\n# " in content, f"{path.parent.name}: Missing markdown heading"

    def test_has_steps_section(self, skill_content: tuple[Path, str]) -> None:
        path, content = skill_content
        assert "##" in content, f"{path.parent.name}: Missing steps sections (## headings)"
