"""RHOAI annotation constants and helpers."""

from typing import Any


class RHOAIAnnotations:
    """RHOAI-specific Kubernetes annotations."""

    # Notebook annotations
    INJECT_OAUTH = "notebooks.opendatahub.io/inject-oauth"
    IMAGE_DISPLAY_NAME = "opendatahub.io/image-display-name"
    LAST_SIZE_SELECTION = "notebooks.opendatahub.io/last-size-selection"
    NOTEBOOK_STOPPED = "kubeflow-resource-stopped"
    NOTEBOOK_IMAGE_ORDER = "notebooks.opendatahub.io/last-image-selection"
    OAUTH_LOGOUT = "notebooks.opendatahub.io/oauth-logout-url"

    # Data connection annotations
    CONNECTION_TYPE = "opendatahub.io/connection-type"
    MANAGED = "opendatahub.io/managed"

    # General annotations
    DASHBOARD_DESCRIPTION = "openshift.io/description"
    DASHBOARD_DISPLAY_NAME = "openshift.io/display-name"
    REQUESTER = "openshift.io/requester"

    @classmethod
    def notebook_stopped_annotation(cls, timestamp: str) -> dict[str, str]:
        """Create annotation to stop a notebook at given timestamp."""
        return {cls.NOTEBOOK_STOPPED: timestamp}

    @classmethod
    def is_notebook_stopped(cls, annotations: dict[str, Any] | None) -> bool:
        """Check if notebook has stop annotation."""
        if not annotations:
            return False
        return cls.NOTEBOOK_STOPPED in annotations

    @classmethod
    def get_notebook_stopped_time(cls, annotations: dict[str, Any] | None) -> str | None:
        """Get the stop timestamp from notebook annotations."""
        if not annotations:
            return None
        return annotations.get(cls.NOTEBOOK_STOPPED)

    @classmethod
    def oauth_annotations(
        cls, logout_url: str | None = None, image_display_name: str | None = None
    ) -> dict[str, str]:
        """Create OAuth injection annotations for notebook."""
        annotations = {cls.INJECT_OAUTH: "true"}
        if logout_url:
            annotations[cls.OAUTH_LOGOUT] = logout_url
        if image_display_name:
            annotations[cls.IMAGE_DISPLAY_NAME] = image_display_name
        return annotations

    @classmethod
    def data_connection_annotations(cls, connection_type: str = "s3") -> dict[str, str]:
        """Create annotations for a data connection secret."""
        return {
            cls.CONNECTION_TYPE: connection_type,
            cls.MANAGED: "true",
        }
