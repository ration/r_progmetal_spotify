# Implementation Plan: Enhanced Catalog Filtering and Pagination

**Branch**: `003-catalog-filtering` | **Date**: 2025-11-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/lahtela/git/progmetal/specs/003-catalog-filtering/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement enhanced catalog browsing with three core capabilities: (1) pagination to display albums in manageable pages (50 items default, configurable to 25/50/100), (2) free-text search across album name, artist name, genre, and vocal style with 500ms debounce and 3-character minimum, and (3) multi-select checkbox filters grouped by category (Genre, Vocal Style) with OR logic within categories and AND logic between categories. All features integrate with existing HTMX-based catalog using Django Paginator, Q objects for search/filter queries, and URL parameter persistence for bookmarkable state.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx, psycopg (PostgreSQL adapter)
**Storage**: PostgreSQL (production/Docker), SQLite (local development/tests)
**Testing**: pytest (Django tests)
**Target Platform**: Linux server (development), Docker containers (production)
**Project Type**: Web application (Django monolith with HTMX)
**Performance Goals**: <1s page navigation, <500ms search/filter updates, <2s page load with 1000+ albums
**Constraints**: 500ms search debounce, 3-character search minimum, no full page reloads (HTMX partial updates)
**Scale/Scope**: 1000+ albums in catalog, 20+ genres, 10+ vocal styles, 50 items per page default

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated before planning (spec.md validated with checklist, all clarifications resolved)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright), linting (ruff), and docstrings (Django views, forms, template tags)
- [x] **User-Centric Design**: Implementation organized by prioritized user stories (P1: Pagination, P2: Search, P3: Filters, P4: Page Size)
- [x] **Test Independence**: Test requirements explicitly defined in spec (19 acceptance scenarios across 4 user stories, contract/integration tests)
- [x] **Incremental Delivery**: Tasks structured to deliver each user story independently (P1 pagination works without search/filters, P2 search works independently, etc.)

**Violations**: None

**Constitution Check Status**: ✅ PASS - All principles satisfied, ready for Phase 0 research

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
├── models.py                      # Album, Genre, VocalStyle models (existing)
├── views.py                       # AlbumListView (modify for pagination/search/filters)
├── forms.py                       # SearchForm, FilterForm (new)
├── templates/catalog/
│   ├── album_list.html            # Main catalog page (modify)
│   └── components/
│       ├── search_box.html        # Search input component (new)
│       ├── filters.html           # Checkbox filters (modify)
│       ├── pagination.html        # Pagination controls (new)
│       ├── page_size_selector.html # Page size selector (new)
│       └── album_tile.html        # Album display (existing)
├── templatetags/                  # Custom template tags (new)
│   └── catalog_extras.py          # Filters for URL parameter handling
└── management/commands/           # Existing import commands

tests/                             # Test suite (existing structure)
├── test_pagination.py             # Pagination tests (new)
├── test_search.py                 # Search tests (new)
├── test_filters.py                # Filter tests (new)
└── test_integration.py            # End-to-end user journey tests (new)

config/                            # Django project settings (existing)
└── urls.py                        # URL routing (existing)
```

**Structure Decision**: Django monolith web application. All functionality lives within the existing `catalog/` app. New components:
- Forms for search and filter inputs
- Template components for UI elements
- Template tags for URL parameter management
- View modifications to AlbumListView for queryset filtering
- Test files organized by feature (pagination, search, filters)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
