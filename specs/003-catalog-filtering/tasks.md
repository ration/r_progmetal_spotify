# Tasks: Enhanced Catalog Filtering and Pagination

**Input**: Design documents from `/home/lahtela/git/progmetal/specs/003-catalog-filtering/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Integration tests are included based on spec requirements (19 acceptance scenarios across 4 user stories)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are absolute from repository root

## Path Conventions

- Django app: `catalog/` at repository root
- Tests: `tests/` at repository root
- Config: `config/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verification

- [X] T001 Verify existing Django project structure matches plan.md (catalog/, config/, tests/)
- [X] T002 [P] Verify Album, Artist, Genre, VocalStyle models exist in catalog/models.py
- [X] T003 [P] Verify AlbumListView exists in catalog/views.py
- [X] T004 [P] Verify django-htmx is installed and configured
- [X] T005 Create catalog/templatetags/ directory for custom template tags
- [X] T006 Create catalog/templatetags/__init__.py to make it a Python package

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create catalog/forms.py with base Form class imports
- [X] T008 Create catalog/templatetags/catalog_extras.py with url_replace template tag for URL parameter handling
- [X] T009 [P] Verify database indexes exist on Album.name, Artist.name, Genre.name, Genre.slug, VocalStyle.name, VocalStyle.slug
- [X] T010 Update catalog/views.py to add select_related('artist', 'genre', 'vocal_style') to base queryset for performance
- [X] T011 Create catalog/templates/catalog/components/ directory if it doesn't exist

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Navigate Large Catalog with Pagination (Priority: P1) 🎯 MVP

**Goal**: Display albums in paginated pages (50 items default) with navigation controls

**Independent Test**: Load catalog with 175+ albums, verify exactly 50 albums display on page 1 with navigation showing "Page 1 of 4", click Next to see albums 51-100 on page 2

### Integration Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Write integration test for basic pagination (175 albums → 4 pages) in tests/test_pagination.py
- [X] T013 [P] [US1] Write integration test for pagination with fewer items than page size in tests/test_pagination.py
- [X] T014 [P] [US1] Write integration test for page navigation and URL updates in tests/test_pagination.py
- [X] T015 [P] [US1] Write integration test for browser refresh maintaining page state in tests/test_pagination.py

### Implementation for User Story 1

- [X] T016 [US1] Update AlbumListView in catalog/views.py to add paginate_by=50 and get_paginate_by() method for dynamic page size
- [X] T017 [US1] Create catalog/templates/catalog/components/pagination.html with HTMX-enabled pagination controls
- [X] T018 [US1] Update catalog/templates/catalog/album_list.html to include pagination component and wrap album tiles in #album-tiles div
- [X] T019 [US1] Create catalog/templates/catalog/components/album_tiles_partial.html for HTMX partial updates
- [X] T020 [US1] Update AlbumListView.get_template_names() in catalog/views.py to return partial template for HTMX requests
- [X] T021 [US1] Add pagination context data to AlbumListView.get_context_data() in catalog/views.py

**Checkpoint**: At this point, User Story 1 (pagination) should be fully functional and testable independently

---

## Phase 4: User Story 2 - Free-Text Search Across Album Data (Priority: P2)

**Goal**: Search albums by album name, artist name, genre, vocal style with 500ms debounce and 3-char minimum

**Independent Test**: Enter "Periphery" in search box, verify all Periphery albums display; enter "djent", verify all Djent genre albums display; enter "ab" (2 chars), verify no search triggered

### Integration Tests for User Story 2

- [X] T022 [P] [US2] Write integration test for search by artist name in tests/test_search.py
- [X] T023 [P] [US2] Write integration test for search by album name in tests/test_search.py
- [X] T024 [P] [US2] Write integration test for search by genre in tests/test_search.py
- [X] T025 [P] [US2] Write integration test for search by vocal style in tests/test_search.py
- [X] T026 [P] [US2] Write integration test for search minimum 3 characters validation in tests/test_search.py
- [X] T027 [P] [US2] Write integration test for search query persistence in URL and refresh in tests/test_search.py

### Implementation for User Story 2

- [X] T028 [US2] Create SearchForm class in catalog/forms.py with query field and 3-char validation
- [X] T029 [US2] Create catalog/templates/catalog/components/search_box.html with HTMX debouncing (500ms delay)
- [X] T030 [US2] Update AlbumListView.get_queryset() in catalog/views.py to add Q object search across name, artist__name, genre__name, vocal_style__name with distinct()
- [X] T031 [US2] Update AlbumListView.get_context_data() in catalog/views.py to add search_query and has_search to context
- [X] T032 [US2] Update catalog/templates/catalog/album_list.html to include search_box component above album grid
- [X] T033 [US2] Add client-side JavaScript in catalog/templates/catalog/album_list.html to prevent search requests for queries < 3 characters using htmx:configRequest event
- [X] T034 [US2] Update catalog/templates/catalog/components/album_tiles_partial.html to show empty state for no search results

**Checkpoint**: At this point, User Stories 1 (pagination) AND 2 (search) should both work independently

