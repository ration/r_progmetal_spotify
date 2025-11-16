# Tasks: Multi-Tab Google Sheets Parsing

**Input**: Design documents from `/specs/005-multi-tab-parsing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Tests are NOT explicitly requested in the feature specification, so test tasks are omitted per template guidance.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and database schema updates

- [X] T001 Create database migration for SyncOperation.current_tab field in catalog/migrations/0005_syncoperation_current_tab.py
- [X] T002 Run migration to add current_tab field to database

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core TabMetadata structure and utility functions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create TabMetadata dataclass in catalog/services/google_sheets.py
- [X] T004 [P] Implement normalize_tab_name() function in catalog/services/google_sheets.py
- [X] T005 [P] Implement extract_year() function in catalog/services/google_sheets.py
- [X] T006 [P] Implement is_prog_metal_tab() function in catalog/services/google_sheets.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Import Albums from All Years (Priority: P1) 🎯 MVP

**Goal**: Enable synchronization of albums from all available year tabs (2017-2025) instead of just a single tab

**Independent Test**: Trigger sync operation via Django admin or management command, verify albums from multiple year tabs appear in catalog with correct release dates and tab processing shows in logs

### Implementation for User Story 1

- [X] T007 [US1] Update SyncOperation model to add current_tab field in catalog/models.py
- [X] T008 [US1] Implement enumerate_tabs() method in GoogleSheetsService in catalog/services/google_sheets.py
- [X] T009 [US1] Implement filter_tabs() method in GoogleSheetsService in catalog/services/google_sheets.py
- [X] T010 [US1] Implement sort_tabs_chronologically() method in GoogleSheetsService in catalog/services/google_sheets.py
- [X] T011 [US1] Implement fetch_albums_from_tab() method in GoogleSheetsService in catalog/services/google_sheets.py
- [X] T012 [US1] Update SyncManager.run_sync() to iterate through all tabs in catalog/services/sync_manager.py
- [X] T013 [US1] Add per-tab progress tracking in SyncManager in catalog/services/sync_manager.py
- [X] T014 [US1] Update progress message format to show "Tab X/Y: [name] - Album Z/N" in catalog/services/sync_manager.py
- [X] T015 [US1] Implement duplicate detection across tabs using existing spotify_album_id check in catalog/services/sync_manager.py
- [X] T016 [US1] Update .env.example to remove gid parameter from GOOGLE_SHEETS_XLSX_URL documentation

**Checkpoint**: At this point, User Story 1 should be fully functional - multi-tab import working with progress tracking

---

## Phase 4: User Story 2 - View Multi-Year Statistics (Priority: P2)

**Goal**: Display catalog statistics that accurately reflect albums from all imported year tabs

**Independent Test**: After multi-tab import completes, verify statistics panel shows correct total album count and last sync timestamp reflects multi-tab operation

### Implementation for User Story 2

- [X] T017 [US2] Update sync_status view template to display tab-level breakdown in catalog/templates/catalog/sync_status.html
- [X] T018 [US2] Enhance SyncRecord creation to aggregate multi-tab results in catalog/services/sync_manager.py
- [X] T019 [US2] Update catalog statistics view to show multi-year data correctly in catalog/views.py
- [X] T020 [US2] Add tab count display to sync completion message in catalog/templates/catalog/sync_status.html

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - multi-tab import with accurate statistics

---

## Phase 5: User Story 3 - Handle Tab-Specific Errors Gracefully (Priority: P3)

**Goal**: When one tab fails to parse or has data issues, continue processing remaining tabs and provide clear error reporting

**Independent Test**: Simulate a tab with invalid data format (via test fixture or temporarily corrupt a tab), verify sync continues with other tabs and displays which tabs succeeded/failed

### Implementation for User Story 3

- [X] T021 [P] [US3] Create TabProcessingError exception class in catalog/services/google_sheets.py
- [X] T022 [P] [US3] Create CriticalSyncError exception class in catalog/services/google_sheets.py
- [X] T023 [US3] Implement classify_and_handle_error() function in catalog/services/sync_manager.py
- [X] T024 [US3] Add per-tab try-except error isolation in SyncManager.run_sync() in catalog/services/sync_manager.py
- [X] T025 [US3] Implement tab results collection (success/failure per tab) in catalog/services/sync_manager.py
- [X] T026 [US3] Implement finalize_sync_operation() with aggregated error reporting in catalog/services/sync_manager.py
- [X] T027 [US3] Update sync status template to show per-tab success/failure breakdown in catalog/templates/catalog/sync_status.html
- [X] T028 [US3] Add detailed error logging for tab failures in catalog/services/sync_manager.py

**Checkpoint**: All user stories should now be independently functional - robust multi-tab import with error isolation

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T029 [P] Update CLAUDE.md with openpyxl multi-tab patterns in active technologies section
- [X] T030 [P] Add logging statements for tab enumeration, filtering, and sorting in catalog/services/google_sheets.py
- [X] T031 Add input validation for tab names (ASCII check, length limit) in catalog/services/google_sheets.py
- [X] T032 Optimize workbook loading to close resources properly after sync in catalog/services/sync_manager.py
- [X] T033 Add performance logging for multi-tab sync duration in catalog/services/sync_manager.py
- [X] T034 Verify existing Spotify API rate limiting works correctly with multi-tab processing in catalog/services/sync_manager.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after User Story 1 - Depends on multi-tab sync working to display statistics
- **User Story 3 (P3)**: Can start after User Story 1 - Enhances error handling for multi-tab sync

### Within Each User Story

- Models/dataclasses before services
- Services before views/templates
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1: T001-T002 must run sequentially (migration creation then execution)
- Phase 2: T004, T005, T006 marked [P] can run in parallel (different functions)
- Phase 3 (US1): All tasks must run sequentially - they modify the same files and have dependencies
- Phase 4 (US2): All tasks must run sequentially - they build on each other
- Phase 5 (US3): T021, T022 marked [P] can run in parallel (different exception classes)
- Phase 6: T029, T030 marked [P] can run in parallel (different files/concerns)

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all utility functions together:
Task: "Implement normalize_tab_name() function in catalog/services/google_sheets.py"
Task: "Implement extract_year() function in catalog/services/google_sheets.py"
Task: "Implement is_prog_metal_tab() function in catalog/services/google_sheets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (database migration)
2. Complete Phase 2: Foundational (TabMetadata and utility functions)
3. Complete Phase 3: User Story 1 (multi-tab import)
4. **STOP and VALIDATE**: Test multi-tab sync independently with real Google Sheets
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (enhanced statistics)
4. Add User Story 3 → Test independently → Deploy/Demo (robust error handling)
5. Each story adds value without breaking previous stories

### Sequential Implementation Strategy (Single Developer)

Given the sequential nature of most tasks:

1. Complete Setup + Foundational phases
2. Implement User Story 1 (P1) completely - core multi-tab functionality
3. Implement User Story 2 (P2) - statistics enhancement
4. Implement User Story 3 (P3) - error handling enhancement
5. Polish and optimize

---

## Notes

- [P] tasks = different functions/files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No automated tests included per specification - manual testing via Django admin and management commands
- Multi-tab sync duration target: <5 minutes for 11 tabs with 250+ albums
- Progress updates every 5 albums and on tab transitions (every 2s UI polling)
- Existing duplicate detection via spotify_album_id handles cross-tab deduplication
