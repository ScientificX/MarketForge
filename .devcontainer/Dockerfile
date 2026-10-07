FROM mcr.microsoft.com/devcontainers/python:3.12

# Install uv (fast, reproducible Python package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy

# Keep the image reproducible; dependencies are installed by `postCreateCommand`.
WORKDIR /workspaces/MarketForge
