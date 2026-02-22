# syntax=docker/dockerfile:1

# Multi-stage build for optimized image size and faster rebuilds
# Stage 1: Builder - Install build dependencies and compile packages

FROM python:3.12-alpine AS builder

WORKDIR /build

# Install build dependencies (only needed during build, not runtime)
RUN apk add --no-cache \
    gcc \
    g++ \
    python3-dev \
    musl-dev \
    linux-headers \
    freetype-dev \
    make

# Create virtual environment in a known location
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set environment variables for pip
ENV PIP_DEFAULT_TIMEOUT=60
ENV PIP_RETRY_MAX=5

### START OF FREETYPE FUNCTIONALITY
ENV FREETYPE_VERSION=2.6.1
ENV FREETYPE_DIR=/build/freetype-2.6.1

# Copy FreeType tar file and extract it
# The URL for FreeType download - must be manually dragged to freetype folder in polari
# Trying to use wget WILL NOT WORK, it is hosted on a mirror which prevents automated retrieval.
COPY freetype/freetype-2.6.1.tar.gz /tmp/freetype.tar.gz

# Extract the tar file into the specified directory
RUN tar -xf /tmp/freetype.tar.gz -C /build --strip-components=1 && \
    rm /tmp/freetype.tar.gz

# Set environment variable to point to FreeType build directory
ENV FREETYPE_ROOT=$FREETYPE_DIR
ENV LD_LIBRARY_PATH="$FREETYPE_DIR/builds/unix/:$LD_LIBRARY_PATH"

### END OF FREETYPE FUNCTIONALITY

# Copy requirements file FIRST (separate layer for better caching)
# This layer only rebuilds when requirements.txt changes
COPY requirements.txt /build/requirements.txt

# Install Python dependencies using cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r /build/requirements.txt && \
    pip install psutil

# Stage 2: Runtime - Minimal image with only runtime dependencies

FROM python:3.12-alpine

WORKDIR /app

# Install only runtime dependencies (much smaller than build dependencies)
# sqlite-libs and libstdc++ are needed for tippecanoe binary
RUN apk add --no-cache freetype sqlite-libs libstdc++

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy FreeType from builder
COPY --from=builder /build /build

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV IN_DOCKER_CONTAINER=true
ENV PORT=3000
ENV DEPLOY_ENV=development
ENV FREETYPE_VERSION=2.6.1
ENV FREETYPE_DIR=/build/freetype-2.6.1
ENV FREETYPE_ROOT=$FREETYPE_DIR
ENV LD_LIBRARY_PATH="$FREETYPE_DIR/builds/unix/:$LD_LIBRARY_PATH"
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code LAST (this layer invalidates most often)
# This ensures dependency layers are cached and reused
COPY . /app

# Ensure data directory exists for SQLite database (volume mount point)
RUN mkdir -p /app/data

# Expose HTTP and HTTPS ports
# HTTP: 3000 (default), HTTPS: 2096 (Cloudflare-compatible)
EXPOSE $PORT
EXPOSE 2096

# Run the application
CMD ["python3", "initLocalhostPolariServer.py"]

# Debug options (uncomment as needed):
# For shell access: docker exec -it container_name_or_id /bin/sh
# CMD ["sleep", "infinity"]
# CMD ["tail", "-f", "/dev/null"]