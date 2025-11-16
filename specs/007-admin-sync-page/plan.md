# Implementation Plan: Admin Sync Page

**Branch**: `007-admin-sync-page` | **Date**: 2025-11-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-admin-sync-page/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a dedicated admin page that houses the album synchronization controls (sync button, status display, and timestamp) currently embedded in the main catalog listing page. This refactoring separates administrative functionality from user-facing catalog browsing, improving the UI organization and page performance. The implementation will reuse existing sync components and HTMX polling mechanisms, simply relocating them to a new URL route with appropriate navigation.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-htmx 1.16.0, Tailwind CSS v4 (CDN), DaisyUI v5
**Storage**: PostgreSQL (production/Docker), SQLite (development/tests)
**Testing**: pytest with pytest-django, pyright for type checking, ruff for linting
**Target Platform**: Web application (Linux server, Docker containers)
**Project Type**: Web application (Django monolith with catalog app)
**Performance Goals**: Page load <2 seconds, HTMX status updates <2 seconds, no user-facing performance regression
**Constraints**: Must maintain all existing sync functionality, preserve HTMX polling behavior, zero breaking changes to current sync operations
**Scale/Scope**: Small-scale refactoring - 1 new view, 1 new template, 2 URL routes, removal of 3 template includes from existing page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated before planning (spec.md passed all quality checks)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright), linting (ruff), and docstrings following existing codebase standards
- [x] **User-Centric Design**: Implementation organized by prioritized user stories (P1: Access admin page, P1: Trigger sync, P1: Monitor status, P2: View timestamp)
- [x] **Test Independence**: Tests not explicitly requested in spec - this is a UI refactoring with no business logic changes. Existing sync functionality remains tested via existing test suite.
- [x] **Incremental Delivery**: Tasks structured to deliver each user story independently - admin page can be created first, then sync button moved, then status, then timestamp

**Violations**: None

All constitution principles are satisfied. This is a straightforward UI refactoring that maintains existing functionality while improving separation of concerns.

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

This is a Django web application with the following structure relevant to this feature:

```text
catalog/                                    # Django app for album catalog
├── views.py                                # MODIFIED: Add admin_sync_page view
├── urls.py                                 # MODIFIED: Add admin/sync route
├── templates/
│   └── catalog/
│       ├── album_list.html                 # MODIFIED: Remove sync components
│       ├── admin_sync.html                 # NEW: Admin sync page template
│       ├── base.html                       # MODIFIED: Add admin nav link
│       └── components/
│           ├── sync_button.html            # UNCHANGED: Reused on admin page
│           ├── sync_status.html            # UNCHANGED: Reused on admin page
│           └── [other components]
├── models.py                               # UNCHANGED: No data model changes
└── services/
    └── sync_manager.py                     # UNCHANGED: No sync logic changes

tests/
├── integration/                            # Optional: Manual testing documented
└── unit/                                   # Optional: No new business logic to test
```

**Structure Decision**: Django web application structure (Option 2). This feature only modifies the catalog app's views, URLs, and templates. No new models, services, or business logic required - purely a UI reorganization.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitution violations to track.

---

## Phase 0: Research & Technical Decisions

**Status**: ✅ Complete

**Output**: `research.md`

**Summary**: Resolved all technical decisions for implementing the admin sync page:

1. **URL Structure**: `/catalog/admin/sync` - maintains namespace consistency
2. **Template Reuse**: Use `{% include %}` for existing sync components
3. **View Pattern**: Function-based view (consistent with existing sync views)
4. **Navigation**: Simple link in base template
5. **HTMX Polling**: No changes needed - existing config is portable
6. **Type Safety**: Follow existing django-stubs patterns
7. **Timestamp Display**: Reuse JavaScript timeago function

**Key Finding**: This is a low-risk refactoring with no new dependencies or complex technical challenges. All implementation patterns already exist in the codebase.

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete

**Outputs**:
- `data-model.md` - No data model changes required
- `contracts/http-endpoints.md` - HTTP endpoint contracts
- `quickstart.md` - Implementation guide

**Summary**:

### Data Model (`data-model.md`)
- **Changes**: NONE
- **Existing Models Used**: `SyncRecord` (read-only for timestamp), `SyncOperation` (read via existing views)
- **Rationale**: Pure UI refactoring, all data structures already exist

### API Contracts (`contracts/http-endpoints.md`)
- **New Endpoint**: `GET /catalog/admin/sync` (admin_sync_page view)
- **Modified Endpoint**: `GET /catalog/` (remove sync components)
- **Unchanged Endpoints**: All existing sync endpoints reused (`/sync/trigger/`, `/sync/status/`, etc.)

### Quickstart Guide (`quickstart.md`)
- Step-by-step implementation instructions
- Testing checklist (8 test scenarios)
- Common issues and solutions
- Rollback procedure
- Performance validation criteria

**Agent Context**: Updated `CLAUDE.md` with feature technologies

---

## Constitution Check - Post Design

**Re-evaluation after Phase 1 design complete**:

- [x] **Specification-Driven**: Design follows validated spec, no deviations ✓
- [x] **Type Safety & Code Quality**: New view will use type annotations, docstrings per existing patterns ✓
- [x] **User-Centric Design**: Design maintains user story priorities (P1 stories independently deliverable) ✓
- [x] **Test Independence**: No new tests required (UI refactoring only), existing sync tests cover functionality ✓
- [x] **Incremental Delivery**: Design supports incremental delivery - each component can be moved independently ✓

**Violations**: None

**Design Validation**: All constitution principles remain satisfied after detailed design phase. The implementation approach is simple, follows existing patterns, and introduces no new complexity.

---

## Next Steps

This planning phase is complete. The next step is to generate tasks:

```bash
/speckit.tasks
```

This will create `tasks.md` with a detailed, ordered list of implementation tasks organized by user story priority.
