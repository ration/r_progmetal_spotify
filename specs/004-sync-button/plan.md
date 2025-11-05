# Implementation Plan: Synchronization Button with Status Display

**Branch**: `004-sync-button` | **Date**: 2025-11-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/lahtela/git/progmetal/specs/004-sync-button/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a user-facing synchronization button with real-time status updates. Users can trigger on-demand album catalog synchronization from Google Sheets and Spotify via a visible "Sync Now" button on the album catalog page. During synchronization, the system displays real-time progress updates (stage, albums processed, total count), handles errors gracefully with clear messages, and shows a "Last synced" timestamp. The feature builds on the existing `import_albums` management command and `SyncRecord` model, adding a web UI trigger via HTMX partial updates and server-sent events or polling for live status.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx, psycopg (PostgreSQL adapter)
**Storage**: PostgreSQL (production/Docker), SQLite (local development/tests)
**Testing**: pytest (Django tests)
**Target Platform**: Linux server (development), Docker containers (production)
**Project Type**: Web application (Django monolith with HTMX)
**Real-Time Updates**: HTTP polling with HTMX (2-second interval, `hx-trigger="every 2s"`)
**Background Execution**: Python threading (daemon threads for sync operations)
**Concurrency Control**: Database row locks via `select_for_update(nowait=True)`
**Performance Goals**: <1s sync trigger response, status updates every 2s during sync, <5min full sync for 50 albums
**Constraints**: Sync button disabled during active sync (prevent concurrent operations), persist sync status across page refreshes, graceful error recovery
**Scale/Scope**: 1 sync button on catalog page, 1 status display component, 1 background task/view for sync execution, support for 100+ albums per sync

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated before planning (spec.md validated with checklist, no clarifications remaining)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright), linting (ruff), and docstrings (Django views, forms, services)
- [x] **User-Centric Design**: Implementation organized by prioritized user stories (P1: Trigger Sync, P2: View Progress, P2: Handle Errors, P3: Last Sync Timestamp)
- [x] **Test Independence**: Test requirements explicitly defined in spec (12 functional requirements, 19 acceptance scenarios across 4 user stories)
- [x] **Incremental Delivery**: Tasks structured to deliver each user story independently (P1 basic sync works without progress display, P2 adds progress, P3 adds timestamp)

**Violations**: None

## Project Structure

### Documentation (this feature)

```text
specs/004-sync-button/
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
├── models.py                      # SyncRecord model (existing), add SyncOperation model (new)
├── views.py                       # AlbumListView (existing), add SyncTriggerView, SyncStatusView (new)
├── urls.py                        # Add sync trigger and status endpoints (new)
├── services/
│   ├── album_importer.py          # Existing sync logic (modify for progress callbacks)
│   └── sync_manager.py            # Sync orchestration and status tracking (new)
├── templates/catalog/
│   ├── album_list.html            # Main catalog page (modify to include sync button)
│   └── components/
│       ├── sync_button.html       # Sync button component (new)
│       ├── sync_status.html       # Status display component (new)
│       └── album_tile.html        # Album display (existing)
├── templatetags/                  # Custom template tags (existing)
│   └── catalog_extras.py          # Add timestamp formatting filter (modify)
└── management/commands/           # Existing import commands
    └── import_albums.py           # Existing (may need progress callback hooks)

tests/                             # Test suite (existing structure)
├── test_sync_trigger.py           # Sync button and trigger tests (new)
├── test_sync_status.py            # Status display tests (new)
├── test_sync_integration.py       # End-to-end sync workflow tests (new)
└── integration/                   # Existing integration tests directory
    └── test_album_views.py        # Existing (may add sync-related tests)

config/                            # Django project settings (existing)
└── urls.py                        # URL routing (existing)
```

**Structure Decision**: Django monolith web application. All functionality lives within the existing `catalog/` app. New components:
- `SyncOperation` model to track individual sync operations with status and progress
- Views for sync trigger (POST endpoint) and status polling/SSE (GET endpoint)
- Service layer (`sync_manager.py`) to orchestrate sync operations and emit progress events
- Template components for sync button and status display
- HTMX integration for button state and status updates without page reloads
- Test files organized by feature (trigger, status, integration)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | No violations | All design decisions align with constitution principles |

---

## Constitution Check (Post-Design Re-Evaluation)

*Re-checked after Phase 1 design and contracts completed.*

**Design Review**:

- [x] **Specification-Driven**: Design artifacts (data-model.md, contracts/) derived directly from spec requirements
- [x] **Type Safety & Code Quality**: Data model includes full type annotations; research.md documents patterns for type-safe Django models and views
- [x] **User-Centric Design**: Design organized by user story priority (P1: basic sync, P2: progress/errors, P3: timestamp)
- [x] **Test Independence**: Contracts define testable acceptance criteria for each user story; data model includes validation test cases
- [x] **Incremental Delivery**: Design supports independent deployment of each user story (P1 works without P2/P3)

**Post-Design Violations**: None

**Design Simplicity**:
- Chose HTTP polling over SSE/WebSockets (simpler, no new dependencies)
- Chose threading over Celery for MVP (simpler, sufficient for scale, easy migration later)
- Chose database locks over cache/file locks (integrated with data model, atomic)
- No new external dependencies required (all built-in or already in project)

**Constitution Check Status**: ✅ PASS - Design maintains alignment with all constitution principles
