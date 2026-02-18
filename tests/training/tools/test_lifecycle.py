"""Tests for training lifecycle tools."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from rhoai_mcp.domains.training.tools.lifecycle import register_tools


class TestLifecycleTools:
    """Test lifecycle tools registration and execution."""

    @pytest.fixture
    def mock_mcp(self) -> MagicMock:
        """Create a mock FastMCP server."""
        mock = MagicMock()
        mock.tool = MagicMock(return_value=lambda f: f)
        return mock

    @pytest.fixture
    def mock_server(self) -> MagicMock:
        """Create a mock RHOAIServer."""
        server = MagicMock()
        server.k8s = MagicMock()
        server.k8s.core_v1 = MagicMock()
        server.config.is_operation_allowed.return_value = (True, None)
        return server

    def test_register_tools_registers_lifecycle_tools(
        self, mock_mcp: MagicMock, mock_server: MagicMock
    ) -> None:
        """Test that lifecycle tools are registered."""
        register_tools(mock_mcp, mock_server)

        # wait_for_job_completion and get_job_spec
        assert mock_mcp.tool.call_count >= 2

    def test_wait_for_job_completion(self, mock_mcp: MagicMock, mock_server: MagicMock) -> None:
        """Test waiting for job completion."""
        # First call returns Running, second returns Completed
        mock_server.k8s.get.side_effect = [
            _make_mock_resource(
                "my-job",
                "training",
                status={"conditions": [{"type": "Completed", "status": "True"}]},
            ),
        ]

        tools = {}

        def capture_tool():
            def decorator(f):
                tools[f.__name__] = f
                return f

            return decorator

        mock_mcp.tool = capture_tool
        register_tools(mock_mcp, mock_server)

        result = tools["wait_for_job_completion"](
            namespace="training", name="my-job", timeout_seconds=1
        )

        assert result["success"] is True
        assert result["final_status"] == "Completed"


def _make_mock_resource(
    name: str,
    namespace: str | None = "default",
    spec: dict | None = None,
    status: dict | None = None,
    annotations: dict | None = None,
    labels: dict | None = None,
) -> MagicMock:
    """Create a mock Kubernetes resource."""
    mock = MagicMock()
    mock.metadata.name = name
    mock.metadata.namespace = namespace
    mock.metadata.uid = f"{name}-uid"
    mock.metadata.creation_timestamp = datetime.now(timezone.utc)
    mock.metadata.labels = labels or {}
    mock.metadata.annotations = annotations or {}
    mock.spec = spec or {}
    mock.status = status or {}
    return mock
