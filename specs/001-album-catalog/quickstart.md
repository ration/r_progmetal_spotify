# Quickstart: Album Catalog Development Setup

**Feature**: Album Catalog Visualization
**Date**: 2025-11-01
**Purpose**: Guide developers through setup and first test

## Prerequisites

- Python 3.14 installed
- Git repository cloned
- Spotify Developer account (for API credentials)
- Google Sheets with album data (CSV export accessible)

---

## 1. Environment Setup

###Step 1: Install Dependencies

```bash
# Sync dependencies with uv
uv sync

# Add spotipy for Spotify API integration
uv add "spotipy~=2.24.0"

# Verify installation
python --version  # Should show Python 3.14.x
django-admin --version  # Should show Django 5.2.8
```

### Step 2: Configure Database

**Development** (SQLite - no setup needed):
```bash
# Default Django configuration uses SQLite
# Database file will be created at: ./db.sqlite3
```

**Production** (PostgreSQL - optional for local testing):
```bash
# Install PostgreSQL (if testing production config)
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib libpq-dev

# macOS:
brew install postgresql

# Create database
createdb progmetal

# Update config/settings.py DATABASES (or use .env file)
```

### Step 3: Configure Spotify API

1. **Create Spotify App**:
   - Visit https://developer.spotify.com/dashboard
   - Click "Create app"
   - App name: "Progmetal Visualizer"
   - Redirect URI: `http://localhost:8000/callback` (not used but required)
   - API: Web API
   - Save and note Client ID and Client Secret

2. **Set Environment Variables**:

Create `.env` file in project root:
```env
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here

# Google Sheets CSV URL
GOOGLE_SHEETS_CSV_URL=https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/export?gid=803985331&format=csv

# Django Settings
DEBUG=True
SECRET_KEY=django-insecure-local-dev-key-change-in-production
```

3. **Update Django Settings**:

In `config/settings.py`, add:
```python
import os
from pathlib import Path

# Spotify API Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Google Sheets
GOOGLE_SHEETS_CSV_URL = os.getenv('GOOGLE_SHEETS_CSV_URL')
```

---

## 2. Database Setup

### Run Migrations

```bash
# Create database tables
python manage.py makemigrations catalog
python manage.py migrate

# Verify migrations
python manage.py showmigrations
```

**Expected Output**:
```
catalog
 [X] 0001_initial
 [X] 0002_seed_genres_vocal_styles
```

### Seed Reference Data

Genres and vocal styles are seeded via data migration (`0002_seed_genres_vocal_styles`):

- Genres: Progressive Metal, Djent, Technical Death Metal, Post-Metal, etc.
- Vocal Styles: Clean Vocals, Harsh Vocals, Mixed Vocals, Instrumental

**Verify seed data**:
```bash
python manage.py shell
>>> from catalog.models import Genre, VocalStyle
>>> Genre.objects.count()  # Should return 8
>>> VocalStyle.objects.count()  # Should return 4
```

---

## 3. Import Album Data

### Run Import Command

```bash
# Import albums from Google Sheets + Spotify API
python manage.py import_albums

# Expected output:
# Fetching CSV from Google Sheets...
# Parsing 150 rows...
# Fetching album 1/150 from Spotify: Haken - Fauna
# Fetching album 2/150 from Spotify: Tesseract - War of Being
# ...
# Import complete: 145 albums created, 3 updated, 2 errors
```

### Verify Import

```bash
python manage.py shell
>>> from catalog.models import Album
>>> Album.objects.count()  # Should match successful imports
>>> album = Album.objects.first()
>>> print(f"{album.artist.name} - {album.name}")
>>> print(f"Cover: {album.cover_art_url}")
```

**Troubleshooting**:
- **Spotify API errors**: Check credentials in `.env`
- **CSV fetch errors**: Verify Google Sheets URL is publicly accessible
- **Rate limiting**: Import script includes exponential backoff, may take 5-10 minutes for large datasets

---

## 4. Run Development Server

```bash
# Start Django development server
python manage.py runserver

# Server will start at: http://127.0.0.1:8000/
```

