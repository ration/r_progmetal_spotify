# Tasks: Synchronization Button with Status Display

**Input**: Design documents from `/home/lahtela/git/progmetal/specs/004-sync-button/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-endpoints.md

**Tests**: No explicit TDD requirement in spec - tests are optional and not included in this task list. Focus on incremental delivery of working user stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, database migration, and verify environment

- [X] T001 Run database migrations to verify PostgreSQL/SQLite is configured
- [X] T002 Verify Spotify credentials are set (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
- [X] T003 Verify Google Sheets URL is configured (GOOGLE_SHEETS_XLSX_URL)
- [X] T004 Verify HTMX is loaded in catalog/templates/catalog/base.html

**Checkpoint**: Environment verified - ready for model creation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model and URL structure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create SyncOperation model in catalog/models.py with status, stage, stage_message, albums_processed, total_albums, started_at, completed_at, error_message, created_by_ip fields
- [X] T006 Add indexes on SyncOperation.status and SyncOperation.started_at in catalog/models.py
- [X] T007 Add SyncOperation model methods: progress_percentage(), duration(), is_active(), display_status() in catalog/models.py
- [X] T008 Generate and apply migration for SyncOperation model: python manage.py makemigrations catalog && python manage.py migrate
- [X] T009 Create catalog/services/sync_manager.py file structure with SyncManager class skeleton
- [X] T010 [P] Add sync URL routes to catalog/urls.py: path('sync/trigger/', ...), path('sync/status/', ...)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Trigger Manual Synchronization (Priority: P1) 🎯 MVP

**Goal**: Users can click a "Sync Now" button on the catalog page to trigger synchronization. Button disables during sync, creates SyncOperation record, and runs sync in background thread.

**Independent Test**: Click sync button → SyncOperation record created → sync runs in background → album data updates

### Implementation for User Story 1

- [X] T011 [US1] Implement sync_trigger view in catalog/views.py: check for active sync with select_for_update, return 409 if active, create SyncOperation, spawn thread, return 202 with HX-Trigger header
- [X] T012 [US1] Implement SyncManager.start_sync method in catalog/services/sync_manager.py: daemon thread creation, exception handling, status updates (pending → running)
- [X] T013 [US1] Implement SyncManager.run_sync method in catalog/services/sync_manager.py: call existing AlbumImporter logic, update SyncOperation status, create SyncRecord on completion
- [X] T014 [P] [US1] Create catalog/templates/catalog/components/sync_button.html: HTMX button with hx-post, hx-target, hx-disabled-elt, hx-indicator
- [X] T015 [P] [US1] Create catalog/templates/catalog/components/sync_status.html: status display div with id="sync-status"
- [X] T016 [US1] Modify catalog/templates/catalog/album_list.html: include sync_button.html and sync_status.html components near page header
- [X] T017 [US1] Add CSRF token validation to sync_trigger view in catalog/views.py
- [X] T018 [US1] Add error handling for missing Spotify credentials in sync_trigger view: return 503 with error alert HTML
- [X] T019 [US1] Add concurrency prevention logic in sync_trigger view: database lock with select_for_update(nowait=True)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can trigger sync via button, sync runs in background, button disables during operation

---

## Phase 4: User Story 2 - View Synchronization Progress (Priority: P2)

**Goal**: While sync runs, user sees real-time status updates every 2 seconds showing stage, album count progress, and percentage complete.

**Independent Test**: Trigger sync → observe status polling every 2s → see "Fetching...", "Syncing album X of Y", "Complete!" messages

### Implementation for User Story 2

- [X] T020 [US2] Implement sync_status view in catalog/views.py: query for active SyncOperation, render sync_status.html template, return stopPolling header when complete
- [X] T021 [US2] Modify catalog/templates/catalog/components/sync_status.html: add hx-get="/catalog/sync/status/", hx-trigger="syncStarted from:body, every 2s", hx-swap="innerHTML"
- [X] T022 [US2] Add progress display to sync_status.html template: spinner, stage_message, progress bar with percentage, album count (X of Y)
- [X] T023 [US2] Add success state HTML to sync_status.html: alert-success with "Sync Complete!" message, album count, duration
- [X] T024 [US2] Add HX-Trigger response headers in sync_status view: "stopPolling" when status is completed/failed, "syncCompleted" on success
- [X] T025 [US2] Implement progress callbacks in SyncManager.run_sync: update albums_processed, total_albums, stage_message every 5 albums
- [X] T026 [US2] Add stage transitions in SyncManager.run_sync: set stage to 'fetching' (Google Sheets), 'processing' (albums), 'finalizing' (completion)
- [X] T027 [US2] Optimize database writes in SyncManager: use save(update_fields=[...]) to minimize lock contention

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - sync triggers correctly AND shows real-time progress updates

---

## Phase 5: User Story 3 - Handle Synchronization Errors (Priority: P2)

**Goal**: System displays clear error messages for failures (missing credentials, network errors, partial failures) and button re-enables for retry.

**Independent Test**: Simulate errors (unset credentials, network failure, partial sync) → verify error messages are clear and actionable, button re-enables

### Implementation for User Story 3

- [X] T028 [US3] Add error state HTML to sync_status.html: alert-error with error title and detailed message from SyncOperation.error_message
- [X] T029 [US3] Add partial success (warning) state to sync_status.html: alert-warning showing "X of Y succeeded, Z failed"
- [X] T030 [US3] Implement error handling in SyncManager.run_sync: wrap sync logic in try/except, set status='failed', store error_message, log exception
- [X] T031 [US3] Add network error detection in SyncManager: catch connection errors, format user-friendly message "Unable to reach external services..."
- [X] T032 [US3] Add missing credentials error in sync_trigger view: check for SPOTIFY_CLIENT_ID/SECRET before creating SyncOperation, return 503 if missing
- [X] T033 [US3] Implement partial failure tracking in SyncManager: count failed albums, include in SyncOperation result, display warning if some albums failed
- [X] T034 [US3] Add Google Sheets error handling in SyncManager: catch invalid URL/data errors, display "Google Sheets configuration error" message
- [X] T035 [US3] Ensure sync_status view returns stopPolling header for failed syncs so button re-enables

**Checkpoint**: All error scenarios now handled gracefully - missing creds, network failures, partial syncs all display clear messages and allow retry

---

## Phase 6: User Story 4 - View Last Synchronization Timestamp (Priority: P3)

**Goal**: Users see "Last synced: X ago" timestamp on page load that auto-updates every minute via JavaScript.

**Independent Test**: Complete a sync → refresh page → see "Last synced: just now" → wait 1 minute → see "1 minute ago"

### Implementation for User Story 4

- [X] T036 [US4] Query last successful SyncRecord in catalog/views.py AlbumListView: filter(success=True).order_by('-sync_timestamp').first()
- [X] T037 [US4] Pass last_sync to template context in AlbumListView.get_context_data()
- [X] T038 [US4] Add timestamp display HTML to catalog/templates/catalog/album_list.html: data-timestamp attribute with ISO format, span.timeago for display
- [X] T039 [US4] Add JavaScript function updateTimeago() in album_list.html: calculate relative time from data-timestamp, update span.timeago text
- [X] T040 [US4] Add setInterval call in album_list.html: call updateTimeago() every 60000ms (1 minute)
- [X] T041 [US4] Handle "never synced" case in template: check if last_sync exists, show "Never synced" or hide element if null

**Checkpoint**: All user stories complete - sync button works, shows progress, handles errors, displays last sync timestamp

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, documentation, and final validation

- [X] T042 [P] Run pyright type checker and fix any type errors in catalog/models.py, catalog/views.py, catalog/services/sync_manager.py
- [X] T043 [P] Run ruff check and fix linting issues in all modified files
- [X] T044 [P] Run ruff format to ensure consistent code formatting
- [X] T045 [P] Add docstrings to all new functions and classes in sync_manager.py and views.py
- [X] T046 [P] Add inline comments explaining complex logic (threading, database locks, progress tracking)
- [X] T047 Verify all migrations are applied: python manage.py showmigrations catalog
- [ ] T048 Manual integration test: click sync button, observe full flow from trigger → progress → completion
- [ ] T049 Manual error test: unset SPOTIFY_CLIENT_ID, trigger sync, verify error message displays correctly
- [ ] T050 Manual concurrency test: open two tabs, trigger sync in both, verify second shows "already in progress"

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Phases 1-3 only** (T001-T019): Basic sync trigger

- Creates working sync button
- Runs sync in background
- Disables button during operation
- Independent, deployable feature

### Incremental Delivery

1. **After Phase 3**: Deploy MVP - users can trigger sync (P1 complete)
2. **After Phase 4**: Add progress visibility (P1 + P2 partial)
3. **After Phase 5**: Add error handling (P1 + P2 complete)
4. **After Phase 6**: Add timestamp display (all user stories complete)
5. **After Phase 7**: Production-ready with quality validation

### Parallel Execution Opportunities

**Phase 1 (Setup)**:
- T001-T004 can all run in parallel (independent checks)

**Phase 2 (Foundation)**:
- T009, T010 can run in parallel with T005-T008 (after model is defined)

**Phase 3 (US1)**:
- T014, T015 (templates) can run in parallel with T011-T013 (views/services)
- T017, T018, T019 (validation/errors) can run after T011

**Phase 4 (US2)**:
- T022, T023 (template HTML) can run in parallel with T020 (view)
- T025, T026, T027 (SyncManager updates) can run in parallel after T020

**Phase 5 (US3)**:
- T028, T029 (error templates) can run in parallel with T030-T034 (error logic)

**Phase 6 (US4)**:
- T038 (HTML), T039-T040 (JavaScript) can run in parallel with T036-T037 (view updates)

**Phase 7 (Polish)**:
- T042, T043, T044, T045, T046 can all run in parallel (different tools/concerns)

---

## Dependencies

### User Story Dependencies

- **US1 (P1)**: No dependencies (can implement first)
- **US2 (P2)**: Depends on US1 (needs sync trigger and SyncOperation model)
- **US3 (P2)**: Depends on US1 (needs sync trigger infrastructure)
- **US4 (P3)**: Depends on US1 (needs SyncRecord created by successful sync)

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation)
    ↓
Phase 3 (US1 - P1) ←─── MVP here
    ↓
Phase 4 (US2 - P2) ──┐
    ↓                │
Phase 5 (US3 - P2) ──┤ These can run in parallel if desired
    ↓                │
Phase 6 (US4 - P3) ──┘
    ↓
Phase 7 (Polish)
```

