"""Custom exceptions and error handling for RHOAI MCP server.

This module provides custom exceptions and utilities for enhancing
error messages with actionable recovery guidance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnhancedError:
    """An error with enhanced context for agent recovery.

    Wraps error messages with additional context to help agents
    recover from failures.
    """

    error: str
    """The original error message."""

    error_code: str
    """A categorized error code (e.g., 'NOT_FOUND', 'AUTH_FAILED')."""

    suggestion: str
    """Actionable suggestion for recovery."""

    related_tools: list[str] = field(default_factory=list)
    """Tools that might help resolve the issue."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for tool response."""
        return {
            "error": self.error,
            "error_code": self.error_code,
            "suggestion": self.suggestion,
            "related_tools": self.related_tools,
        }


@dataclass
class ErrorPattern:
    """A pattern for matching and enhancing errors.

    Used to recognize common errors and provide targeted guidance.
    """

    pattern: str
    """Regex pattern to match against error messages."""

    error_code: str
    """The error code to assign when this pattern matches."""

    suggestion: str
    """The suggestion to provide when this pattern matches."""

    related_tools: list[str] = field(default_factory=list)
    """Tools that might help resolve this type of error."""


# Common error patterns for RHOAI MCP operations
ERROR_PATTERNS: list[ErrorPattern] = [
    # Image pull errors
    ErrorPattern(
        pattern=r"(?i)imagepullbackoff|errimagepull|failed to pull",
        error_code="IMAGE_PULL_FAILED",
        suggestion="The container image could not be pulled. Verify the image name "
        "exists and is accessible. Use list_notebook_images to see available images.",
        related_tools=["list_notebook_images"],
    ),
    # GPU errors
    ErrorPattern(
        pattern=r"(?i)gpu.*unavailable|insufficient.*nvidia|nvidia.*not found",
        error_code="GPU_UNAVAILABLE",
        suggestion="No GPU resources are available. Check cluster accelerator "
        "profiles or reduce gpu_count to 0.",
        related_tools=["get_workbench"],
    ),
    # Quota errors
    ErrorPattern(
        pattern=r"(?i)exceeded quota|resource quota|insufficient.*cpu|insufficient.*memory",
        error_code="QUOTA_EXCEEDED",
        suggestion="Resource quota exceeded. Try reducing resource requests "
        "(cpu_request, memory_request) or contact an administrator.",
        related_tools=["get_project"],
    ),
    # Namespace errors (more specific, must come before generic "not found")
    ErrorPattern(
        pattern=r"(?i)namespace.*not found|project.*not found",
        error_code="NAMESPACE_NOT_FOUND",
        suggestion="The specified project/namespace does not exist. "
        "Use list_projects to see available projects.",
        related_tools=["list_projects", "create_project"],
    ),
    # Not found errors (generic, comes after more specific patterns)
    ErrorPattern(
        pattern=r"(?i)not found|does not exist|404",
        error_code="NOT_FOUND",
        suggestion="The requested resource was not found. Verify the name "
        "and namespace are correct, or list resources to see available options.",
        related_tools=["list_projects", "list_workbenches"],
    ),
    # Authentication errors
    ErrorPattern(
        pattern=r"(?i)unauthorized|forbidden|403|401|authentication.*fail",
        error_code="AUTH_FAILED",
        suggestion="Authentication or authorization failed. Check that the "
        "kubeconfig is valid and you have permissions for this operation.",
        related_tools=[],
    ),
    # Connection errors
    ErrorPattern(
        pattern=r"(?i)connection.*refused|network.*unreachable|timeout",
        error_code="CONNECTION_FAILED",
        suggestion="Failed to connect to the Kubernetes API. Check network "
        "connectivity and cluster availability.",
        related_tools=[],
    ),
    # Validation errors
    ErrorPattern(
        pattern=r"(?i)invalid.*name|dns.*invalid|must.*consist of|must be.*valid",
        error_code="INVALID_NAME",
        suggestion="The resource name is invalid. Names must be DNS-compatible: "
        "lowercase letters, numbers, and hyphens only, starting with a letter.",
        related_tools=[],
    ),
    # Already exists
    ErrorPattern(
        pattern=r"(?i)already exists|conflict|409",
        error_code="ALREADY_EXISTS",
        suggestion="A resource with this name already exists. Use a different "
        "name or delete the existing resource first.",
        related_tools=["list_workbenches", "list_inference_services"],
    ),
    # Read-only mode
    ErrorPattern(
        pattern=r"(?i)read.only|operation.*not allowed|disabled",
        error_code="OPERATION_DISABLED",
        suggestion="This operation is disabled. The server may be in read-only "
        "mode or dangerous operations may be disabled.",
        related_tools=[],
    ),
    # Storage errors
    ErrorPattern(
        pattern=r"(?i)pvc.*not found|persistent.*volume|storage.*unavailable",
        error_code="STORAGE_ERROR",
        suggestion="Storage is unavailable or not found. Use list_storage to "
        "see available PVCs or create new storage.",
        related_tools=["list_storage", "create_storage"],
    ),
    # Model format errors
    ErrorPattern(
        pattern=r"(?i)unsupported.*format|model.*format|invalid.*model",
        error_code="INVALID_MODEL_FORMAT",
        suggestion="The model format is not supported. Supported formats include: "
        "onnx, pytorch, tensorflow, and others depending on the runtime.",
        related_tools=["list_serving_runtimes"],
    ),
]


