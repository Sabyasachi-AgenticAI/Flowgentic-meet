# syntax=docker/dockerfile:1

# Use the official UV Python base image with Python 3.14 on Debian Bookworm
# UV is a fast Python package manager that provides better performance than pip
# We use the slim variant to keep the image size smaller while still having essential tools
ARG PYTHON_VERSION=3.14
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Compile Python source to bytecode (.pyc) during install so the first import
# doesn't pay the compilation cost. This reduces agent cold-start time at the
# expense of a slightly longer build.
ENV UV_COMPILE_BYTECODE=1

# Ensure local models are downloaded to a shared directory accessible by all stages.
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch

# Store Playwright browser binaries inside /app so they are copied to the final stage
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers

# --- Build stage ---
# Install dependencies, build native extensions, and prepare the application
FROM base AS build

# Install build dependencies required for Python packages with native extensions
# gcc: C compiler needed for building Python packages with C extensions
# g++: C++ compiler needed for building Python packages with C extensions
# python3-dev: Python development headers needed for compilation
# We clean up the apt cache after installation to keep the image size down
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Create a new directory for our application code
# And set it as the working directory
WORKDIR /app

# Copy just the dependency files first, for more efficient layer caching
COPY pyproject.toml uv.lock ./
RUN mkdir -p src

# Install Python dependencies using UV's lock file
# --locked ensures we use exact versions from uv.lock for reproducible builds
# This creates a virtual environment and installs all dependencies
# Ensure your uv.lock file is checked in for consistency across environments
RUN uv sync --locked

# Pre-download any ML models or files the agent needs
# This runs before COPY . . so the download layer is cached across code-only changes.
# The module-level command discovers installed livekit-plugins-* packages without
# loading your agent code.
RUN uv run --module livekit.agents download-files

# Install Playwright Chromium browser binary into /app/.playwright-browsers
# so it gets copied to the final stage in COPY --from=build /app /app
# --with-deps also installs required system libraries in the build container
RUN uv run playwright install --with-deps chromium

# Copy all remaining application files into the container
# This includes source code, configuration files, and dependency specifications
# (Excludes files specified in .dockerignore)
COPY . .

# --- Production stage ---
# Build tools (gcc, g++, python3-dev) are not included in the final image
FROM base

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/build/building/best-practices/#user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Install Chromium runtime system library dependencies in the final stage
# (system libs from build stage are NOT carried over in multi-stage builds)
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
  && rm -rf /var/lib/apt/lists/*

# Copy the application and virtual environment with correct ownership in a single layer
# This avoids expensive recursive chown and excludes build tools from the final image
COPY --from=build --chown=appuser:appuser /app /app

WORKDIR /app

# Switch to the non-privileged user for all subsequent operations
# This improves security by not running as root
USER appuser

# Run the AgentServer using UV
# UV will activate the virtual environment and run the agent.
# The "start" command tells the AgentServer to connect to LiveKit and begin waiting for jobs.
CMD ["uv", "run", "src/agent.py", "start"]
