# Dockerfile for Django Album Catalog Application
# Python 3.14 with uv package manager

FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user with home directory
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1000 -g appuser -m -d /home/appuser appuser

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager as root, then make it accessible to appuser
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh && \
    cp -r /root/.local /home/appuser/.local && \
    chown -R appuser:appuser /home/appuser/.local

# Ensure the installed binary is on the `PATH`
ENV PATH="/home/appuser/.local/bin/:$PATH"

# Copy dependency files
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv sync --frozen && chown -R appuser:appuser /app/.venv

# Add venv to PATH so python/django commands work directly
ENV PATH="/app/.venv/bin:$PATH"

# Copy project files
COPY --chown=appuser:appuser . .

# Create directory for PostgreSQL socket (if needed)
RUN mkdir -p /var/run/postgresql && chmod 777 /var/run/postgresql

# Ensure app directory is owned by appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8000 for Django development server
EXPOSE 8000

# Run migrations and start development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