---

## Phase 5: User Story 3 - Multi-Select Checkbox Filtering by Category (Priority: P3)

**Goal**: Filter albums by multiple genres/vocal styles with OR within category, AND between categories

**Independent Test**: Check "Djent" and "Progressive Metal" genres, verify albums with either genre display; add "Clean" vocal style, verify only Djent/Progressive with clean vocals display; uncheck filters, verify all albums return

### Integration Tests for User Story 3

- [ ] T035 [P] [US3] Write integration test for OR logic within genre category in tests/test_filters.py
- [ ] T036 [P] [US3] Write integration test for AND logic between genre and vocal style categories in tests/test_filters.py
- [ ] T037 [P] [US3] Write integration test for filter changes updating results immediately in tests/test_filters.py
- [ ] T038 [P] [US3] Write integration test for pagination with filtered results in tests/test_filters.py
- [ ] T039 [P] [US3] Write integration test for filter state persistence across refresh in tests/test_filters.py

### Implementation for User Story 3

- [ ] T040 [US3] Create FilterForm class in catalog/forms.py with genre and vocal_style MultipleChoiceField
- [ ] T041 [US3] Create catalog/templates/catalog/components/filters.html with checkbox groups for genres and vocal styles using HTMX
- [ ] T042 [US3] Update AlbumListView.get_queryset() in catalog/views.py to add filter logic using genre__slug__in and vocal_style__slug__in
- [ ] T043 [US3] Update AlbumListView.get_context_data() in catalog/views.py to add selected_genres, selected_vocals, has_filters, filter_count, all_genres, all_vocals to context
- [ ] T044 [US3] Update catalog/templates/catalog/album_list.html to include filters component
- [ ] T045 [US3] Update catalog/templates/catalog/components/album_tiles_partial.html to show empty state for no filter matches and include "Clear filters" button

**Checkpoint**: All core user stories (pagination, search, filters) should now be independently functional

---

## Phase 6: User Story 4 - Configure Page Size (Priority: P4)

**Goal**: Allow users to select page size (25, 50, 100) with preference persisted in session

**Independent Test**: Select "100 items per page", verify 100 albums display and pagination updates to fewer pages; navigate to page 2, verify 100 items per page maintained; close tab and reopen, verify preference remembered

### Integration Tests for User Story 4

- [ ] T046 [P] [US4] Write integration test for page size selection updating display in tests/test_page_size.py
- [ ] T047 [P] [US4] Write integration test for page size persistence across page navigation in tests/test_page_size.py
- [ ] T048 [P] [US4] Write integration test for custom page size with filters in tests/test_page_size.py

### Implementation for User Story 4

- [ ] T049 [US4] Create catalog/templates/catalog/components/page_size_selector.html with select dropdown and sessionStorage JavaScript
- [ ] T050 [US4] Update AlbumListView.get_context_data() in catalog/views.py to add page_size and page_size_options to context
- [ ] T051 [US4] Update catalog/templates/catalog/album_list.html to include page_size_selector component
- [ ] T052 [US4] Add JavaScript in page_size_selector.html to save selection to sessionStorage and restore on page load

**Checkpoint**: All user stories (P1-P4) should now be complete and independently functional

---

## Phase 7: Integration & Edge Cases

**Purpose**: Ensure all user stories work together and handle edge cases

- [ ] T053 [P] Write integration test for search + filters combination (AND logic) in tests/test_integration.py
- [ ] T054 [P] Write integration test for search + filters + pagination in tests/test_integration.py
- [ ] T055 [P] Write integration test for invalid page numbers (redirect to valid page) in tests/test_integration.py
- [ ] T056 [P] Write integration test for empty catalog (0 albums) in tests/test_integration.py
- [ ] T057 [P] Write integration test for special characters in search in tests/test_integration.py
- [ ] T058 Update catalog/views.py to add edge case handling for invalid page numbers (PageNotAnInteger, EmptyPage)
- [ ] T059 Update catalog/templates/catalog/components/album_tiles_partial.html to add hx-swap-oob for pagination updates outside #album-tiles
- [ ] T060 [P] Add type annotations to all functions in catalog/views.py
- [ ] T061 [P] Add type annotations to all functions in catalog/forms.py
- [ ] T062 [P] Add type annotations to catalog/templatetags/catalog_extras.py
- [ ] T063 [P] Add docstrings to all functions in catalog/views.py
- [ ] T064 [P] Add docstrings to all functions in catalog/forms.py
- [ ] T065 [P] Add docstrings to catalog/templatetags/catalog_extras.py

---

## Phase 8: Polish & Validation

**Purpose**: Code quality, performance, and final validation

