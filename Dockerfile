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
    curl \
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
ENV FREETYPE_SHA256=0a3c7dfbda6da1e8fce29232e8e96d987ababbbf71ebc8c75659e4132c367014

# Fetched at build time rather than vendored into git — a 2.2MB tarball
# that git would keep forever, plus a manual "drag the file in" step.
#
# The old comment here claimed automated retrieval was impossible. That
# was a wget-without-redirects problem: the SourceForge mirror serves it
# fine over `curl -L`, byte-identical to what was vendored. Several hosts
# are tried so no single one is load-bearing (savannah 502s periodically),
# and the checksum gate means a wrong or tampered tarball fails the build
# instead of silently building against it.
RUN set -eux; \
    for url in \
      "https://download.savannah.gnu.org/releases/freetype/freetype-${FREETYPE_VERSION}.tar.gz" \
      "https://downloads.sourceforge.net/project/freetype/freetype2/${FREETYPE_VERSION}/freetype-${FREETYPE_VERSION}.tar.gz" \
      "https://mirrors.kernel.org/gentoo/distfiles/freetype-${FREETYPE_VERSION}.tar.gz" ; do \
        echo "trying $url"; \
        if curl -fsSL --retry 2 --connect-timeout 20 -o /tmp/freetype.tar.gz "$url"; then \
          if echo "${FREETYPE_SHA256}  /tmp/freetype.tar.gz" | sha256sum -c -; then break; fi; \
          echo "checksum mismatch from $url — discarding"; \
        fi; \
        rm -f /tmp/freetype.tar.gz; \
    done; \
    test -f /tmp/freetype.tar.gz; \
    echo "${FREETYPE_SHA256}  /tmp/freetype.tar.gz" | sha256sum -c -; \
    tar -xf /tmp/freetype.tar.gz -C /build --strip-components=1; \
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
# ngspice: the electrodevice circuit engine (materials -> SPICE
# ladder) rides in-backend like scikit-fem — capability-honest if
# the package ever goes missing.
# ffmpeg: video module (modules/video/) WebM/MP4/HLS conversion —
# same capability-honest pattern (video_conversion.py checks
# shutil.which('ffmpeg') and reports missing rather than crashing).
RUN apk add --no-cache freetype sqlite-libs libstdc++ ngspice ffmpeg git   # git: an instance fetches optional modules from their repositories (fetch-admit)

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
# mp-1: modules/ is a second import root — relocated feature modules
# keep their import names in EVERY python process (server, selftest
# subprocesses, docker exec), not just where sitecustomize loads.
# fetched (optional) modules live on the data volume so they survive a restart; the image tree stays read-only-ish
ENV PYTHONPATH=/app/data/modules:/app/modules
ENV POLARI_FETCHED_MODULES_DIR=/app/data/modules

# Copy application code LAST (this layer invalidates most often)
# This ensures dependency layers are cached and reused
COPY . /app
# Image variants (his rule 2026-09-12): `core` carries only the core-tier modules — what makes Polari a networking
# and app system; optional modules are fetched from their polari-module-* repositories on admission (the register
# stays, so the instance knows where). `all` (default) carries every official module.
ARG POLARI_MODULE_SET=all
ENV POLARI_MODULE_SET=${POLARI_MODULE_SET}
RUN if [ "$POLARI_MODULE_SET" = core ]; then python3 -c "import json,shutil,os; reg=json.load(open('/app/modules/polari-modules.json'))['modules']; gone=[m for m,e in reg.items() if e.get('tier','optional')!='core' and os.path.isdir('/app/modules/'+m)]; [shutil.rmtree('/app/modules/'+m) for m in gone]; print('core image: removed %d optional module(s), kept %d core' % (len(gone), sum(1 for e in reg.values() if e.get('tier')=='core')))"; fi
LABEL org.opencontainers.image.variant=${POLARI_MODULE_SET}

# Ensure data directory exists for SQLite database (volume mount point)
RUN mkdir -p /app/data/modules && chmod -R a+rwX /app/data /app/modules   # any runtime uid may fetch modules and write data

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