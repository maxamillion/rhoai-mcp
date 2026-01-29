"""Utility functions and helpers for RHOAI MCP server."""

from rhoai_mcp.utils.annotations import RHOAIAnnotations
from rhoai_mcp.utils.cache import (
    cache_stats,
    cached,
    clear_cache,
    clear_expired,
    invalidate,
)
from rhoai_mcp.utils.errors import (
    AuthenticationError,
    ConfigurationError,
    EnhancedError,
    ErrorPattern,
    NotFoundError,
    OperationNotAllowedError,
    ResourceExistsError,
    RHOAIError,
    ValidationError,
    enhance_error,
    wrap_error_response,
)
from rhoai_mcp.utils.labels import RHOAILabels
from rhoai_mcp.utils.response import (
    PaginatedResponse,
    ResponseBuilder,
    Verbosity,
    paginate,
)

__all__ = [
    # Errors
    "RHOAIError",
    "NotFoundError",
    "AuthenticationError",
    "ConfigurationError",
    "ValidationError",
    "OperationNotAllowedError",
    "ResourceExistsError",
    # Error enhancement
    "EnhancedError",
    "ErrorPattern",
    "enhance_error",
    "wrap_error_response",
    # Labels and annotations
    "RHOAIAnnotations",
    "RHOAILabels",
    # Response formatting
    "Verbosity",
    "ResponseBuilder",
    "PaginatedResponse",
    "paginate",
    # Caching
    "cached",
    "clear_cache",
    "clear_expired",
    "cache_stats",
    "invalidate",
]
