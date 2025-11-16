# Tasks: Just-in-Time Spotify API Usage

**Input**: Design documents from `/specs/006-jit-spotify-api/`
**Prerequisites**: plan.md (tech stack), spec.md (user stories), data-model.md (entities), contracts/endpoints.md (API contracts), research.md (decisions), quickstart.md (validation)

**Tests**: Test tasks are included per constitution requirements (contract tests, integration tests, unit tests)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Django app structure: `catalog/` for application code, `config/` for settings, `tests/` at repository root
- Models: `catalog/models.py`
- Services: `catalog/services/`
- Views: `catalog/views.py`
- Templates: `catalog/templates/catalog/`
- Management commands: `catalog/management/commands/`
- Tests: `tests/contract/`, `tests/integration/`, `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema changes and configuration setup

- [x] T001 Create database migration 0006_add_spotify_cache_fields in catalog/migrations/
- [x] T002 Add spotify_cover_url field (nullable URLField, max_length=500, indexed) to Album model in catalog/models.py
- [x] T003 Add spotify_cover_cached_at field (nullable DateTimeField) to Album model in catalog/models.py
- [x] T004 Add spotify_metadata_json field (nullable JSONField) to Album model in catalog/models.py
- [x] T005 Add spotify_metadata_cached_at field (nullable DateTimeField) to Album model in catalog/models.py
- [x] T006 Add database index on spotify_cover_cached_at field in catalog/models.py
- [x] T007 Add clean() validation method to Album model for cache field consistency in catalog/models.py
- [x] T008 Run migration to apply schema changes (python manage.py migrate)
- [x] T009 [P] Configure Spotify API settings in config/settings.py (SPOTIFY_MAX_CONCURRENT=10, SPOTIFY_RETRY_ATTEMPTS=3)

**Checkpoint**: ✅ Database schema updated, configuration ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core services and utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T010 Create album_cache.py service module in catalog/services/
- [x] T011 Implement extract_spotify_album_id() function with regex parsing in catalog/services/album_cache.py
- [x] T012 Implement get_cached_cover_url() function to check Album.spotify_cover_url in catalog/services/album_cache.py
- [x] T013 Implement cache_cover_url() function with select_for_update() locking in catalog/services/album_cache.py
- [x] T014 Implement get_cached_metadata() function to check Album.spotify_metadata_json in catalog/services/album_cache.py
- [x] T015 Implement cache_metadata() function with select_for_update() locking in catalog/services/album_cache.py
- [x] T016 Add fetch_album_cover() method to SpotifyClient class in catalog/services/spotify_client.py
- [x] T017 Add fetch_album_metadata() method to SpotifyClient class in catalog/services/spotify_client.py
- [x] T018 Add rate_limited decorator with exponential backoff to spotify_client.py
- [x] T019 Add Spotify error logging (rate limits, API failures) to spotify_client.py

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Album Catalog with Cover Art (Priority: P1) 🎯 MVP

**Goal**: Users can browse albums with cover art loaded progressively as they scroll. Cover art is fetched from Spotify on-demand when albums enter viewport.

**Independent Test**: Load catalog page, verify skeleton placeholders initially, scroll to reveal albums, confirm cover art loads within 1 second, reload page to verify cache hit (instant display).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US1] Contract test for GET /catalog/album/<id>/cover-art/ endpoint in tests/contract/test_spotify_endpoints.py
- [ ] T021 [P] [US1] Contract test verifying HTML response format with <img> tag in tests/contract/test_spotify_endpoints.py
- [ ] T022 [P] [US1] Contract test verifying JSON response format with cover_url field in tests/contract/test_spotify_endpoints.py
- [ ] T023 [P] [US1] Contract test for error responses (404, 429, 500) in tests/contract/test_spotify_endpoints.py
- [ ] T024 [P] [US1] Integration test for lazy cover art loading on catalog page in tests/integration/test_lazy_loading.py
- [ ] T025 [P] [US1] Integration test for cache hit scenario (second page load) in tests/integration/test_lazy_loading.py
- [ ] T026 [P] [US1] Integration test for placeholder display on API error in tests/integration/test_lazy_loading.py
- [ ] T027 [P] [US1] Unit test for extract_spotify_album_id() with valid URLs in tests/unit/test_album_cache.py
- [ ] T028 [P] [US1] Unit test for extract_spotify_album_id() with invalid URLs in tests/unit/test_album_cache.py
- [ ] T029 [P] [US1] Unit test for cache_cover_url() with concurrent requests in tests/unit/test_album_cache.py

### Implementation for User Story 1

- [ ] T030 [US1] Create album_cover_art view function in catalog/views.py
- [ ] T031 [US1] Implement cache check logic in album_cover_art view using get_cached_cover_url()
- [ ] T032 [US1] Implement Spotify API fetch logic in album_cover_art view using fetch_album_cover()
- [ ] T033 [US1] Implement cache update logic in album_cover_art view using cache_cover_url()
- [ ] T034 [US1] Add error handling for rate limits (return skeleton placeholder) in album_cover_art view
- [ ] T035 [US1] Add error handling for API failures (return unavailable placeholder) in album_cover_art view
- [ ] T036 [US1] Add error handling for missing Spotify URL (return no-spotify placeholder) in album_cover_art view
- [ ] T037 [US1] Add HTML response rendering with <img> tag in album_cover_art view
- [ ] T038 [US1] Add JSON response format support with format=json query param in album_cover_art view
- [ ] T039 [US1] Add URL route for /catalog/album/<int:album_id>/cover-art/ in catalog/urls.py
- [ ] T040 [US1] Update album_list.html template to render skeleton placeholders initially in catalog/templates/catalog/album_list.html
- [ ] T041 [US1] Add HTMX hx-get attribute with /catalog/album/{id}/cover-art/ in catalog/templates/catalog/components/album_tile.html
- [ ] T042 [US1] Add HTMX hx-trigger="intersect once" attribute to album tile figure in catalog/templates/catalog/components/album_tile.html
- [ ] T043 [US1] Add HTMX hx-swap="innerHTML" attribute to album tile figure in catalog/templates/catalog/components/album_tile.html
- [ ] T044 [US1] Add CSS fade-in animation for cover art load transition in catalog/templates/catalog/album_list.html or static CSS
- [ ] T045 [US1] Add HX-Trigger response header for cover-art-loaded event in album_cover_art view
- [ ] T046 [US1] Update catalog view to use select_related() for artist and prefetch_related() for genres to optimize queries in catalog/views.py

**Checkpoint**: At this point, User Story 1 should be fully functional - catalog displays with progressive cover art loading

---

## Phase 4: User Story 2 - Import Albums Without Spotify Dependencies (Priority: P2)

**Goal**: Administrators can import albums from Google Sheets quickly without Spotify API calls. Import stores only basic data + Spotify URLs.

**Independent Test**: Run import command, verify albums stored with spotify_url populated but spotify_cover_url=NULL, confirm import completes 50%+ faster than old approach, verify no Spotify API calls logged.

### Tests for User Story 2 ⚠️

- [ ] T047 [P] [US2] Integration test for import_albums command without Spotify calls in tests/integration/test_album_import.py
- [ ] T048 [P] [US2] Integration test verifying albums have spotify_url but no spotify_cover_url after import in tests/integration/test_album_import.py
- [ ] T049 [P] [US2] Integration test for import completion when Spotify API unavailable in tests/integration/test_album_import.py
- [ ] T050 [P] [US2] Integration test measuring import performance (baseline vs optimized) in tests/integration/test_album_import.py
- [ ] T051 [P] [US2] Unit test for Spotify URL extraction from Google Sheets data in tests/unit/test_spotify_client.py

### Implementation for User Story 2

- [ ] T052 [US2] Modify import_albums management command to add --skip-spotify flag (default=True) in catalog/management/commands/import_albums.py
- [ ] T053 [US2] Update import_albums to store spotify_url from Google Sheets without fetching metadata in catalog/management/commands/import_albums.py
- [ ] T054 [US2] Update import_albums to set spotify_cover_url=None and spotify_metadata_json=None during import in catalog/management/commands/import_albums.py
- [ ] T055 [US2] Add logging message indicating Spotify API calls were skipped in catalog/management/commands/import_albums.py
- [ ] T056 [US2] Update import_albums command help text to explain --skip-spotify flag in catalog/management/commands/import_albums.py
- [ ] T057 [US2] Add --no-skip-spotify flag option for backward compatibility (pre-populate cache) in catalog/management/commands/import_albums.py
- [ ] T058 [US2] Update Google Sheets parser to extract spotify_url column in catalog/services/google_sheets.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - fast imports + lazy loading

---

## Phase 5: User Story 3 - View Album Detail Page with Full Metadata (Priority: P3)

**Goal**: Users can view detailed album information (track listing, genres, popularity) fetched on-demand when clicking an album tile.

**Independent Test**: Click album tile, verify detail page loads with basic info, confirm full metadata (tracks, genres) appears immediately after page load, reload page to verify cached metadata (instant display).

### Tests for User Story 3 ⚠️

- [ ] T059 [P] [US3] Contract test for GET /catalog/album/<id>/metadata/ endpoint in tests/contract/test_spotify_endpoints.py
- [ ] T060 [P] [US3] Contract test verifying HTML response format with track listing in tests/contract/test_spotify_endpoints.py
- [ ] T061 [P] [US3] Contract test verifying JSON response format with metadata structure in tests/contract/test_spotify_endpoints.py
- [ ] T062 [P] [US3] Integration test for metadata loading on album detail page in tests/integration/test_lazy_loading.py
- [ ] T063 [P] [US3] Integration test for metadata cache hit scenario in tests/integration/test_lazy_loading.py
- [ ] T064 [P] [US3] Unit test for cache_metadata() with JSON serialization in tests/unit/test_album_cache.py

### Implementation for User Story 3

- [ ] T065 [US3] Create album_metadata view function in catalog/views.py
- [ ] T066 [US3] Implement cache check logic in album_metadata view using get_cached_metadata()
- [ ] T067 [US3] Implement Spotify API fetch logic in album_metadata view using fetch_album_metadata()
- [ ] T068 [US3] Implement cache update logic in album_metadata view using cache_metadata()
- [ ] T069 [US3] Add error handling for missing metadata (return message about unavailable details) in album_metadata view
- [ ] T070 [US3] Add HTML response rendering with track listing, genres, popularity in album_metadata view
- [ ] T071 [US3] Add JSON response format support for metadata in album_metadata view
- [ ] T072 [US3] Add URL route for /catalog/album/<int:album_id>/metadata/ in catalog/urls.py
- [ ] T073 [US3] Update album_detail.html template to render basic info from database in catalog/templates/catalog/album_detail.html
- [ ] T074 [US3] Add HTMX hx-get attribute with /catalog/album/{id}/metadata/ in catalog/templates/catalog/album_detail.html
- [ ] T075 [US3] Add HTMX hx-trigger="load" attribute to metadata container in catalog/templates/catalog/album_detail.html
- [ ] T076 [US3] Add loading spinner placeholder for metadata section in catalog/templates/catalog/album_detail.html
- [ ] T077 [US3] Create metadata display component with track listing HTML in catalog/templates/catalog/components/ or album_detail.html
- [ ] T078 [US3] Add genres badge display using DaisyUI in metadata component
- [ ] T079 [US3] Add popularity score display in metadata component

**Checkpoint**: All user stories should now be independently functional - catalog, import, and detail page all working

---

## Phase 6: Admin Features - Cache Refresh Command

**Purpose**: Administrative tools for manual cache management

- [ ] T080 Create refresh_spotify_cache management command file in catalog/management/commands/refresh_spotify_cache.py
- [ ] T081 Add --album-id argument for refreshing specific album in refresh_spotify_cache command
- [ ] T082 Add --artist argument for refreshing albums by artist name in refresh_spotify_cache command
- [ ] T083 Add --genre argument for refreshing albums by genre in refresh_spotify_cache command
- [ ] T084 Add --dry-run flag for preview mode in refresh_spotify_cache command
- [ ] T085 Implement album filtering logic based on command arguments in refresh_spotify_cache command
- [ ] T086 Implement progress bar display using tqdm or Django progress output in refresh_spotify_cache command
- [ ] T087 Implement rate limit handling with exponential backoff in refresh_spotify_cache command
- [ ] T088 Add logging for failed refreshes with album details in refresh_spotify_cache command
- [ ] T089 Add summary output showing success/failure counts in refresh_spotify_cache command
- [ ] T090 Update command help text with usage examples in refresh_spotify_cache command

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T091 [P] Add type annotations to all functions in catalog/services/album_cache.py (pyright strict mode)
- [ ] T092 [P] Add type annotations to all functions in catalog/services/spotify_client.py (pyright strict mode)
- [ ] T093 [P] Add docstrings to all functions in catalog/services/album_cache.py
- [ ] T094 [P] Add docstrings to all functions in catalog/services/spotify_client.py
- [ ] T095 [P] Add docstrings to view functions in catalog/views.py (album_cover_art, album_metadata)
- [ ] T096 [P] Run ruff check and fix any linting issues in catalog/
- [ ] T097 [P] Run ruff format to ensure consistent formatting in catalog/
- [ ] T098 [P] Run pyright and resolve any type errors in catalog/
- [ ] T099 [P] Add error logging for all Spotify API failures in catalog/services/spotify_client.py
- [ ] T100 [P] Add performance logging for cache hit/miss rates in catalog/services/album_cache.py
- [ ] T101 Update quickstart.md with actual command outputs and verification steps in specs/006-jit-spotify-api/quickstart.md
- [ ] T102 Verify all tests pass (pytest)
- [ ] T103 Run import performance benchmark and document results
- [ ] T104 Measure cache hit rate after browsing and document results
- [ ] T105 Validate success criteria from spec.md (50%+ import speedup, 80%+ API call reduction)
- [ ] T106 Update CLAUDE.md with feature usage notes in CLAUDE.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Admin Features (Phase 6)**: Depends on Foundational phase, can proceed in parallel with user stories
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 but integrates when both complete
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2 but uses same cache infrastructure

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Views depend on services being implemented first
- Templates depend on views and URL routes being ready
- Integration with existing code happens after core functionality works

### Parallel Opportunities

- Phase 1 tasks T002-T007 (model field additions) can run in parallel
- Phase 2 tasks T011-T015 (cache service functions) can run in parallel
- Phase 2 tasks T016-T019 (Spotify client enhancements) can run in parallel
- All test tasks within each user story can run in parallel (marked [P])
- User Stories 1, 2, 3 can all be developed in parallel after Foundational phase
- All Polish tasks (T091-T101) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T020: "Contract test for GET /catalog/album/<id>/cover-art/ endpoint in tests/contract/test_spotify_endpoints.py"
Task T021: "Contract test verifying HTML response format with <img> tag in tests/contract/test_spotify_endpoints.py"
Task T022: "Contract test verifying JSON response format with cover_url field in tests/contract/test_spotify_endpoints.py"
Task T023: "Contract test for error responses (404, 429, 500) in tests/contract/test_spotify_endpoints.py"
Task T024: "Integration test for lazy cover art loading on catalog page in tests/integration/test_lazy_loading.py"
Task T025: "Integration test for cache hit scenario (second page load) in tests/integration/test_lazy_loading.py"
Task T026: "Integration test for placeholder display on API error in tests/integration/test_lazy_loading.py"
Task T027: "Unit test for extract_spotify_album_id() with valid URLs in tests/unit/test_album_cache.py"
Task T028: "Unit test for extract_spotify_album_id() with invalid URLs in tests/unit/test_album_cache.py"
Task T029: "Unit test for cache_cover_url() with concurrent requests in tests/unit/test_album_cache.py"

# After tests written and failing, launch parallel implementation tasks:
# (Templates and view logic can proceed in parallel since they're different files)
Task T040: "Update album_list.html template to render skeleton placeholders initially"
Task T041: "Add HTMX hx-get attribute with /catalog/album/{id}/cover-art/"
Task T042: "Add HTMX hx-trigger='intersect once' attribute to album tile figure"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task T047: "Integration test for import_albums command without Spotify calls"
Task T048: "Integration test verifying albums have spotify_url but no spotify_cover_url after import"
Task T049: "Integration test for import completion when Spotify API unavailable"
Task T050: "Integration test measuring import performance (baseline vs optimized)"
Task T051: "Unit test for Spotify URL extraction from Google Sheets data"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (database schema changes)
2. Complete Phase 2: Foundational (cache service + Spotify client enhancements)
3. Complete Phase 3: User Story 1 (catalog with lazy loading)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Load catalog → see placeholders
   - Scroll → see cover art load
   - Reload → see instant cache hits
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (Tasks T001-T019)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! Tasks T020-T046)
3. Add User Story 2 → Test independently → Deploy/Demo (Fast imports! Tasks T047-T058)
4. Add User Story 3 → Test independently → Deploy/Demo (Rich metadata! Tasks T059-T079)
5. Add Admin Features → Cache management ready (Tasks T080-T090)
6. Polish → Production ready (Tasks T091-T106)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Tasks T001-T019)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (Tasks T020-T046)
   - **Developer B**: User Story 2 (Tasks T047-T058)
   - **Developer C**: User Story 3 (Tasks T059-T079)
   - **Developer D**: Admin Features (Tasks T080-T090)
3. Stories complete and integrate independently
4. Team reconvenes for Polish phase (Tasks T091-T106)

---

## Notes

- **[P] tasks**: Different files, no dependencies - safe to parallelize
- **[Story] label**: Maps task to specific user story for traceability
- **Test-first approach**: All tests must be written and fail before implementation begins
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Type safety**: All code must pass pyright strict mode (no `Any` types without justification)
- **Code quality**: All code must pass ruff check and ruff format before commit
- **Documentation**: All functions must have docstrings explaining purpose, parameters, and return values

### Success Validation Checklist

After completing all tasks, verify these success criteria from spec.md:

- [ ] **SC-001**: Import process completes without Spotify API calls (check logs)
- [ ] **SC-001**: Import time reduced by 50%+ vs eager loading (benchmark results)
- [ ] **SC-002**: Cover art appears within 1 second of viewport visibility (manual test)
- [ ] **SC-003**: Cached cover art shows instantly on second page load (manual test)
- [ ] **SC-004**: Rate limit errors show placeholder, not user-facing errors (manual test)
- [ ] **SC-005**: 95%+ cover art requests succeed when API available (monitoring logs)
- [ ] **SC-006**: Total API calls reduced by 80%+ (compare before/after metrics)

### Performance Benchmarks to Document

- Import time: 500 albums (before vs after)
- Cache hit rate: After 100 albums viewed
- API call count: Full browsing session
- Time to first cover art: Catalog page load