### Verify Application

**Open in browser**: http://127.0.0.1:8000/catalog/albums/

**Expected Behavior**:
- Album tiles displayed in grid layout
- Each tile shows: cover image, album name, artist, genre, release year
- Filters available: Genre dropdown, Vocal Style dropdown
- Clicking tile navigates to album detail page
- Responsive layout (test by resizing browser window)

---

## 5. Run Tests

### Setup Test Database

```bash
# pytest will use separate test database (auto-created/destroyed)
pytest --version  # Verify pytest installed
```

### Run Test Suite

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                 # Unit tests only
pytest tests/integration/          # Integration tests only
pytest tests/contract/             # Contract tests only

# Run with coverage
pytest --cov=catalog --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Expected Test Results

**Test Counts** (will be added during implementation):
- Unit tests: ~15 tests (models, import logic, helpers)
- Integration tests: ~10 tests (views, HTMX responses, filters)
- Contract tests: ~5 tests (Spotify API mocking, CSV parsing)

**Coverage Target**: > 80% (Constitution principle II: TDD)

---

## 6. Development Workflow

### Test-Driven Development (TDD)

**Per Constitution Principle II**, follow red-green-refactor:

1. **Write Test** (Red):
   ```bash
   # Create test file (e.g., tests/unit/test_album_model.py)
   pytest tests/unit/test_album_model.py::test_album_validation
   # Test fails (expected)
   ```

2. **Implement** (Green):
   ```bash
   # Add model validation logic (catalog/models.py)
   pytest tests/unit/test_album_model.py::test_album_validation
   # Test passes
   ```

3. **Refactor**:
   ```bash
   # Improve code quality
   pytest  # All tests still pass
   ```

4. **Commit** (Atomic):
   ```bash
   git add tests/unit/test_album_model.py catalog/models.py
   git commit -m "feat: add album validation logic

   - Validate spotify_album_id format
   - Validate spotify_url prefix
   - Strip whitespace from album name

   Tests pass. Red-green-refactor cycle followed."
   ```

### Code Quality Checks

```bash
# Linting
ruff check .
ruff check --fix .  # Auto-fix issues

# Formatting
ruff format .

# Type checking
pyright

# All checks must pass before commit (per Constitution)
```

### Django Debug Toolbar

**Enable in development** (already configured):
- Visit http://127.0.0.1:8000/catalog/albums/
- Debug toolbar appears on right side of page
- Inspect SQL queries, template rendering, cache hits

**Key Panels**:
- **SQL**: Verify `select_related()` usage (should see JOINs, not N+1 queries)
- **Time**: Check view execution time (target < 1 second)
- **Templates**: See which templates rendered

---

## 7. Common Development Tasks

### Add New Album Manually (Shell)

```bash
python manage.py shell
>>> from catalog.models import Album, Artist, Genre, VocalStyle
>>> artist, _ = Artist.objects.get_or_create(name="Tool", country="USA")
>>> genre = Genre.objects.get(slug="progressive-metal")
>>> vocal = VocalStyle.objects.get(slug="clean-vocals")
>>> album = Album.objects.create(
...     name="Fear Inoculum",
...     artist=artist,
...     genre=genre,
...     vocal_style=vocal,
...     spotify_album_id="7acEciVtnuTzmwKptkjth5",
...     spotify_url="https://open.spotify.com/album/7acEciVtnuTzmwKptkjth5",
...     release_date="2019-08-30",
...     cover_art_url="https://i.scdn.co/image/..."
... )
>>> print(f"Created: {album}")
```

### Re-sync Specific Album

```bash
python manage.py sync_spotify --album-id 7acEciVtnuTzmwKptkjth5

# Or re-sync all albums (update metadata)
python manage.py sync_spotify --all
```

### Clear Database and Re-import

```bash
# Delete all albums (cascades to related data)
python manage.py shell
>>> from catalog.models import Album
>>> Album.objects.all().delete()

# Re-import
python manage.py import_albums
```

### View Import Logs