def enhance_error(error_message: str) -> EnhancedError:
    """Enhance an error message with recovery guidance.

    Matches the error against known patterns and provides
    actionable suggestions for recovery.

    Args:
        error_message: The original error message.

    Returns:
        An EnhancedError with context and suggestions.
    """
    for pattern in ERROR_PATTERNS:
        if re.search(pattern.pattern, error_message):
            return EnhancedError(
                error=error_message,
                error_code=pattern.error_code,
                suggestion=pattern.suggestion,
                related_tools=pattern.related_tools,
            )

    # Default enhancement for unknown errors
    return EnhancedError(
        error=error_message,
        error_code="UNKNOWN_ERROR",
        suggestion="An unexpected error occurred. Check the error message "
        "for details and try again.",
        related_tools=[],
    )


def wrap_error_response(error: str | Exception) -> dict[str, Any]:
    """Wrap an error into a standardized tool response.

    This function is intended for use in tool implementations
    to provide consistent error responses with recovery guidance.

    Args:
        error: The error message or exception.

    Returns:
        A dictionary suitable for returning from a tool.
    """
    error_message = str(error)
    enhanced = enhance_error(error_message)
    return enhanced.to_dict()


class RHOAIError(Exception):
    """Base exception for RHOAI MCP operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class NotFoundError(RHOAIError):
    """Resource not found."""

    def __init__(self, resource_type: str, name: str, namespace: str | None = None) -> None:
        location = f" in namespace '{namespace}'" if namespace else ""
        super().__init__(
            f"{resource_type} '{name}' not found{location}",
            {"resource_type": resource_type, "name": name, "namespace": namespace},
        )


class AuthenticationError(RHOAIError):
    """Authentication or authorization error."""

    def __init__(self, message: str = "Failed to authenticate with Kubernetes API") -> None:
        super().__init__(message)


class ConfigurationError(RHOAIError):
    """Configuration error."""

    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, details)


class ValidationError(RHOAIError):
    """Input validation error."""

    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, details)


class OperationNotAllowedError(RHOAIError):
    """Operation not allowed due to safety settings."""

    def __init__(self, operation: str, reason: str | None = None) -> None:
        message = f"Operation '{operation}' is not allowed"
        if reason:
            message += f": {reason}"
        super().__init__(message, {"operation": operation, "reason": reason})


class ResourceExistsError(RHOAIError):
    """Resource already exists."""

    def __init__(self, resource_type: str, name: str, namespace: str | None = None) -> None:
        location = f" in namespace '{namespace}'" if namespace else ""
        super().__init__(
            f"{resource_type} '{name}' already exists{location}",
            {"resource_type": resource_type, "name": name, "namespace": namespace},
        )