- [ ] T066 [P] Run pyright type checker on catalog/ and fix any errors
- [ ] T067 [P] Run ruff check on catalog/ and fix any linting errors
- [ ] T068 [P] Run ruff format on catalog/ to ensure consistent formatting
- [ ] T069 Run all integration tests (pytest tests/ -v) and verify 100% pass rate
- [ ] T070 Verify performance: page load < 2s, search/filter updates < 500ms, page navigation < 1s
- [ ] T071 Verify accessibility: keyboard navigation, ARIA labels, screen reader support
- [ ] T072 Manual testing: Complete all 19 acceptance scenarios from spec.md
- [ ] T073 [P] Update CLAUDE.md with any new patterns or learnings from implementation
- [ ] T074 Verify all URLs are bookmarkable (test sharing links with search/filters/page state)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion - Independent of US1 but builds on pagination
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) completion - Independent of US1/US2
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) completion - Independent of other stories
- **Integration (Phase 7)**: Depends on US1, US2, US3 completion (US4 optional)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Pagination)**: No dependencies on other stories - Can start after Foundational
- **User Story 2 (P2 - Search)**: No dependencies on other stories - Can start after Foundational (works with or without pagination)
- **User Story 3 (P3 - Filters)**: No dependencies on other stories - Can start after Foundational (works with or without pagination/search)
- **User Story 4 (P4 - Page Size)**: Depends on US1 (pagination) - Enhances pagination feature

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Template components before view updates
- View queryset changes before context data updates
- Core implementation before edge case handling
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: T002, T003, T004 can run in parallel

**Phase 2 (Foundational)**: T009 can run in parallel with other foundational tasks

**Phase 3 (User Story 1 Tests)**: T012, T013, T014, T015 can all run in parallel (different test functions)

**Phase 4 (User Story 2 Tests)**: T022, T023, T024, T025, T026, T027 can all run in parallel

**Phase 5 (User Story 3 Tests)**: T035, T036, T037, T038, T039 can all run in parallel

**Phase 6 (User Story 4 Tests)**: T046, T047, T048 can all run in parallel

**Phase 7 (Integration Tests)**: T053, T054, T055, T056, T057 can all run in parallel

**Phase 7 (Type Annotations)**: T060, T061, T062 can all run in parallel (different files)

**Phase 7 (Docstrings)**: T063, T064, T065 can all run in parallel (different files)

**Phase 8 (Code Quality)**: T066, T067, T068 can run in parallel (independent tools)

**After Foundational Phase**: User Stories 1, 2, 3 can be worked on in parallel by different developers (US4 depends on US1)

---

## Parallel Example: User Story 2 Tests

All tests for User Story 2 can be launched together since they test different aspects and write to different test functions:

```bash
# Launch all User Story 2 tests in parallel:
Task T022: "Write integration test for search by artist name in tests/test_search.py"
Task T023: "Write integration test for search by album name in tests/test_search.py"
Task T024: "Write integration test for search by genre in tests/test_search.py"
Task T025: "Write integration test for search by vocal style in tests/test_search.py"
Task T026: "Write integration test for search minimum 3 characters validation in tests/test_search.py"
Task T027: "Write integration test for search query persistence in URL and refresh in tests/test_search.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T011) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T012-T021) - Pagination only
4. **STOP and VALIDATE**: Run tests, verify pagination works independently
5. Deploy/demo if ready - Users can now browse paginated catalog

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)** - Pagination working
3. Add User Story 2 → Test independently → **Deploy/Demo** - Search added
4. Add User Story 3 → Test independently → **Deploy/Demo** - Filters added
5. Add User Story 4 → Test independently → **Deploy/Demo** - Page size customization
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) + Foundational (Phase 2) together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T012-T021) - Pagination
   - **Developer B**: User Story 2 (T022-T034) - Search
   - **Developer C**: User Story 3 (T035-T045) - Filters
3. User Story 4 starts after US1 completes (T046-T052)
4. Integration work (Phase 7) starts after core stories complete
5. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 74

**By Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 5 tasks (BLOCKING)
- Phase 3 (US1 - Pagination): 10 tasks (4 tests + 6 implementation)
- Phase 4 (US2 - Search): 13 tasks (6 tests + 7 implementation)
- Phase 5 (US3 - Filters): 11 tasks (5 tests + 6 implementation)
- Phase 6 (US4 - Page Size): 7 tasks (3 tests + 4 implementation)
- Phase 7 (Integration): 13 tasks (5 tests + 8 implementation/quality)
- Phase 8 (Polish): 9 tasks

**By User Story**:
- US1 (Pagination): 10 tasks
- US2 (Search): 13 tasks
- US3 (Filters): 11 tasks
- US4 (Page Size): 7 tasks
- Cross-cutting: 33 tasks (setup, foundational, integration, polish)

**Parallel Opportunities**: 46 tasks marked [P] can run in parallel when dependencies are met

**Independent Test Coverage**: Each user story has 3-6 integration tests covering all acceptance scenarios from spec.md

---

## Notes

- All tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks = different files or independent operations, no dependencies
- [Story] label (US1-US4) maps task to specific user story for traceability
- Each user story is independently completable and testable per Constitution Principle III
- Tests are written FIRST and must FAIL before implementation (TDD approach)
- Type annotations, linting, and docstrings enforced per Constitution Principle II
- Commit after each logical task group
- Stop at any checkpoint to validate story independently
- 19 acceptance scenarios from spec.md are covered by 27 integration tests across phases
