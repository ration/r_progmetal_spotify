# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django 5.2 web application for visualizing r/progmetal release data from Google Sheets. The project uses django-htmx for interactive functionality and is styled with Tailwind CSS and DaisyUI.

## Architecture

- **Django Project Structure**: Uses a `config/` directory as the project root (not the typical project name)
  - `config/settings.py` - Django settings
  - `config/urls.py` - Root URL configuration
  - `config/wsgi.py` and `config/asgi.py` - WSGI/ASGI application entry points

- **Apps**:
  - `catalog/` - Main app for displaying release data
    - URLs mounted at `/catalog/`
    - Templates in `catalog/templates/`
    - Base template uses Tailwind CSS (via CDN) and DaisyUI

- **Database**:
  - **Development**: PostgreSQL (via Docker) or SQLite (local)
  - **Tests**: SQLite in-memory (fast, isolated)
  - **Production**: PostgreSQL

- **Frontend Stack**:
  - Tailwind CSS v4 (browser CDN)
  - DaisyUI v5 (CSS component library)
  - HTMX via django-htmx

## Development Commands

### Docker Setup (Recommended)
This project supports Docker with PostgreSQL for production-like development:
```bash
make up                    # Start Docker services (PostgreSQL + Django)
make down                  # Stop Docker services
make logs                  # View service logs
make migrate               # Run migrations in Docker
make shell                 # Open Django shell
make test                  # Run tests
make import                # Import test data
```

See `DOCKER.md` for complete Docker documentation.

### Local Development (SQLite)
For quick local development without Docker:

#### Package Management
```bash
uv sync                    # Install dependencies
uv add <package>           # Add a new dependency
uv add --dev <package>     # Add a dev dependency
```

#### Running the Development Server
```bash
python manage.py runserver
```

#### Database Operations
```bash
python manage.py makemigrations      # Create new migrations
python manage.py migrate             # Apply migrations
python manage.py createsuperuser     # Create admin user
```

### Testing
```bash
pytest                     # Run all tests
pytest <path>              # Run specific test file
pytest -k <test_name>      # Run tests matching pattern
```

### Linting
```bash
ruff check .              # Check for linting issues
ruff check --fix .        # Auto-fix linting issues
ruff format .             # Format code
```

### Type Checking
```bash
pyright                   # Run type checker
```

## Data Source

The application visualizes data from a Google Sheets document containing r/progmetal releases:
- 2025 data sheet: https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/edit?gid=1232942063#gid=1232942063
- CSV export URL: https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/export?gid=803985331#gid=803985331&format=csv
- Test data available in `tests/testdata/2025.csv`

## Album Catalog Feature (001-album-catalog branch)

### Data Flow
1. **Google Sheets CSV** → Contains Spotify album URLs and basic metadata
2. **Spotify API** → Fetches rich album metadata (cover art, artist details, genres)
3. **PostgreSQL Database** → Caches enriched album data locally

### Key Components
- **Models**: `Album`, `Artist`, `Genre`, `VocalStyle` (catalog/models.py)
- **Data Import**: Django management commands (`import_albums`, `sync_spotify`)
- **HTMX Endpoints**: Partial HTML responses for filtering without page reloads
- **Spotify Integration**: `spotipy` library for Spotify Web API access

### Environment Variables Required
```bash
# Required
SPOTIFY_CLIENT_ID=<your_spotify_client_id>
SPOTIFY_CLIENT_SECRET=<your_spotify_client_secret>
GOOGLE_SHEETS_XLSX_URL=https://docs.google.com/spreadsheets/.../export?format=xlsx

# Optional - for PostgreSQL (leave empty to use SQLite)
DATABASE_URL=postgresql://progmetal:progmetal_dev_password@localhost:5432/progmetal
```

**Note**: With Docker, `DATABASE_URL` is automatically configured in `docker-compose.yml`.

### Import Commands
```bash
python manage.py import_albums       # Import from Google Sheets + Spotify API
python manage.py sync_spotify --all  # Re-sync all albums with Spotify
```

### HTMX Patterns
- Filter changes trigger `GET /catalog/albums/?genre=djent` with `HX-Request: true` header
- Server returns HTML fragment (just tiles, not full page)
- HTMX swaps content into `#album-tiles` container
- Browser URL updated via `HX-Push-Url` response header

### Documentation
- Feature spec: `specs/001-album-catalog/spec.md`
- Implementation plan: `specs/001-album-catalog/plan.md`
- Data model: `specs/001-album-catalog/data-model.md`
- API contracts: `specs/001-album-catalog/contracts/htmx-endpoints.md`
- Setup guide: `specs/001-album-catalog/quickstart.md`

## Key Configuration Notes

- Python version: 3.14
- Django version: 5.2.8
- The project uses psycopg for PostgreSQL support (production), SQLite for development
- Static files are configured but may need collection for production: `python manage.py collectstatic`
- Secret key is currently set to a development value and should be changed for production
- Spotify API rate limit: ~180 requests per 30 seconds (handled by import script with backoff)

## Active Technologies
- Python 3.14 + Django 5.2.8, django-htmx, psycopg (PostgreSQL adapter) (002-catalog-statistics)
- PostgreSQL (production/Docker), SQLite (local development/tests) (002-catalog-statistics)
- openpyxl 3.1+ for multi-tab Google Sheets parsing (005-multi-tab-parsing)
  - Workbook enumeration via `workbook.sheetnames`
  - Tab filtering by name pattern (ends with "Prog-metal" or matches year regex)
  - Chronological sorting by extracted year (oldest to newest)
  - Per-tab album fetching with progress tracking
  - Tab-level error isolation and recovery
- Python 3.14 + Django 5.2.8, django-htmx, spotipy (Spotify API client), psycopg (PostgreSQL adapter) (006-jit-spotify-api)
- Python 3.14 + Django 5.2.8, django-htmx 1.16.0, Tailwind CSS v4 (CDN), DaisyUI v5 (007-admin-sync-page)
- PostgreSQL (production/Docker), SQLite (development/tests) (007-admin-sync-page)
- Python 3.14 + Django 5.2.8, django-allauth (for OAuth), spotipy (Spotify API client), psycopg (PostgreSQL adapter) (008-spotify-auth)

## Recent Changes
- 007-admin-sync-page: Created dedicated admin page for sync controls, moved sync button/status/timestamp from main catalog to /catalog/admin/sync
- 005-multi-tab-parsing: Added multi-tab Google Sheets parsing with openpyxl, tab filtering, chronological processing, and error isolation
- 002-catalog-statistics: Added Python 3.14 + Django 5.2.8, django-htmx, psycopg (PostgreSQL adapter)
