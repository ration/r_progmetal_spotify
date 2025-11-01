# r/progmetal Album Catalog

Django web application for browsing and visualizing progressive metal album releases from r/progmetal's community-maintained spreadsheet.

## Features

- Browse album releases with cover art, metadata, and filtering
- Daily synchronization from Google Sheets
- Album metadata enriched via Spotify API
- Filter by genre and vocal style
- Responsive tile-based interface

## Data Sources

- **Google Sheets**: Community release tracker (2,147+ albums)
  - Edit view: https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/edit?gid=1232942063#gid=1232942063
  - XLSX export (preserves Spotify hyperlinks): `?format=xlsx&gid=803985331`
- **Spotify Web API**: Album metadata (cover art, release dates, etc.)

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your Spotify API credentials:
     - Register app at: https://developer.spotify.com/dashboard
     - Copy `Client ID` and `Client Secret` to `.env`

   ```bash
   cp .env.example .env
   # Edit .env and add your Spotify credentials
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Import albums:
   ```bash
   # Test with first 3 albums
   python manage.py import_albums --limit 3

   # Import first 50 albums
   python manage.py import_albums --limit 50

   # Import all 2,500+ albums (takes ~10 minutes due to Spotify API rate limits)
   python manage.py import_albums
   ```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_google_sheets_service.py -v

# Run with coverage
python -m pytest tests/ --cov=catalog --cov-report=html
```

## Architecture

- **Django 5.2.8** with Python 3.14
- **PostgreSQL** (production) / **SQLite** (development)
- **HTMX** for dynamic filtering without full page reloads
- **Spotify API** via spotipy library
- **openpyxl** for parsing XLSX exports (preserves hyperlinks)
