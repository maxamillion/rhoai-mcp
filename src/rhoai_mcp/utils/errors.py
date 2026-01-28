"""Custom exceptions for RHOAI MCP server."""

from typing import Any


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