```bash
# Logs stored in console and/or file (check config/settings.py LOGGING)
tail -f logs/django.log  # If file logging enabled

# Check specific import errors
python manage.py import_albums 2>&1 | grep ERROR
```

---

## 8. Frontend Development

### Static Files

**CSS** (Tailwind + Custom):
- Base styles: `catalog/static/catalog/css/album-catalog.css`
- Tailwind CDN loaded in `templates/catalog/base.html`

**Images**:
- Placeholder album cover: `catalog/static/catalog/images/placeholder-album.png`

**Collect Static** (for production):
```bash
python manage.py collectstatic
# Files copied to STATIC_ROOT (configured in settings.py)
```

### Template Development

**Template Hierarchy**:
```
templates/base.html                  # Project-wide base (Tailwind, HTMX)
└── catalog/album_list.html          # Catalog page layout
    └── catalog/album_list_tiles.html  # HTMX fragment (tiles only)
        └── catalog/components/album_tile.html  # Single tile component
```

**Test Template Changes**:
1. Edit template file
2. Refresh browser (no server restart needed)
3. Inspect HTMX network requests in DevTools (XHR tab)

### HTMX Debugging

**Browser DevTools**:
- Network tab → Filter XHR → See HTMX requests
- Check `HX-Request: true` header
- Verify response is HTML fragment (not full page)

**HTMX Console Logs**:
```html
<script>
    htmx.logger = function(elt, event, data) {
        if(console) {
            console.log("HTMX:", event, data);
        }
    }
</script>
```

---

## 9. Troubleshooting

### Issue: Spotify API 401 Unauthorized

**Cause**: Invalid or expired credentials

**Solution**:
```bash
# Verify credentials in .env
cat .env | grep SPOTIFY

# Test credentials manually
python -c "
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
))

album = sp.album('3IBcauSj5M2A6lTeffJzdv')
print(f'Success: {album[\"name\"]}')
"
```

### Issue: Google Sheets CSV 403 Forbidden

**Cause**: CSV export URL not publicly accessible

**Solution**:
1. Open Google Sheets
2. File → Share → Publish to web
3. Select "Entire Document" or specific sheet
4. Format: CSV
5. Copy published URL (should start with `https://docs.google.com/spreadsheets/`)

### Issue: Album Tiles Not Displaying

**Check**:
1. Database has albums: `python manage.py shell` → `Album.objects.count()`
2. View returns data: Add `print(albums.count())` in view
3. Template receives context: `{{ albums|length }}` in template
4. CSS loaded: Inspect element → Check for Tailwind classes

### Issue: HTMX Filters Not Working

**Check**:
1. HTMX script loaded: View page source → Search for `htmx.org`
2. Network requests: DevTools → XHR tab → See filter requests
3. `HX-Request` header present: Check request headers in DevTools
4. View returns fragment: Response should be HTML tiles only, not full page

---

## 10. Next Steps

After confirming the development environment works:

1. **Run `/speckit.tasks`**: Generate detailed task breakdown
2. **Start TDD Cycle**: Write first test (album model validation)
3. **Implement User Story 1**: Browse album catalog (P1 priority)
4. **Commit Atomically**: Follow constitution's atomic commits policy
5. **Iterate**: Complete each user story independently (P1 → P2 → P3)

---

## Quick Reference

**Start Server**: `python manage.py runserver`
**Run Tests**: `pytest`
**Import Data**: `python manage.py import_albums`
**Shell**: `python manage.py shell`
**Lint**: `ruff check .`
**Format**: `ruff format .`
**Type Check**: `pyright`

**URLs**:
- Catalog: http://127.0.0.1:8000/catalog/albums/
- Admin: http://127.0.0.1:8000/admin/ (create superuser first)
- API Docs: N/A (HTMX endpoints, not REST API)

**Documentation**:
- Spec: `specs/001-album-catalog/spec.md`
- Plan: `specs/001-album-catalog/plan.md`
- Data Model: `specs/001-album-catalog/data-model.md`
- Contracts: `specs/001-album-catalog/contracts/htmx-endpoints.md`
