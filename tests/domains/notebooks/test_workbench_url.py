"""Tests for workbench URL resolution from OpenShift Routes."""

from unittest.mock import MagicMock

import pytest

from rhoai_mcp.domains.notebooks.client import NotebookClient
from rhoai_mcp.utils.errors import NotFoundError, RHOAIError


class TestGetWorkbenchUrl:
    """Test _get_workbench_url Route-based URL resolution."""

    @pytest.fixture
    def mock_k8s(self) -> MagicMock:
        """Create a mock K8sClient."""
        return MagicMock()

    @pytest.fixture
    def client(self, mock_k8s: MagicMock) -> NotebookClient:
        """Create a NotebookClient with mocked K8sClient."""
        return NotebookClient(mock_k8s)

    def test_route_with_tls_returns_https(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When Route has TLS config, return https URL."""
        mock_route = MagicMock()
        mock_route.spec.host = "my-wb-test-ns.apps.cluster.example.com"
        mock_route.spec.tls = MagicMock()  # TLS present
        mock_k8s.get.return_value = mock_route

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url == "https://my-wb-test-ns.apps.cluster.example.com"

    def test_route_without_tls_returns_http(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When Route has no TLS config, return http URL."""
        mock_route = MagicMock()
        mock_route.spec.host = "my-wb-test-ns.apps.cluster.example.com"
        mock_route.spec.tls = None
        mock_k8s.get.return_value = mock_route

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url == "http://my-wb-test-ns.apps.cluster.example.com"

    def test_route_not_found_returns_none(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When Route does not exist, return None."""
        mock_k8s.get.side_effect = NotFoundError("Route", "my-wb", "test-ns")

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url is None

    def test_permission_denied_returns_none(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When SA lacks Route read permission (403), return None."""
        mock_k8s.get.side_effect = RHOAIError("Failed to get Route 'my-wb': Forbidden")

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url is None

    def test_crd_not_available_returns_none(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When Route CRD is not available (non-OpenShift), return None."""
        mock_k8s.get.side_effect = RHOAIError(
            "Resource not found: route.openshift.io/v1/Route"
        )

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url is None

    def test_route_with_empty_host_returns_none(
        self, client: NotebookClient, mock_k8s: MagicMock
    ) -> None:
        """When Route exists but has no host, return None."""
        mock_route = MagicMock()
        mock_route.spec.host = ""
        mock_k8s.get.return_value = mock_route

        url = client._get_workbench_url("my-wb", "test-ns")

        assert url is None
