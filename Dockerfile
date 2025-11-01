# Dockerfile for Django Album Catalog Application
# Python 3.14 with uv package manager

FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv sync --frozen

# Copy project files
COPY . .

# Create directory for PostgreSQL socket (if needed)
RUN mkdir -p /var/run/postgresql && chmod 777 /var/run/postgresql

# Expose port 8000 for Django development server
EXPOSE 8000

# Run migrations and start development server
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
