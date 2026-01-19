# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for RHOAI MCP Server
# Supports Docker and Podman with all transport modes (stdio, SSE, streamable-http)

# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# =============================================================================
FROM python:3.12-slim AS builder

# Copy uv from official image for fast, reproducible builds
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev dependencies for production)
# Use BuildKit cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="RHOAI MCP Server"
LABEL org.opencontainers.image.description="MCP server for Red Hat OpenShift AI - enables AI agents to interact with RHOAI environments"
LABEL org.opencontainers.image.vendor="Red Hat"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/admiller/rhoai-mcp-prototype"

# Create non-root user for security
RUN groupadd --gid 1000 rhoai && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash rhoai

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=rhoai:rhoai /app/.venv /app/.venv

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables with container-friendly defaults
# Transport: default to stdio for Claude Desktop compatibility
ENV RHOAI_MCP_TRANSPORT="stdio"
# HTTP binding: use 0.0.0.0 for container networking
ENV RHOAI_MCP_HOST="0.0.0.0"
ENV RHOAI_MCP_PORT="8000"
# Auth: default to auto-detection
ENV RHOAI_MCP_AUTH_MODE="auto"
# Logging: default to INFO
ENV RHOAI_MCP_LOG_LEVEL="INFO"

# Expose port for HTTP transports (SSE, streamable-http)
EXPOSE 8000

# Switch to non-root user
USER rhoai

# Health check for HTTP transports
# Note: Only works with SSE/streamable-http, not stdio
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 0

# Default entrypoint runs the MCP server
ENTRYPOINT ["rhoai-mcp"]

# Default to stdio transport (can be overridden with --transport sse|streamable-http)
CMD ["--transport", "stdio"]