**Recommended Order**: Sequential (1 → 2 → 3 → 4 → 5 → 6 → 7) for simplicity, but US2/US3/US4 can be parallelized by different developers after US1 completes.

---

## Task Completion Tracking

**Total Tasks**: 50
- **Setup (Phase 1)**: 4 tasks
- **Foundation (Phase 2)**: 6 tasks
- **User Story 1 (Phase 3)**: 9 tasks
- **User Story 2 (Phase 4)**: 8 tasks
- **User Story 3 (Phase 5)**: 8 tasks
- **User Story 4 (Phase 6)**: 6 tasks
- **Polish (Phase 7)**: 9 tasks

**Parallel Opportunities**: ~20 tasks marked with [P] can run in parallel with other tasks

**Estimated Effort**:
- Phase 1-2: 1 hour (setup and foundation)
- Phase 3 (US1 MVP): 2-3 hours (core sync trigger)
- Phase 4 (US2): 3-4 hours (progress display)
- Phase 5 (US3): 2-3 hours (error handling)
- Phase 6 (US4): 1-2 hours (timestamp)
- Phase 7 (Polish): 2-3 hours (validation and quality)

**Total**: 11-16 hours for complete implementation

---

## Validation Checklist

After completing all tasks, verify:

- [ ] All 12 functional requirements (FR-001 through FR-012) are met
- [ ] All 7 success criteria (SC-001 through SC-007) are satisfied
- [ ] Each user story's acceptance scenarios pass manual testing
- [ ] Pyright reports zero type errors
- [ ] Ruff check reports zero linting errors
- [ ] All docstrings are present on new functions/classes
- [ ] Database migrations are applied and reversible
- [ ] HTMX polling works correctly (starts on syncStarted, stops on completion)
- [ ] Concurrent sync prevention works (409 Conflict returned)
- [ ] Button disables during sync and re-enables after completion/failure

---

**Tasks Status**: ✅ Generated and ready for implementation via `/speckit.implement`
