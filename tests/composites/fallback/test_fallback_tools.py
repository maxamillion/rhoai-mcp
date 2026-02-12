"""Tests for the fallback workflow guide tool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rhoai_mcp.composites.fallback.tools import FallbackPlugin, register_tools
from rhoai_mcp.utils.skill_loader import load_skills

SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"

# Known workflow names that should be available
KNOWN_WORKFLOWS = [
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
]


@pytest.fixture()
def mock_mcp() -> MagicMock:
    """Create a mock MCP server that captures tool registrations."""
    mock = MagicMock()
    registered_tools: dict[str, object] = {}

    def tool_decorator() -> object:
        def decorator(func: object) -> object:
            registered_tools[getattr(func, "__name__", str(func))] = func
            return func

        return decorator

    mock.tool = tool_decorator
    mock._registered_tools = registered_tools
    return mock


@pytest.fixture()
def get_workflow_guide(mock_mcp: MagicMock) -> object:
    """Register tools and return the get_workflow_guide function."""
    # Clear the skills cache to ensure fresh load
    import rhoai_mcp.composites.fallback.tools as fallback_module

    fallback_module._skills_cache = None

    register_tools(mock_mcp)
    return mock_mcp._registered_tools["get_workflow_guide"]


class TestGetWorkflowGuide:
    """Test the get_workflow_guide fallback tool."""

    def test_known_workflow_returns_content(self, get_workflow_guide: object) -> None:
        """get_workflow_guide('train-model') returns non-empty guidance."""
        result = get_workflow_guide("train-model")  # type: ignore[operator]
        assert "workflow" in result
        assert result["workflow"] == "train-model"
        assert "guide" in result
        assert len(result["guide"]) > 100

    def test_unknown_workflow_returns_error(self, get_workflow_guide: object) -> None:
        """get_workflow_guide('nonexistent') returns error."""
        result = get_workflow_guide("nonexistent")  # type: ignore[operator]
        assert "error" in result
        assert "available_workflows" in result
        assert len(result["available_workflows"]) > 0

    @pytest.mark.parametrize("workflow", KNOWN_WORKFLOWS)
    def test_all_known_workflows_return_content(
        self, get_workflow_guide: object, workflow: str
    ) -> None:
        """All known skill names return content."""
        result = get_workflow_guide(workflow)  # type: ignore[operator]
        assert "error" not in result, f"Workflow '{workflow}' returned error: {result.get('error')}"
        assert "guide" in result
        assert "description" in result

    def test_result_includes_description(self, get_workflow_guide: object) -> None:
        """Result includes a description field."""
        result = get_workflow_guide("deploy-model")  # type: ignore[operator]
        assert "description" in result
        assert isinstance(result["description"], str)
        assert len(result["description"]) > 10


class TestFallbackPlugin:
    """Test the FallbackPlugin class."""

    def test_plugin_metadata(self) -> None:
        plugin = FallbackPlugin()
        meta = plugin.rhoai_get_plugin_metadata()
        assert meta.name == "fallback"
        assert meta.version == "1.0.0"

    def test_plugin_health_check(self) -> None:
        plugin = FallbackPlugin()
        server = MagicMock()
        healthy, msg = plugin.rhoai_health_check(server=server)
        assert healthy is True


class TestSkillLoader:
    """Test the skill_loader utility."""

    def test_load_skills_from_directory(self) -> None:
        """load_skills() returns all skills."""
        skills = load_skills(SKILLS_DIR)
        assert len(skills) == 21

    def test_load_skills_invalid_directory(self) -> None:
        """load_skills() with invalid dir returns empty dict."""
        skills = load_skills(Path("/nonexistent/path"))
        assert skills == {}

    def test_skill_info_has_required_fields(self) -> None:
        """Each SkillInfo has name, description, content."""
        skills = load_skills(SKILLS_DIR)
        for name, skill in skills.items():
            assert skill.name == name
            assert len(skill.description) > 0
            assert len(skill.content) > 0
