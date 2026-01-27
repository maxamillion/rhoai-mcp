"""Core domain modules for RHOAI MCP.

This package contains the core domain functionality that was previously
split across separate packages. These domains are now registered directly
with the server rather than via entry points.

External plugins (like training) still use entry point discovery.
"""

from rhoai_mcp_core.domains.registry import DomainModule, get_core_domains

__all__ = ["DomainModule", "get_core_domains"]
