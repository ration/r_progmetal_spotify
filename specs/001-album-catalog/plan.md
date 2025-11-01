# Implementation Plan: Album Catalog Visualization

**Branch**: `001-album-catalog` | **Date**: 2025-11-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-album-catalog/spec.md`

## Summary

Build a Django web application that displays newly released progressive metal albums in a tile-based grid interface. Users can browse albums, view detailed information, and filter by genre and vocal style. Album data is sourced from a Google Sheets document containing Spotify links, with album metadata (cover art, artist details) fetched from the Spotify API. The frontend uses HTMX for dynamic interactions without full page reloads, providing a responsive browsing experience.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx 1.16.0, psycopg 3.2.10, spotipy (Spotify API client)
**Storage**: PostgreSQL (production), SQLite (development/testing)
**Testing**: pytest with pytest-django
**Target Platform**: Web browser (desktop, tablet, mobile)
**Project Type**: Web application (Django monolith with HTMX-enhanced templates)
**Performance Goals**: <5 second initial page load, <1 second filter response, support 100+ albums
**Constraints**: Spotify API rate limits (Web API: ~180 requests/30 seconds), Google Sheets CSV must be publicly accessible
**Scale/Scope**: Single-user browsing application, ~100-500 album catalog, no user accounts required

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity First ✅ PASS

- **Using Django's built-in features**: Django ORM for models, Django template system with HTMX, Django views (no REST framework needed)
- **No unnecessary abstractions**: Direct model-view-template pattern, no repository pattern, no service layer complexity beyond simple data import
- **Justified dependencies**:
  - django-htmx: Required for interactive filtering without JavaScript frameworks (aligns with simplicity)
  - spotipy: Industry-standard Spotify API client (avoids reinventing OAuth/API handling)
  - PostgreSQL: Required for production (specified by user), but SQLite for dev (Django default)

### Principle II: Test-Driven Development (TDD) ✅ PASS

- **Test types required**:
  - Unit tests: Album model validation, data import parsing
  - Integration tests: View rendering, HTMX fragment responses, filter logic
  - Contract tests: Spotify API mocking, Google Sheets CSV parsing
- **Test-first workflow**: All tests written before implementation
- **Tools**: pytest with pytest-django, Django test client for HTMX requests

### Principle III: Data Integrity & Validation ✅ PASS

- **Validation layers planned**:
  1. Django model field validation (CharField max_length, DateField format)
  2. CSV import validation (required fields, data type checks)
  3. Spotify API response validation (handle missing/malformed data)
  4. Database constraints (NOT NULL on critical fields, UNIQUE on Spotify IDs)
- **Error handling**: Graceful fallbacks for missing cover art, invalid dates, API failures

### Principle IV: Observability ✅ PASS

- **Logging requirements**:
  - Spotify API calls (request/response/timing)
  - Google Sheets CSV fetch operations
  - Data import success/failure counts
  - HTMX request handling for debugging
- **Development tools**: Django Debug Toolbar enabled in development

### Principle V: Documentation Standards ✅ PASS

- **Documentation planned**:
  - Docstrings for all models, views, data import functions
  - README updates for Spotify API setup and Google Sheets configuration
  - CLAUDE.md updates with Spotify API integration details
  - Inline comments for CSV parsing logic and API error handling

**Constitution Compliance**: ALL GATES PASS - No complexity violations

## Project Structure

### Documentation (this feature)

```text
specs/001-album-catalog/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Development setup
├── contracts/           # Phase 1: HTMX endpoint specs
└── tasks.md             # Phase 2: Task breakdown (created by /speckit.tasks)
```

### Source Code (repository root)

```text
catalog/                     # Existing Django app (reuse)
├── models.py               # Album, Artist, Genre, VocalStyle models
├── views.py                # Album list, detail, filter views
├── urls.py                 # URL routing
├── templates/
│   ├── catalog/
│   │   ├── album_list.html      # Main catalog page
│   │   ├── album_list_tiles.html # HTMX fragment for tiles
│   │   ├── album_detail.html    # Album detail view
│   │   └── components/
│   │       ├── album_tile.html  # Reusable tile component
│   │       └── filters.html     # Genre/vocal style filters
├── static/
│   └── catalog/
│       ├── css/
│       │   └── album-catalog.css  # Tile layout, responsive grid
│       └── images/
│           └── placeholder-album.png  # Fallback for missing covers
├── management/
│   └── commands/
│       ├── import_albums.py     # Django command for CSV import
│       └── sync_spotify.py      # Fetch Spotify API data
└── services/
    ├── google_sheets.py         # Fetch CSV from Google Sheets
    ├── spotify_client.py        # Spotify API integration
    └── album_importer.py        # Import/sync orchestration

tests/
├── unit/
│   ├── test_models.py           # Album model validation
│   ├── test_spotify_client.py   # API client mocking
│   └── test_album_importer.py   # Import logic
├── integration/
│   ├── test_views.py            # View rendering + HTMX
│   └── test_filters.py          # Filter functionality
└── contract/
    ├── test_google_sheets.py    # CSV format validation
    └── test_spotify_api.py      # API response handling

config/
├── settings.py                  # Add SPOTIFY_* settings
└── urls.py                      # Already routes to catalog/

requirements added to pyproject.toml:
- spotipy ~= 2.24.0
```

**Structure Decision**: Reuse existing Django structure with catalog/ app. This is a standard Django monolith with HTMX enhancements - no backend/frontend split needed. All code lives in the catalog/ app following Django conventions (models, views, templates, management commands). Static files for CSS and a placeholder image. Services subdirectory for data fetching logic (Google Sheets, Spotify API) keeps concerns separated without over-engineering.

## Complexity Tracking

> No violations - this section is empty per constitution requirements.

