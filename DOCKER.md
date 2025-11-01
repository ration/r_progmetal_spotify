# Docker Development Guide

Complete guide for running the Album Catalog application with Docker and PostgreSQL.

## Quick Start

```bash
# Start services
make up

# Run migrations
make migrate

# Import test data (10 albums)
make import

# View logs
make logs

# Access application
open http://localhost:8000
```

## Prerequisites

- **Docker**: Install from [docker.com](https://docs.docker.com/get-docker/)
- **Docker Compose**: Included with Docker Desktop, or install separately
- **Make**: Usually pre-installed on Linux/macOS. Windows: use WSL or Git Bash

Verify installation:
```bash
docker --version
docker-compose --version
make --version
```

## Architecture

The Docker setup consists of two services:

1. **PostgreSQL Database** (`db`)
   - Image: `postgres:16-alpine`
   - Port: `5432`
   - Database: `progmetal`
   - User: `progmetal`
   - Password: `progmetal_dev_password`
   - Volume: `postgres_data` (persists between restarts)

2. **Django Application** (`web`)
   - Built from: `./Dockerfile`
   - Port: `8000`
   - Mounts: Current directory as `/app` (live code reload)
   - Depends on: `db` service (waits for PostgreSQL health check)

## Configuration Files

### docker-compose.yml
Main orchestration file defining services, networks, and volumes.

### Dockerfile
Django application container definition using Python 3.14 and uv package manager.

### .dockerignore
Excludes unnecessary files from Docker build context (faster builds).

### docker/postgres/
- `init.sql`: Database initialization script
- `postgresql.conf`: PostgreSQL configuration tuning

### scripts/docker-entrypoint.sh
Container startup script (migrations, static files, superuser creation).

## Makefile Commands

### Service Management
```bash
make up          # Start all services in background
make down        # Stop all services
make restart     # Restart all services
make build       # Rebuild Docker images
make status      # Show service status
```

### Logs and Debugging
```bash
make logs        # View logs from all services
make logs-db     # View PostgreSQL logs only
make logs-web    # View Django logs only
```

### Database Operations
```bash
make migrate          # Run migrations
make makemigrations   # Create new migrations
make createsuperuser  # Create Django admin user
```

### Shell Access
```bash
make shell       # Open Django shell
make bash        # Open bash shell in web container
make psql        # Connect to PostgreSQL database
```

### Data Import
```bash
make import      # Import 10 test albums
make import-all  # Import all 2,500+ albums (takes ~10 min)
```

### Testing
```bash
make test        # Run all tests
make test-cov    # Run tests with coverage report
```

### Database Backup/Restore
```bash
make db-backup                        # Backup database to SQL file
make db-restore FILE=backup.sql       # Restore from SQL file
```

### Cleanup
```bash
make clean       # Stop services and DELETE all data (WARNING!)
make prune       # Remove unused Docker images/containers
```

### Development Shortcuts
```bash
make dev         # Start services and run migrations
make dev-fresh   # Clean start with fresh database
make dev-import  # Start services and import test data
```

## Environment Variables

The application uses environment variables from `.env` file:

```bash
# Required for Spotify API
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret

# Required for Google Sheets
GOOGLE_SHEETS_XLSX_URL=https://docs.google.com/.../export?format=xlsx&gid=...

# Database URL (set by docker-compose.yml, no need to change)
DATABASE_URL=postgresql://progmetal:progmetal_dev_password@localhost:5432/progmetal

# Django settings
DEBUG=True
SECRET_KEY=django-insecure-local-dev-key
```

**Note**: `DATABASE_URL` is automatically set in `docker-compose.yml`, but you can override it in `.env` if needed.

## Common Workflows

### First Time Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd progmetal

# 2. Create .env file
cp .env.example .env
# Edit .env and add your Spotify API credentials

# 3. Start services
make dev

# 4. Import data
make import

# 5. Access application
open http://localhost:8000
```

### Daily Development
```bash
# Start services (if not running)
make up

# View logs while working
make logs

# Run tests before committing
make test

# Stop when done
make down
```

### Database Reset
```bash
# WARNING: This deletes all data!
make clean
make dev
make import
```

### Creating Migrations
```bash
# After modifying models
make makemigrations

# Apply migrations
make migrate
```

### Debugging
```bash
# Check service status
make status

# View detailed logs
make logs

# Access Django shell
make shell

# Access PostgreSQL directly
make psql
```

## Troubleshooting

### Services won't start
```bash
# Check what's using port 5432 or 8000
sudo lsof -i :5432
sudo lsof -i :8000

# View detailed error messages
docker-compose logs

# Rebuild images
make build
make up
```

### Database connection errors
```bash
# Check PostgreSQL is healthy
docker-compose ps

# Wait a few seconds and retry
make restart

# Check DATABASE_URL in .env
```

### Permission errors
```bash
# Fix volume permissions
docker-compose down
docker volume rm progmetal_postgres_data
make dev
```

### Code changes not reflected
```bash
# Restart Django
make restart

# For dependency changes, rebuild
make build
make up
```

### Tests failing
```bash
# Tests use SQLite (not PostgreSQL)
# Run outside Docker for debugging
python -m pytest tests/ -v

# Check if migrations are applied
make migrate
```

## Performance Tips

1. **Use volume mounts for development**: Current setup mounts code directory for live reload
2. **Use PostgreSQL locally**: Faster than accessing from container
3. **Limit imports during development**: Use `make import` (10 albums) instead of `make import-all`
4. **Prune unused Docker resources**: Run `make prune` periodically

## Production Considerations

This Docker setup is optimized for **development**. For production:

1. **Use production PostgreSQL**: Not the Docker container
2. **Set `DEBUG=False`**: In environment variables
3. **Use proper SECRET_KEY**: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
4. **Configure ALLOWED_HOSTS**: Add your domain
5. **Use Gunicorn/uWSGI**: Instead of `runserver`
6. **Enable HTTPS**: Use reverse proxy (nginx)
7. **Set up logging**: Configure Django logging properly
8. **Use Docker secrets**: For sensitive credentials

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Docker Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
