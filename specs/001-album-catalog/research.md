# Research: Album Catalog Implementation Decisions

**Feature**: Album Catalog Visualization
**Date**: 2025-11-01
**Purpose**: Document technology choices and architectural decisions

## Architecture Overview

### Decision: Django Monolith with HTMX

**Chosen Approach**: Single Django application with HTMX-enhanced templates

**Rationale**:
- Aligns with Constitution Principle I (Simplicity First) - no unnecessary frontend/backend split
- HTMX provides interactivity without JavaScript framework complexity
- Django's template system + HTMX = progressive enhancement pattern
- Existing project structure already uses Django + django-htmx

**Alternatives Considered**:
- **Django REST Framework + React**: Rejected - over-engineering for simple CRUD + filtering
- **Full page reloads**: Rejected - poor UX for filtering (loses scroll position, flicker)
- **Vanilla JavaScript**: Rejected - HTMX declarative approach is simpler and more maintainable

**Implementation Notes**:
- HTMX attributes in templates (`hx-get`, `hx-target`, `hx-swap`)
- Partial template rendering for album tiles (HTMX fragments)
- Django views return full HTML or fragments based on `HX-Request` header

---

## Data Source Integration

### Decision: Google Sheets CSV + Spotify API

**Chosen Approach**:
1. Google Sheets CSV export URL provides Spotify album links
2. Spotify Web API fetches album metadata (cover art, artist, genres)
3. Local PostgreSQL database caches enriched data

**Rationale**:
- Google Sheets is the existing data source (user requirement)
- Spotify API is authoritative source for album metadata and cover art
- Local caching reduces API calls and improves performance
- Separation of concerns: CSV = album list, Spotify = rich metadata

**Alternatives Considered**:
- **Store all data in Google Sheets**: Rejected - no API for cover art URLs, manual data entry error-prone
- **Scrape Spotify web pages**: Rejected - against TOS, fragile, no official cover art access
- **Use different music API (Last.fm, MusicBrainz)**: Rejected - Spotify has best cover art quality and is already referenced in sheets

**CSV Expected Format**:
```csv
Release Date,Artist,Album,Spotify URL,Genre,Country,Vocal Style
2025-01-15,Haken,Fauna,https://open.spotify.com/album/abc123,Progressive Metal,UK,Clean
```

