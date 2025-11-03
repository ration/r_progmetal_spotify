# Tasks: Catalog Statistics

**Input**: Design documents from `/specs/002-catalog-statistics/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: No automated tests requested in specification - manual testing using quickstart.md guide

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Django web application structure:
- **catalog/**: Main Django app (models, views, templates, commands)
- **config/**: Django project settings
- **tests/**: Test files (optional, not required by spec)

---

## Phase 1: Setup

**Purpose**: Project initialization and dependency configuration

- [x] T001 Add django.contrib.humanize to INSTALLED_APPS in config/settings.py

**Checkpoint**: Humanize app enabled for template filters (naturaltime, intcomma)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Add SyncRecord model to catalog/models.py with full type annotations
- [x] T003 [P] Register SyncRecord in Django admin in catalog/admin.py
- [x] T004 Create database migration for SyncRecord model (python manage.py makemigrations catalog)
- [x] T005 Apply migration to create catalog_syncrecord table (python manage.py migrate)

**Checkpoint**: Foundation ready - SyncRecord model exists, migrated, visible in admin

---

## Phase 3: User Story 1 - View Catalog Freshness (Priority: P1) 🎯 MVP

**Goal**: Display when the catalog was last synchronized so users know if data is current

**Independent Test**: Navigate to catalog page and verify "Last synchronized: X ago" displays prominently. If never synchronized, shows "Not yet synchronized". (See quickstart.md Scenario 1-4)

### Implementation for User Story 1

- [x] T006 [US1] Modify catalog/management/commands/import_albums.py to create SyncRecord after successful sync
- [x] T007 [US1] Update catalog/views.py AlbumListView.get_context_data() to query latest_sync and pass to template
- [x] T008 [US1] Create catalog/templates/catalog/components/stats_panel.html template component for statistics display
- [ ] T009 [US1] Modify catalog/templates/catalog/album_list.html to include stats_panel.html with humanize filters for timestamp
- [ ] T010 [US1] Run pyright type checking and fix any type errors
- [ ] T011 [US1] Run ruff check and ruff format on modified files
- [ ] T012 [US1] Manually test using quickstart.md Scenarios 1-4 (never synchronized, first sync, relative time, absolute time)

**Checkpoint**: At this point, User Story 1 (View Catalog Freshness) should be fully functional and testable independently. Users can see "Last synchronized: X ago" on catalog page.

---

## Phase 4: User Story 2 - View Total Catalog Size (Priority: P2)

**Goal**: Display total number of albums in catalog so users understand collection scope

**Independent Test**: Navigate to catalog page and verify total album count displays with thousands separators (e.g., "1,247 albums"). Works with both empty and large catalogs. (See quickstart.md Scenarios 5, 9)

### Implementation for User Story 2

- [ ] T013 [US2] Update catalog/views.py AlbumListView.get_context_data() to add total_albums count to context
- [ ] T014 [US2] Modify catalog/templates/catalog/components/stats_panel.html to display total_albums with intcomma filter
- [ ] T015 [US2] Run pyright type checking and fix any type errors
- [ ] T016 [US2] Run ruff check and ruff format on modified files
- [ ] T017 [US2] Manually test using quickstart.md Scenarios 5, 9 (large catalog with thousands separator, empty catalog)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users see both last sync time AND total album count.

---

## Phase 5: User Story 3 - See Recent Growth (Priority: P3)

**Goal**: Display how many albums were added in last sync so users can identify new content

**Independent Test**: Perform sync that adds albums, verify "+N new" displays. Perform sync with zero additions, verify "+0 new" or no indicator. (See quickstart.md Scenarios 6-7)

### Implementation for User Story 3

- [ ] T018 [US3] Modify catalog/templates/catalog/components/stats_panel.html to display albums_created count from latest_sync
- [ ] T019 [US3] Add conditional logic to hide/show growth indicator when albums_created is 0
- [ ] T020 [US3] Run pyright type checking and fix any type errors
- [ ] T021 [US3] Run ruff check and ruff format on modified files
- [ ] T022 [US3] Manually test using quickstart.md Scenarios 6-7 (subsequent sync with new albums, sync with zero new albums)

**Checkpoint**: All user stories should now be independently functional. Users see complete statistics: last sync time, total albums, and recent additions.

---

## Phase 6: Per-Album Import Timestamps (Enhancement)

**Goal**: Display when each individual album was added to the database on album tiles

**Independent Test**: Navigate to catalog page and verify each album tile shows "Added: X ago" using the album's imported_at timestamp

**Rationale**: Complements catalog-wide statistics by showing per-album freshness. Uses existing Album.imported_at field and same humanize filters already enabled in Phase 1.

### Implementation for Per-Album Timestamps

- [ ] T023 [P] Modify catalog/templates/catalog/components/album_tile.html to display album.imported_at using naturaltime filter
- [ ] T024 Manually test album tiles show "Added: X ago" for each album (verify relative time formatting works)
- [ ] T025 Run pyright and ruff checks on modified template file

**Checkpoint**: Album tiles now show both catalog-wide statistics (top of page) and per-album import timestamps (on each tile).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, testing, and documentation

- [ ] T026 [P] Manually test HTMX filter interaction using quickstart.md Scenario 8 (verify statistics remain visible during filtering)
- [ ] T027 [P] Manually test multiple syncs using quickstart.md Scenario 10 (verify latest sync always shown)
- [ ] T028 [P] Verify visual layout on desktop/tablet/mobile viewports per quickstart.md checklist
- [ ] T029 [P] Verify performance: page load < 2 seconds, statistics query < 50ms (use Django Debug Toolbar if available)
- [ ] T030 [P] Verify Django admin interface for SyncRecord per quickstart.md admin verification section
- [ ] T031 Run final pyright check on entire catalog app
- [ ] T032 Run final ruff check on entire catalog app
- [ ] T033 Validate all acceptance criteria from spec.md are met (3 user stories, 10 functional requirements, 5 success criteria)

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Integrates with US1/US2 but independently testable
- **Per-Album Timestamps (Phase 6)**: Can start after Phase 1 (Setup) - Independent of user stories, uses existing Album.imported_at field

**All user stories are independently testable**: Each can be demonstrated and validated on its own using quickstart.md test scenarios.

### Within Each User Story

- Models before views (T002 before T007)
- Views before templates (T007 before T008-T009)
- Templates before testing (T009 before T012)
- Implementation before quality checks (T006-T009 before T010-T011)
- Quality checks before manual testing (T010-T011 before T012)

### Parallel Opportunities

- **Setup phase**: Only 1 task, no parallelization
- **Foundational phase**: T002 and T003 can run in parallel (different files)
- **Within User Stories**: All implementation tasks in a story must complete before quality checks
- **Per-Album Timestamps (Phase 6)**: T023 can be done in parallel with any user story work (independent template file)
- **Polish phase**: Tasks T026-T030 marked [P] can run in parallel (independent testing activities)
- **Different user stories**: Can be worked on in parallel by different team members after Foundational phase completes

---

## Parallel Example: Foundational Phase

```bash
# Launch these tasks together:
Task: "Add SyncRecord model to catalog/models.py with full type annotations"
Task: "Register SyncRecord in Django admin in catalog/admin.py"

