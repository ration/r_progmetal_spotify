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

2. Configure environment variables (copy `.env.example` to `.env`):
   ```bash
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   GOOGLE_SHEETS_XLSX_URL=https://docs.google.com/spreadsheets/d/.../export?format=xlsx&gid=...
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Import albums:
   ```bash
   # Test with first 10 albums
   python manage.py import_albums --limit 10

   # Import all albums
   python manage.py import_albums
   ```

## Architecture

- **Django 5.2.8** with Python 3.14
- **PostgreSQL** (production) / **SQLite** (development)
- **HTMX** for dynamic filtering without full page reloads
- **Spotify API** via spotipy library
- **openpyxl** for parsing XLSX exports (preserves hyperlinks)