**Spotify API Integration**:
- Use `spotipy` library (official Python client)
- OAuth Client Credentials flow (no user auth needed)
- Extract from Spotify API response:
  - Album cover art (images[0].url - highest resolution)
  - Artist name (artists[0].name)
  - Release date (release_date)
  - Genres (genres array from artist endpoint - album endpoint doesn't have genres)

**API Rate Limiting**:
- Spotify Web API: ~180 requests per 30 seconds
- Mitigation: Batch imports, cache in database, sync command runs periodically (not on every page load)

---

## Database Schema Design

### Decision: Normalized Models with Django ORM

**Chosen Approach**: Separate models for Album, Artist, Genre, VocalStyle with foreign keys

**Rationale**:
- Supports efficient filtering (JOIN queries faster than string matching)
- Data integrity via foreign keys and constraints
- Follows Django best practices (fat models, thin views)
- Enables future features (artist pages, genre analytics)

**Alternatives Considered**:
- **Denormalized (all data in Album model)**: Rejected - poor query performance for filters, data duplication
- **NoSQL (MongoDB)**: Rejected - project uses PostgreSQL, relational data fits SQL model

**Key Design Decisions**:
- `spotify_album_id`: Unique identifier, prevents duplicate imports
- `cover_art_url`: Store Spotify CDN URL (external hosting, no local storage needed)
- `release_date`: DateField (handles partial dates like "2025" or "2025-01")
- `Artist`: Separate model (many albums can share same artist)
- `Genre`/`VocalStyle`: Separate models (enables dropdown population, data consistency)

**Database Constraints**:
- Album.spotify_album_id: UNIQUE, NOT NULL
- Album.name: NOT NULL, max 500 chars (Spotify limit)
- Album.release_date: NULL allowed (some albums have incomplete data)
- Foreign keys: CASCADE delete (if artist deleted, remove albums)

---

## HTMX Interaction Patterns

### Decision: Partial HTML Replacement for Filters

**Chosen Approach**:
- Filter changes trigger HTMX requests to backend
- Backend returns HTML fragment (just the tiles, not full page)
- HTMX swaps content in `#album-tiles` container

**Rationale**:
- Faster than full page reload (less data transfer, no CSS/JS re-download)
- Maintains scroll position and UI state
- Server-side rendering = SEO-friendly, no client-side hydration complexity
- Progressive enhancement: works with JavaScript disabled (falls back to full page reload)

**HTMX Endpoints**:
1. `GET /catalog/albums/` - Full page (initial load)
2. `GET /catalog/albums/?genre=prog-metal` - HTMX fragment (filtered tiles)
3. `GET /catalog/albums/<id>/` - Album detail view

**Template Structure**:
```
album_list.html (full page)
├── filters.html (genre/vocal style dropdowns)
└── album_list_tiles.html (HTMX swap target)
    └── album_tile.html × N (individual tiles)
```

**HTMX Attributes**:
- `hx-get="/catalog/albums/?genre={{genre}}"` - Trigger filter request
- `hx-target="#album-tiles"` - Replace tiles container
- `hx-swap="innerHTML"` - Swap strategy
- `hx-push-url="true"` - Update browser URL (back button support)

---

## Styling & Responsive Design

### Decision: CSS Grid with Tailwind/DaisyUI

**Chosen Approach**: Use existing Tailwind CSS + DaisyUI for tile layout

**Rationale**:
- Project already uses Tailwind + DaisyUI (base.html references CDN)
- CSS Grid ideal for tile layouts (auto-fit, responsive columns)
- DaisyUI provides pre-styled components (cards, buttons, dropdowns)
- No additional dependencies needed

**Grid Breakpoints**:
- Mobile (< 768px): 1-2 columns
- Tablet (768-1024px): 2-3 columns
- Desktop (> 1024px): 3-4 columns

**Tile Design**:
- Album cover: Square aspect ratio (Spotify provides square images)
- Overlay text on hover: Artist, album name, release date
- Click entire tile to navigate to detail view
- Placeholder image for missing covers (static file)

---

## Data Import Strategy

### Decision: Django Management Command + Periodic Sync

**Chosen Approach**:
1. `python manage.py import_albums` - Manual import/sync command
2. Command fetches Google Sheets CSV
3. For each row, lookup or create album via Spotify API
4. Upsert into database (update existing, insert new)

**Rationale**:
- Django management commands are standard for data tasks
- Runs independently of web requests (no page load delays)
- Can be scheduled with cron/systemd timer for daily sync
- Testable in isolation (unit tests for import logic)

**Import Flow**:
1. Fetch CSV from Google Sheets export URL
2. Parse CSV rows (pandas or csv module)
3. Extract Spotify album ID from URL
4. Query Spotify API for album details
5. Query Spotify API for artist details (to get genres)
6. Create/update Album, Artist, Genre, VocalStyle records
7. Log success/failure counts

**Error Handling**:
- Invalid Spotify URL: Log warning, skip row
- Spotify API failure: Retry with exponential backoff (max 3 attempts)
- Missing required fields: Log error, skip row
- Duplicate album (same spotify_id): Update existing record

**Future Enhancement** (out of scope for MVP):
- Webhook from Google Sheets (Apps Script) to trigger sync
- Celery task for background processing
- Admin UI for manual sync trigger

---

## Testing Strategy

### Decision: TDD with pytest + Django Test Client

**Chosen Approach**: Write tests before implementation (red-green-refactor)

**Test Categories**:

1. **Unit Tests**:
   - Model validation (Album.clean(), Genre choices)
   - CSV parsing logic (handle malformed rows)
   - Spotify API client (mocked responses)
   - Date parsing utilities

2. **Integration Tests**:
   - View rendering (album_list, album_detail)
   - HTMX fragment responses (check HX-Request header)
   - Filter logic (genre/vocal style queries)
   - Template context data

3. **Contract Tests**:
   - Google Sheets CSV format (column names, data types)
   - Spotify API response structure (mock realistic JSON)
   - External URL validation (Spotify link format)

**Mocking Strategy**:
- `responses` library for HTTP mocking (Spotify API, Google Sheets CSV)
- Django TestCase for database transactions (rollback after each test)
- Factory pattern for test data (AlbumFactory, ArtistFactory)

**Test Data**:
- Fixtures: sample CSV, Spotify API JSON responses
- Stored in `tests/fixtures/` directory
- Include edge cases: missing cover art, partial dates, long names

---

## Deployment Considerations

### Decision: PostgreSQL for Production, SQLite for Development

**Chosen Approach**:
- Development: SQLite (Django default, no setup)
- Production: PostgreSQL (user requirement)

**Rationale**:
- SQLite sufficient for local dev and testing
- PostgreSQL for production (better concurrency, full-text search potential)
- Django ORM abstracts differences (same code works on both)

**Environment Configuration**:
- `.env` file for secrets (Spotify client ID/secret, DB credentials)
- `django-environ` or similar for env var loading
- Settings override: `DATABASES['default']` based on environment

**Static Files**:
- Local dev: `python manage.py collectstatic` → `static/` directory
- Production: Serve via nginx or CDN (out of scope for MVP)

**Spotify API Credentials**:
- Register app at https://developer.spotify.com/dashboard
- Client Credentials flow (no user login needed)
- Store in environment variables:
  - `SPOTIFY_CLIENT_ID`
  - `SPOTIFY_CLIENT_SECRET`

---

## Summary of Key Decisions

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| Architecture | Django Monolith + HTMX | Simplicity, existing stack, progressive enhancement |
| Data Sources | Google Sheets CSV + Spotify API | Existing data source + authoritative metadata |
| Database | PostgreSQL (prod), SQLite (dev) | User requirement, Django default |
| Frontend Interactivity | HTMX partial updates | No JS framework needed, server-side rendering |
| Styling | Tailwind CSS + DaisyUI | Already in project, CSS Grid for tiles |
| Data Import | Django management command | Standard pattern, testable, schedulable |
| Testing | pytest + Django TestClient | TDD compliance, constitution requirement |

All decisions align with Constitution Principle I (Simplicity First) - no over-engineering, use Django built-ins where possible, justify all dependencies.