# Then sequentially:
Task: "Create database migration" (depends on model code)
Task: "Apply migration" (depends on migration file)
```

---

## Parallel Example: Polish Phase

```bash
# Launch all these testing tasks together:
Task: "Manually test HTMX filter interaction using quickstart.md Scenario 8"
Task: "Manually test multiple syncs using quickstart.md Scenario 10"
Task: "Verify visual layout on desktop/tablet/mobile viewports"
Task: "Verify performance metrics"
Task: "Verify Django admin interface for SyncRecord"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (1 task)
2. Complete Phase 2: Foundational (4 tasks - CRITICAL)
3. Complete Phase 3: User Story 1 (7 tasks)
4. **STOP and VALIDATE**: Test User Story 1 independently using quickstart.md Scenarios 1-4
5. Demo to stakeholders: "Users can now see when catalog was last synchronized"

**MVP delivers**: Basic sync freshness display - most critical user need met

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (P1) → Test independently → Demo (MVP! 🎯)
3. Add User Story 2 (P2) → Test independently → Demo (total count added)
4. Add User Story 3 (P3) → Test independently → Demo (growth indicator added)
5. Add Per-Album Timestamps (Phase 6) → Test independently → Demo (per-album freshness)
6. Each phase adds value without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (5 tasks)
2. Once Foundational is done:
   - Developer A: User Story 1 (7 tasks)
   - Developer B: User Story 2 (5 tasks) - can start in parallel
   - Developer C: User Story 3 (5 tasks) - can start in parallel
3. Stories complete and integrate independently

**Note**: User Story 2 and 3 both modify stats_panel.html, so coordinate merge order: US1 → US2 → US3

---

## Task Count Summary

- **Phase 1 (Setup)**: 1 task
- **Phase 2 (Foundational)**: 4 tasks
- **Phase 3 (User Story 1)**: 7 tasks 🎯 MVP
- **Phase 4 (User Story 2)**: 5 tasks
- **Phase 5 (User Story 3)**: 5 tasks
- **Phase 6 (Per-Album Timestamps)**: 3 tasks
- **Phase 7 (Polish)**: 8 tasks

**Total**: 33 tasks

**Parallel opportunities**: 2 in Foundational, 1 in Per-Album Timestamps, 5 in Polish = 8 tasks can run concurrently

**MVP scope**: Phases 1-3 (12 tasks) deliver core value (catalog freshness display)
**Enhanced scope**: Add Phase 6 (+3 tasks) for per-album timestamps

---

## File Modification Summary

**New Files** (2):
- catalog/migrations/0003_syncrecord.py (auto-generated)
- catalog/templates/catalog/components/stats_panel.html

**Modified Files** (7):
- config/settings.py (add humanize to INSTALLED_APPS)
- catalog/models.py (add SyncRecord model)
- catalog/admin.py (register SyncRecord)
- catalog/management/commands/import_albums.py (create SyncRecord after sync)
- catalog/views.py (add latest_sync and total_albums to context)
- catalog/templates/catalog/album_list.html (include stats_panel component)
- catalog/templates/catalog/components/album_tile.html (add per-album imported_at timestamp)

**No Changes Needed** (verified):
- catalog/templates/catalog/album_list_tiles.html (HTMX partial unchanged)
- catalog/services/*.py (no changes needed)
- All test files (no automated tests requested)

---

## Notes

- All tasks follow strict checklist format: `- [ ] TaskID [P?] [Story?] Description with file path`
- No automated tests requested in spec - use quickstart.md for manual testing
- Type safety enforced via pyright checks after each user story
- Code quality enforced via ruff checks after each user story
- Each user story is independently deployable and demonstrable
- Stop at any checkpoint to validate story independently before proceeding
- Django's built-in humanize app used (no custom template filters needed)
- SyncRecord model created by management command only (not manually via admin)

---

## Ready to Execute

All tasks are immediately executable with clear file paths and acceptance criteria. Begin with Phase 1 (T001), proceed sequentially through phases, validating at each checkpoint.

**Recommended first milestone**: Complete through Phase 3 (T001-T012) for MVP deployment.
