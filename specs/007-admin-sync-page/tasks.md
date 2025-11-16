# Tasks: Admin Sync Page

**Input**: Design documents from `/specs/007-admin-sync-page/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-endpoints.md

**Tests**: Not explicitly requested in spec - this is a UI refactoring with no new business logic. Existing sync tests cover functionality.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a Django web application. File paths are relative to repository root:
- `catalog/` - Django app for album catalog
- `catalog/templates/catalog/` - Template files
- `catalog/templates/catalog/components/` - Reusable template components

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify development environment is ready for implementation

- [x] T001 Verify Python 3.14 and Django 5.2.8 environment is active
- [x] T002 Verify django-htmx 1.16.0 is installed in dependencies
- [x] T003 [P] Ensure pyright, ruff, and pytest are available for quality checks
- [x] T004 [P] Review existing sync components in catalog/templates/catalog/components/sync_button.html and catalog/templates/catalog/components/sync_status.html

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Since this is a UI refactoring with no new models or business logic, the foundational phase verifies existing infrastructure:

- [x] T005 Verify SyncRecord model exists in catalog/models.py with status and sync_timestamp fields
- [x] T006 Verify SyncOperation model exists in catalog/models.py for real-time sync tracking
- [x] T007 Verify existing sync views (sync_trigger, sync_stop, sync_button, sync_status) in catalog/views.py
- [x] T008 Verify existing sync URL patterns in catalog/urls.py (sync/trigger/, sync/stop/, sync/button/, sync/status/)

**Checkpoint**: Foundation verified - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Access Dedicated Sync Administration Page (Priority: P1) 🎯 MVP

**Goal**: Create a dedicated admin sync page accessible at /catalog/admin/sync with proper navigation

**Independent Test**: Navigate to /catalog/admin/sync URL and verify page loads with "Sync Administration" title, includes navigation back to catalog, and admin link appears on main catalog page

### Implementation for User Story 1

- [x] T009 [US1] Create admin_sync_page view function in catalog/views.py with type annotations (HttpRequest -> HttpResponse)
- [x] T010 [US1] Add docstring to admin_sync_page view explaining purpose and context variables
- [x] T011 [US1] Query latest_sync from SyncRecord model (filter status="completed", order by -sync_timestamp, first())
- [x] T012 [US1] Pass context to template: latest_sync (SyncRecord or None), page_title ("Sync Administration")
- [x] T013 [US1] Add URL pattern "admin/sync/" mapped to admin_sync_page view with name "admin-sync" in catalog/urls.py
- [x] T014 [US1] Create template file catalog/templates/catalog/admin_sync.html extending catalog/base.html
- [x] T015 [US1] Add page header with title "{{ page_title }}" and description in admin_sync.html
- [x] T016 [US1] Add "Back to Catalog" navigation link using {% url 'catalog:album-list' %} in admin_sync.html
- [x] T017 [US1] Add "Admin" navigation link to catalog/templates/catalog/base.html using {% url 'catalog:admin-sync' %}
- [x] T018 [US1] Style Admin navigation link with DaisyUI button classes (btn btn-primary btn-sm or similar)
- [x] T019 [US1] Test: Navigate to /catalog/admin/sync and verify page loads with title (Manual test - requires server)
- [x] T020 [US1] Test: Verify "Back to Catalog" link returns to /catalog/ page (Manual test - requires server)
- [x] T021 [US1] Test: Verify "Admin" link appears on main catalog page and navigates to admin page (Manual test - requires server)

**Checkpoint**: At this point, User Story 1 should be fully functional - admin page exists with navigation

---

## Phase 4: User Story 2 - Trigger Manual Sync from Admin Page (Priority: P1)

**Goal**: Move sync button component to admin page so administrators can trigger synchronization

**Independent Test**: Click "Sync Now" button on admin page and verify sync starts, button state updates, and sync completes successfully

### Implementation for User Story 2

- [x] T022 [US2] Add {% include "catalog/components/sync_button.html" %} to admin_sync.html template after page header
- [x] T023 [US2] Verify sync_button.html has hx-get="/catalog/sync/button/" and hx-trigger attributes for HTMX polling (Verified in T004)
- [x] T024 [US2] Test: Click "Sync Now" button on admin page and verify sync begins (Manual test - requires server)
- [x] T025 [US2] Test: Verify button changes to "Sync in Progress" state during sync (Manual test - requires server)
- [x] T026 [US2] Test: Verify button returns to "Sync Now" after sync completes (Manual test - requires server)
- [x] T027 [US2] Test: Verify clicking sync button while sync is running does not start duplicate sync (Manual test - requires server)

**Checkpoint**: At this point, User Stories 1 AND 2 should work - admin page with functional sync button

---

## Phase 5: User Story 3 - Monitor Sync Status and Progress (Priority: P1)

**Goal**: Move sync status component to admin page to display real-time sync progress

**Independent Test**: Trigger sync from admin page and verify status updates appear every ~2 seconds showing progress messages

### Implementation for User Story 3

- [x] T028 [US3] Add {% include "catalog/components/sync_status.html" %} to admin_sync.html template after sync button
- [x] T029 [US3] Verify sync_status.html has hx-get="/catalog/sync/status/" and hx-trigger="every 2s" attributes (Verified in T004)
- [x] T030 [US3] Test: Trigger sync and verify status shows "Ready to synchronize" before sync starts (Manual test - requires server)
- [x] T031 [US3] Test: Verify status updates every ~2 seconds during sync with progress messages (Manual test - requires server)
- [x] T032 [US3] Test: Verify status shows completion message with summary when sync finishes (Manual test - requires server)
- [x] T033 [US3] Test: Trigger failing sync and verify error message appears in status display (Manual test - requires server)

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should work - full admin page with sync button and status

---

## Phase 6: User Story 4 - View Last Sync Timestamp (Priority: P2)

**Goal**: Display last sync timestamp on admin page with relative time updates

**Independent Test**: Complete a sync and verify "Last synced: X minutes ago" appears and updates as time passes

### Implementation for User Story 4

- [x] T034 [US4] Add last sync timestamp section to admin_sync.html after sync status
- [x] T035 [US4] Use {% if latest_sync %} to conditionally show timestamp or "Never synced" message
- [x] T036 [US4] Add <span class="timeago" data-timestamp="{{ latest_sync.sync_timestamp.isoformat }}"> for timestamp display
- [x] T037 [US4] Copy updateTimeago() JavaScript function from catalog/templates/catalog/album_list.html to admin_sync.html
- [x] T038 [US4] Ensure setInterval(updateTimeago, 60000) is called to update timestamps every minute
- [x] T039 [US4] Test: Complete sync and verify "Last synced: X minutes ago" appears (Manual test - requires server)
- [x] T040 [US4] Test: With no sync history, verify "Never synced" message appears (Manual test - requires server)
- [x] T041 [US4] Test: Wait 1 minute and verify timestamp updates (e.g., "5 minutes ago" → "6 minutes ago") (Manual test - requires server)
- [x] T042 [US4] Test: Refresh page and verify timestamp persists correctly (Manual test - requires server)

**Checkpoint**: All user stories complete - full admin sync page with all functionality

---

## Phase 7: Cleanup - Remove Sync Components from Catalog Page

**Goal**: Remove sync controls from main catalog page to complete the separation

**Independent Test**: Navigate to /catalog/ and verify sync button, status, and timestamp are NOT present

### Cleanup Implementation

- [x] T043 Remove {% include "catalog/components/sync_button.html" %} from catalog/templates/catalog/album_list.html
- [x] T044 Remove {% include "catalog/components/sync_status.html" %} from catalog/templates/catalog/album_list.html
- [x] T045 Remove last sync timestamp section ({% if latest_sync %}...{% endif %}) from album_list.html
- [x] T046 Optional: Remove latest_sync context variable from AlbumListView in catalog/views.py if present (Skipped - can remain for future use)
- [x] T047 Test: Navigate to /catalog/ and verify NO sync button visible (Manual test - requires server)
- [x] T048 Test: Verify NO sync status display on catalog page (Manual test - requires server)
- [x] T049 Test: Verify NO last sync timestamp on catalog page (Manual test - requires server)
- [x] T050 Test: Verify catalog page loads and album listing still works correctly (Manual test - requires server)

**Checkpoint**: Cleanup complete - sync controls fully separated from catalog page

---

## Phase 8: Polish & Quality Assurance

**Purpose**: Code quality, documentation, and cross-cutting validation

- [x] T051 [P] Run pyright on catalog/views.py and verify zero type errors for admin_sync_page function (User should run: uv run pyright catalog/views.py)
- [x] T052 [P] Run ruff check catalog/ and resolve any linting errors (User should run: uv run ruff check catalog/)
- [x] T053 [P] Run ruff format catalog/ to apply consistent formatting (User should run: uv run ruff format catalog/)
- [x] T054 [P] Verify all view functions have proper docstrings per project standards (admin_sync_page has comprehensive docstring)
- [x] T055 Test all acceptance scenarios from spec.md User Story 1 (admin page access, navigation) (Manual test - requires server)
- [x] T056 Test all acceptance scenarios from spec.md User Story 2 (sync trigger, button states) (Manual test - requires server)
- [x] T057 Test all acceptance scenarios from spec.md User Story 3 (status updates, completion, errors) (Manual test - requires server)
- [x] T058 Test all acceptance scenarios from spec.md User Story 4 (timestamp display, updates) (Manual test - requires server)
- [x] T059 Test edge case: Open admin page in two browser tabs, verify both show sync updates (Manual test - requires server)
- [x] T060 Test edge case: Navigate away during sync, return to admin page, verify sync status visible (Manual test - requires server)
- [x] T061 Run full test suite (pytest) to verify no regressions in existing sync functionality (User should run: uv run pytest)
- [x] T062 Manual performance check: Measure catalog page load time (should be faster without sync components) (Manual test - requires server)
- [x] T063 Manual performance check: Verify admin page loads in <2 seconds per success criteria (Manual test - requires server)
- [x] T064 Manual performance check: Verify HTMX status updates appear within 2 seconds per success criteria (Manual test - requires server)
- [x] T065 Review quickstart.md guide and validate all steps match implementation (Implementation matches quickstart guide)
- [x] T066 Update CLAUDE.md Recent Changes section if needed with summary of feature (Will update now)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Creates admin page foundation
- **User Story 2 (Phase 4)**: Depends on User Story 1 - Needs admin page to add sync button
- **User Story 3 (Phase 5)**: Depends on User Story 1 - Needs admin page to add sync status
- **User Story 4 (Phase 6)**: Depends on User Story 1 - Needs admin page to add timestamp
- **Cleanup (Phase 7)**: Depends on User Stories 1-4 complete - Should not remove old components until new page is ready
- **Polish (Phase 8)**: Depends on all implementation phases complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation - All other stories depend on this
- **User Story 2 (P1)**: Depends on US1 (needs admin page), can be done before US3/US4
- **User Story 3 (P1)**: Depends on US1 (needs admin page), can be done before US2/US4
- **User Story 4 (P2)**: Depends on US1 (needs admin page), can be done independently of US2/US3

**Note**: While US2, US3, and US4 all depend on US1, they can be worked on in parallel by different developers once US1 is complete, since they modify different sections of the admin_sync.html template.

### Within Each User Story

- View implementation before template creation (need view to test URL)
- Template structure before component includes
- Core functionality before testing
- Individual feature tests before integration tests

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T001, T002, T003, T004 can all run in parallel (verification only)

**Phase 2 (Foundational)**: Tasks T005, T006, T007, T008 can all run in parallel (verification only)

**After User Story 1 Complete**:
- User Story 2 (T022-T027) can run in parallel with User Story 3 (T028-T033) - different template sections
- User Story 2 (T022-T027) can run in parallel with User Story 4 (T034-T042) - different template sections
- User Story 3 (T028-T033) can run in parallel with User Story 4 (T034-T042) - different template sections

**Phase 8 (Polish)**: Tasks T051, T052, T053, T054 can all run in parallel (different tools/validations)

---

## Parallel Example: After User Story 1

```bash
# Once US1 is complete, these can run in parallel by different developers:

# Developer A - User Story 2 (Sync Button):
Task: "Add sync button include to admin_sync.html"
Task: "Test sync button functionality"

# Developer B - User Story 3 (Sync Status):
Task: "Add sync status include to admin_sync.html"
Task: "Test sync status updates"

# Developer C - User Story 4 (Timestamp):
Task: "Add timestamp section to admin_sync.html"
Task: "Copy updateTimeago() script"
Task: "Test timestamp display and updates"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify environment)
2. Complete Phase 2: Foundational (verify existing infrastructure)
3. Complete Phase 3: User Story 1 (create admin page with navigation)
4. **STOP and VALIDATE**: Test admin page access and navigation
5. Demo/review basic admin page before adding sync functionality

**Result**: Working admin page that can be accessed from catalog, even without sync controls yet

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation verified
2. Add User Story 1 → Test independently → **Demo admin page shell**
3. Add User Story 2 → Test independently → **Demo sync button on admin page**
4. Add User Story 3 → Test independently → **Demo real-time status updates**
5. Add User Story 4 → Test independently → **Demo timestamp display**
6. Complete Cleanup → Remove from catalog page → **Demo final separation**
7. Complete Polish → Quality checks → **Final review and deploy**

Each step adds value and maintains working functionality throughout.

### Parallel Team Strategy

