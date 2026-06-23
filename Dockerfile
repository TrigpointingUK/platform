FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Download OSTN15/OSGM15 grid files for accurate UK coordinate transformation
# These files enable sub-centimetre horizontal accuracy and proper height conversion
# See: docs/decisions/0001-ostn15-coordinate-conversion.md
# Files must go in pyproj's bundled PROJ data directory (pip installs its own PROJ)
RUN PROJ_DATA_DIR=$(python -c "import pyproj; print(pyproj.datadir.get_data_dir())") && \
    echo "Installing OSTN15/OSGM15 to: $PROJ_DATA_DIR" && \
    curl -fsSL -o "$PROJ_DATA_DIR/uk_os_OSTN15_NTv2_OSGBtoETRS.tif" \
        https://cdn.proj.org/uk_os_OSTN15_NTv2_OSGBtoETRS.tif && \
    curl -fsSL -o "$PROJ_DATA_DIR/uk_os_OSGM15_GB.tif" \
        https://cdn.proj.org/uk_os_OSGM15_GB.tif && \
    ls -la "$PROJ_DATA_DIR"/*.tif

# Disable PROJ network access - all grid files must be local
ENV PROJ_NETWORK=OFF

# Copy application code
COPY api/ ./api/
COPY res/ ./res/

# Inject build metadata into api/__version__.py
# These args are supplied by CI; defaults provide sensible fallbacks for local builds
ARG GIT_SHA=unknown
ARG BUILD_TIME=unknown
RUN printf "__version__ = \"%s\"\n__build_time__ = \"%s\"\n" "$GIT_SHA" "$BUILD_TIME" > api/__version__.py

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check using Python urllib (no external dependencies)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=10)" || exit 1

# Run the application (as module to ensure proper Python path)
CMD ["python", "-m", "api.start"]
