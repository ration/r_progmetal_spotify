# Implementation Plan: Just-in-Time Spotify API Usage

**Branch**: `006-jit-spotify-api` | **Date**: 2025-11-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-jit-spotify-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature optimizes Spotify API usage by implementing a just-in-time loading strategy. During album import from Google Sheets, the system will store only basic metadata and Spotify URLs without making API calls. Cover art and detailed metadata will be fetched on-demand when albums are displayed in the UI or when users view album detail pages. This approach reduces import time by 50%+, eliminates Spotify API dependency during import, and reduces total API calls by 80%+ through caching and progressive loading.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx, spotipy (Spotify API client), psycopg (PostgreSQL adapter)
**Storage**: PostgreSQL (production/Docker), SQLite (local development/tests)
**Testing**: pytest with Django test framework
**Target Platform**: Linux server (Docker containers), web browser frontend
**Project Type**: Web application (Django backend + HTMX frontend)
**Performance Goals**: Cover art loads within 1 second of viewport visibility, album imports complete 50%+ faster than current eager-loading approach
**Constraints**: Spotify API rate limits (~180 requests per 30 seconds), must not degrade user experience during API delays, cache storage must be efficient
**Scale/Scope**: Catalog with 500+ albums, expected 10-50 concurrent users browsing catalog, progressive loading for viewport-visible albums only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated (specs/006-jit-spotify-api/spec.md, validated via requirements.md checklist)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright strict mode), linting (ruff), formatting (ruff format), and docstrings for all functions/classes
- [x] **User-Centric Design**: Implementation organized by 3 prioritized user stories (P1: browsing with cover art, P2: import without Spotify, P3: detail page metadata)
- [x] **Test Independence**: Test requirements defined - contract tests for API endpoints, integration tests for cover art loading and caching, unit tests for Spotify URL extraction and error handling
- [x] **Incremental Delivery**: Tasks will be structured to deliver P1 (cover art on catalog), then P2 (import optimization), then P3 (detail page metadata) - each independently deployable

**Violations**: None

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
catalog/                           # Django app (existing)
├── models.py                      # Album, Artist, Genre, VocalStyle models (modify for caching)
├── services/
│   ├── spotify_client.py          # Spotify API wrapper (modify for on-demand fetching)
│   ├── google_sheets.py           # Google Sheets import (existing)
│   └── album_cache.py             # NEW: Cache management service
├── views.py                       # Album catalog views (modify for lazy loading)
├── urls.py                        # URL routing (add new endpoints)
├── templates/catalog/
│   ├── album_list.html            # Catalog page (modify for progressive loading)
│   ├── album_detail.html          # Detail page (modify for on-demand metadata)
│   └── components/
│       └── album_tile.html        # Album tile component (modify for lazy cover art)
└── management/commands/
    ├── import_albums.py           # Import command (modify to skip Spotify)
    └── refresh_spotify_cache.py   # NEW: Manual cache refresh command

config/                            # Django project settings
└── settings.py                    # Add cache configuration

tests/
├── contract/
│   └── test_spotify_endpoints.py  # NEW: Contract tests for cover art API
├── integration/
│   ├── test_album_import.py       # Test import without Spotify
│   └── test_lazy_loading.py      # NEW: Test progressive cover art loading
└── unit/
    ├── test_spotify_client.py     # Test URL extraction and error handling
    └── test_album_cache.py        # NEW: Test cache service
```

**Structure Decision**: Django web application structure. The existing `catalog/` app will be modified to implement just-in-time loading. Key additions include a new cache management service (`album_cache.py`), a cache refresh management command, and new tests for lazy loading behavior. The frontend uses Django templates with HTMX for progressive loading without a separate frontend codebase.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - table not needed.

---

## Constitution Check (Post-Design Re-evaluation)

*Re-checked after Phase 1 design completion*

- [x] **Specification-Driven**: Design artifacts (data-model.md, contracts/, quickstart.md) derived directly from validated spec
- [x] **Type Safety & Code Quality**: All new code will follow pyright strict mode, ruff linting, and comprehensive docstrings (documented in quickstart.md)
- [x] **User-Centric Design**: Design artifacts organized by user stories (P1: cover art loading, P2: import optimization, P3: detail metadata)
- [x] **Test Independence**: Contract tests (endpoints.md), integration tests (lazy loading), and unit tests (cache service) explicitly defined
- [x] **Incremental Delivery**: Design supports independent delivery of P1 (catalog cover art), P2 (import changes), P3 (detail page metadata)

**Violations**: None

**Design Review Notes**:
- Data model uses simple nullable fields (no complex schemas)
- API contracts follow REST conventions with HTMX integration
- Caching strategy uses existing Django ORM (no external dependencies)
- All design decisions documented in research.md with rationale
