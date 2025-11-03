# Implementation Plan: Catalog Statistics

**Branch**: `002-catalog-statistics` | **Date**: 2025-11-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-catalog-statistics/spec.md`

**Note**: This plan implements catalog statistics display showing last sync time, total albums, and recent additions.

## Summary

Display catalog synchronization statistics on the main catalog page to inform users about data freshness and collection size. This requires:

1. **Persistent sync tracking**: Add SyncRecord model to store synchronization metadata (timestamp, albums created/updated, success status)
2. **Command enhancement**: Modify import_albums management command to create SyncRecord after each sync
3. **UI integration**: Update catalog page template to display statistics with human-readable formatting
4. **Template utilities**: Add template filters for relative time ("2 hours ago") and number formatting (thousands separators)

**Technical Approach**: Extend existing Django catalog app with new model and template enhancements, integrating seamlessly with current HTMX-based filtering.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx, psycopg (PostgreSQL adapter)
**Storage**: PostgreSQL (production/Docker), SQLite (local development/tests)
**Testing**: pytest with Django plugin
**Target Platform**: Linux server (Docker) or local development environment
**Project Type**: Web application (Django monolith)
**Performance Goals**: Statistics query < 50ms, page load < 2 seconds including statistics
**Constraints**: No additional external APIs, must work with existing HTMX patterns, statistics visible on full page and HTMX partial updates
**Scale/Scope**: 10,000+ albums in catalog, single page enhancement (catalog index)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated at specs/002-catalog-statistics/spec.md (all checklist items passed)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright strict mode), ruff linting, docstrings for all new classes/functions
- [x] **User-Centric Design**: Implementation organized by 3 prioritized user stories (P1: View Freshness, P2: View Total, P3: See Growth)
- [x] **Test Independence**: Test requirements N/A - spec does not request explicit tests (simple display feature, manual testing sufficient)
- [x] **Incremental Delivery**: Tasks will be structured to deliver P1 (last sync time) first, then P2 (total count), then P3 (recent additions)

**Violations**: None

## Project Structure

### Documentation (this feature)

```text
specs/002-catalog-statistics/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: SyncRecord model design
├── quickstart.md        # Phase 1: Manual testing guide
└── tasks.md             # Phase 2: Implementation tasks (created by /speckit.tasks)
```

### Source Code (repository root)

This is a Django web application with a single `catalog` app:

```text
catalog/                           # Main Django app
├── models.py                      # Models: Album, Artist, Genre, VocalStyle, SyncRecord (NEW)
├── views.py                       # Views: AlbumListView (will be enhanced)
├── urls.py                        # URL routing
├── admin.py                       # Django admin registration
├── templatetags/                  # Custom template tags/filters
│   ├── __init__.py
│   └── catalog_extras.py          # NEW: relative_time, format_number filters
├── management/commands/
│   └── import_albums.py           # MODIFY: Create SyncRecord after sync
├── services/
│   ├── album_importer.py          # MODIFY: Return sync metadata
│   ├── spotify_client.py          # No changes needed
│   └── google_sheets.py           # No changes needed
├── templates/catalog/
│   ├── album_list.html            # MODIFY: Add statistics display
│   ├── album_list_tiles.html      # No changes (HTMX partial)
│   └── components/
│       └── stats_panel.html       # NEW: Statistics display component
└── migrations/
    └── 0003_syncrecord.py         # NEW: Add SyncRecord model

tests/
├── test_models.py                 # Tests for Album, Artist, etc.
└── test_sync_record.py            # NEW: Tests for SyncRecord model (optional)

config/                            # Django project settings
├── settings.py
└── urls.py
```

**Structure Decision**: Django monolith with single `catalog` app. All changes confined to catalog app (models, views, templates, management commands). No new apps needed - SyncRecord naturally belongs in catalog app alongside Album model.

## Complexity Tracking

No constitution violations - this section is not applicable.

## Phase 0 & 1: Completed Artifacts

### Phase 0: Research (Complete)

**File**: `research.md`

**Key Findings**:
- Existing sync system returns counts but doesn't persist them
- Need new SyncRecord model to track sync metadata
- Django's `humanize` app provides time/number formatting filters
- Simple two-query approach for statistics (latest sync + album count)
- No performance concerns (<10ms overhead)

### Phase 1: Design (Complete)

**Files Generated**:
1. `data-model.md` - SyncRecord model specification with full type annotations
2. `quickstart.md` - Manual testing guide with 10 test scenarios

**Key Design Decisions**:
- SyncRecord model with 7 fields (timestamp, counts, status, error)
- Indexed query optimization (`-sync_timestamp` for O(1) latest lookup)
- Django humanize filters for time/number formatting (no custom code)
- Statistics panel above filters in album_list.html
- Component-based template (`components/stats_panel.html`)

**Constitution Re-check**: ✅ All principles still satisfied after design phase

### Phase 2: Next Steps

Run `/speckit.tasks` to generate implementation tasks organized by user story:
- Phase 1: Setup (migration, dependencies)
- Phase 2: Foundational (model, admin registration)
- Phase 3: User Story 1 - View Catalog Freshness (P1)
- Phase 4: User Story 2 - View Total Catalog Size (P2)
- Phase 5: User Story 3 - See Recent Growth (P3)
- Phase 6: Polish (testing, documentation)

**Branch**: `002-catalog-statistics` (already checked out)

**Ready for Implementation**: ✅ Yes - all research and design artifacts complete