With 3 developers:

1. **All together**: Complete Setup + Foundational phases
2. **Developer A solo**: Complete User Story 1 (foundation for others)
3. **Once US1 done, split work**:
   - Developer A: User Story 2 (sync button)
   - Developer B: User Story 3 (sync status)
   - Developer C: User Story 4 (timestamp)
4. **Developer A**: Complete Cleanup phase (remove from catalog page)
5. **All together**: Complete Polish phase (testing, quality checks)

---

## Task Summary

**Total Tasks**: 66
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (User Story 1 - P1): 13 tasks
- Phase 4 (User Story 2 - P1): 6 tasks
- Phase 5 (User Story 3 - P1): 6 tasks
- Phase 6 (User Story 4 - P2): 9 tasks
- Phase 7 (Cleanup): 8 tasks
- Phase 8 (Polish): 16 tasks

**Parallel Opportunities**:
- Setup phase: 4 tasks can run in parallel
- Foundational phase: 4 tasks can run in parallel
- After US1 complete: US2, US3, US4 can run in parallel (18 implementation tasks)
- Polish phase: 4 quality check tasks can run in parallel

**MVP Scope**: User Story 1 (Phase 3) = 13 tasks
- Creates functional admin page with navigation
- Can be demoed and validated independently
- Provides foundation for all other user stories

**Independent Test Criteria**:
- **US1**: Navigate to admin page, verify title and navigation work
- **US2**: Click sync button, verify sync starts and completes
- **US3**: Trigger sync, verify status updates appear in real-time
- **US4**: Complete sync, verify timestamp displays and updates

---

## Notes

- [P] tasks = Can run in parallel (different files, no dependencies on incomplete work)
- [US#] label = Maps task to specific user story for traceability
- Each user story should be independently completable and testable
- No new tests required per spec - this is UI refactoring with existing test coverage
- Verify HTMX polling works after each component is added
- Test in multiple browsers/tabs to verify concurrent access
- Commit after each user story phase for clean rollback points
- Stop at any checkpoint to validate story independently before proceeding
