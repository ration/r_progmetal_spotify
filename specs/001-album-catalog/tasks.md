# Tasks: Album Catalog Visualization

**Input**: Design documents from `/specs/001-album-catalog/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD is REQUIRED per Constitution Principle II. All tests written before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Daily Sync Requirement**: Implement automated daily synchronization from Google Sheets (https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/edit?gid=803985331)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project uses Django structure with `catalog/` app:
- Models: `catalog/models.py`
- Views: `catalog/views.py`
- Templates: `catalog/templates/catalog/`
- Services: `catalog/services/`
- Management commands: `catalog/management/commands/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/contract/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [X] T001 Add spotipy dependency to pyproject.toml (spotipy~=2.24.0)
- [X] T002 Run uv sync to install dependencies
- [X] T003 Create .env.example file with required environment variables (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, GOOGLE_SHEETS_CSV_URL)
- [X] T004 [P] Create placeholder album cover image in catalog/static/catalog/images/placeholder-album.png
- [X] T005 [P] Create CSS file for album catalog styles in catalog/static/catalog/css/album-catalog.css

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Models & Migrations

- [X] T006 [P] Create Artist model in catalog/models.py with fields: name, country, spotify_artist_id
- [X] T007 [P] Create Genre model in catalog/models.py with fields: name, slug
- [X] T008 [P] Create VocalStyle model in catalog/models.py with fields: name, slug
- [X] T009 Create Album model in catalog/models.py with fields: spotify_album_id, name, artist (FK), genre (FK), vocal_style (FK), release_date, cover_art_url, spotify_url, imported_at, updated_at
- [X] T010 Add model validation methods to Album model (clean() for spotify URL and ID validation)
- [X] T011 Create initial migration for catalog models (makemigrations catalog)
- [X] T012 Create data migration to seed Genre table with 8 progressive metal subgenres
- [X] T013 Create data migration to seed VocalStyle table with 4 vocal style options
- [X] T014 Run migrations (migrate catalog)

### Data Import Infrastructure

- [X] T015 Create catalog/services/ directory for data fetching logic
- [X] T016 [P] Create GoogleSheetsService in catalog/services/google_sheets.py to fetch CSV from export URL
- [X] T017 [P] Create SpotifyClient in catalog/services/spotify_client.py using spotipy library with Client Credentials auth
- [X] T018 Create AlbumImporter in catalog/services/album_importer.py to orchestrate CSV parsing and Spotify API calls
- [X] T019 Create Django management command import_albums in catalog/management/commands/import_albums.py
- [ ] T020 [P] Create Django management command sync_spotify in catalog/management/commands/sync_spotify.py for re-syncing existing albums

### Configuration

- [X] T021 Add Spotify API settings to config/settings.py (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET from env vars)
- [X] T022 Add Google Sheets CSV URL to config/settings.py (GOOGLE_SHEETS_CSV_URL from env var)
- [X] T023 Configure logging for Spotify API calls and data imports in config/settings.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Browse Album Catalog (Priority: P1) 🎯 MVP

**Goal**: Display album tiles in responsive grid layout with cover art, artist, album name, release date, genre, country, and vocal style

**Independent Test**: Load /catalog/albums/ and verify tiles display with all required fields, sorted by newest first, responsive grid layout

### Tests for User Story 1 (TDD - Write FIRST)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T024 [P] [US1] Unit test for Album model __str__ method in tests/unit/test_album_model.py
- [ ] T025 [P] [US1] Unit test for Album.get_cover_art_or_placeholder() method in tests/unit/test_album_model.py
- [ ] T026 [P] [US1] Unit test for Album.formatted_release_date() method in tests/unit/test_album_model.py
- [ ] T027 [P] [US1] Integration test for album_list view rendering in tests/integration/test_album_views.py
- [ ] T028 [P] [US1] Integration test for album tile display with all fields in tests/integration/test_album_views.py
- [ ] T029 [P] [US1] Integration test for responsive grid layout CSS in tests/integration/test_templates.py
- [ ] T030 [P] [US1] Contract test for Google Sheets CSV parsing in tests/contract/test_google_sheets.py
- [ ] T031 [P] [US1] Contract test for Spotify API album fetch in tests/contract/test_spotify_api.py

### Implementation for User Story 1

- [X] T032 [P] [US1] Create base template catalog/templates/catalog/base.html extending project base with HTMX script
- [X] T033 [US1] Create album_list view in catalog/views.py that queries Album.objects with select_related for artist, genre, vocal_style, ordered by -release_date
- [X] T034 [US1] Create URL pattern for album_list in catalog/urls.py mapped to / route
- [X] T035 [US1] Create album_list.html template in catalog/templates/catalog/ with grid container
- [X] T036 [US1] Create album_list_tiles.html fragment template in catalog/templates/catalog/ for HTMX partial updates
- [X] T037 [US1] Create album_tile.html component in catalog/templates/catalog/components/ displaying cover, name, artist, date, genre, country, vocal
- [X] T038 [US1] Implement responsive grid CSS in catalog/static/catalog/css/album-catalog.css (1-2 cols mobile, 2-3 tablet, 3-4 desktop)
- [X] T039 [US1] Add logic to album_list view to detect HX-Request header and return fragment vs full page
- [X] T040 [US1] Add placeholder image fallback logic to album_tile template

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run tests, verify all pass, commit atomically.

---

## Phase 4: User Story 2 - View Album Details (Priority: P2)

**Goal**: Click album tile to view detailed album information with high-res cover art and link to Spotify

**Independent Test**: Click any album tile, verify detail page shows, displays all fields prominently, has back button, shows high-res cover

### Tests for User Story 2 (TDD - Write FIRST)

- [ ] T041 [P] [US2] Integration test for album_detail view rendering in tests/integration/test_album_views.py
- [ ] T042 [P] [US2] Integration test for album_detail displays all fields in tests/integration/test_album_views.py
- [ ] T043 [P] [US2] Integration test for back button navigation in tests/integration/test_album_views.py
- [ ] T044 [P] [US2] Integration test for Spotify link opens in new tab in tests/integration/test_album_views.py

### Implementation for User Story 2

- [ ] T045 [P] [US2] Create album_detail view in catalog/views.py using get_object_or_404 with select_related
- [ ] T046 [US2] Create URL pattern for album_detail in catalog/urls.py mapped to /<int:id>/ route
- [ ] T047 [US2] Create album_detail.html template in catalog/templates/catalog/ with two-column layout (cover + details)
- [ ] T048 [US2] Add HTMX attributes to album_tile for navigation (hx-get to detail URL, hx-target body, hx-push-url true)
- [ ] T049 [US2] Style album detail page with large cover image and organized metadata grid
- [ ] T050 [US2] Add Spotify external link button with target="_blank" and visual styling

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can browse and view details.

---

## Phase 5: User Story 3 - Filter by Genre (Priority: P3)

**Goal**: Add genre dropdown filter that updates album tiles via HTMX without full page reload

**Independent Test**: Select genre from dropdown, verify only matching albums display, clear filter returns all albums

### Tests for User Story 3 (TDD - Write FIRST)

- [ ] T051 [P] [US3] Integration test for genre filter query parameter in tests/integration/test_filters.py
- [ ] T052 [P] [US3] Integration test for HTMX fragment response with HX-Request header in tests/integration/test_filters.py
- [ ] T053 [P] [US3] Integration test for filter clears all albums display in tests/integration/test_filters.py
- [ ] T054 [P] [US3] Integration test for no results message when no albums match filter in tests/integration/test_filters.py

### Implementation for User Story 3

- [ ] T055 [P] [US3] Add genre filter logic to album_list view checking request.GET.get('genre')
- [ ] T056 [P] [US3] Create filters.html component in catalog/templates/catalog/components/ with genre dropdown
- [ ] T057 [US3] Add HTMX attributes to genre select (hx-get to album_list URL, hx-target #album-tiles, hx-push-url true)
- [ ] T058 [US3] Include filters component in album_list.html template above tiles container
- [ ] T059 [US3] Add "Clear Filters" button with HTMX to reset to unfiltered view
- [ ] T060 [US3] Add visual indicator for active filter state in UI
- [ ] T061 [US3] Add empty state message in album_list_tiles template when no albums match filter

**Checkpoint**: Genre filtering works independently, can be tested without vocal style filtering

---

## Phase 6: User Story 4 - Filter by Vocal Style (Priority: P3)

**Goal**: Add vocal style dropdown filter that works independently or combined with genre filter

**Independent Test**: Select vocal style filter, verify only matching albums display, combine with genre filter, verify AND logic

### Tests for User Story 4 (TDD - Write FIRST)

- [ ] T062 [P] [US4] Integration test for vocal style filter query parameter in tests/integration/test_filters.py
- [ ] T063 [P] [US4] Integration test for combined genre AND vocal style filters in tests/integration/test_filters.py
- [ ] T064 [P] [US4] Integration test for filter state preservation in URL in tests/integration/test_filters.py

### Implementation for User Story 4

- [ ] T065 [P] [US4] Add vocal style filter logic to album_list view checking request.GET.get('vocal')
- [ ] T066 [US4] Add vocal style dropdown to filters.html component
- [ ] T067 [US4] Add HTMX attributes to vocal style select (same pattern as genre)
- [ ] T068 [US4] Update filter logic in album_list view to support multiple filters with Q objects
- [ ] T069 [US4] Update "Clear Filters" button to remove both filter parameters
- [ ] T070 [US4] Update filter state indicator to show both active filters

**Checkpoint**: All user stories complete and independently functional

---

## Phase 7: Daily Synchronization (Additional Requirement)

**Goal**: Implement automated daily synchronization from Google Sheets

**Independent Test**: Run sync command manually, verify updates existing albums and adds new ones, check logs for import statistics

### Tests for Daily Sync

- [ ] T071 [P] Unit test for AlbumImporter.sync() method to update existing albums in tests/unit/test_album_importer.py
- [ ] T072 [P] Unit test for AlbumImporter handles new albums in CSV in tests/unit/test_album_importer.py
- [ ] T073 [P] Unit test for AlbumImporter handles removed albums gracefully in tests/unit/test_album_importer.py
- [ ] T074 [P] Integration test for import_albums command output and logging in tests/integration/test_management_commands.py

### Implementation for Daily Sync

- [ ] T075 Add upsert logic to AlbumImporter to update existing albums by spotify_album_id
- [ ] T076 Add logging to AlbumImporter for sync statistics (created, updated, errors)
- [ ] T077 Add --force flag to import_albums command to re-fetch all albums from Spotify API
- [ ] T078 Add error handling and retry logic with exponential backoff for Spotify API failures
- [ ] T079 Create systemd timer unit file for daily sync in docs/deployment/progmetal-sync.timer
- [ ] T080 Create systemd service unit file in docs/deployment/progmetal-sync.service
- [ ] T081 Document cron alternative in specs/001-album-catalog/quickstart.md

**Checkpoint**: Daily sync can be scheduled, manual testing confirms data updates

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T082 [P] Add docstrings to all models in catalog/models.py (NumPy/Google style)
- [ ] T083 [P] Add docstrings to all views in catalog/views.py
- [ ] T084 [P] Add docstrings to all service classes in catalog/services/
- [ ] T085 [P] Add inline comments for CSV parsing logic in AlbumImporter
- [ ] T086 [P] Add inline comments for Spotify API error handling
- [ ] T087 Update README.md with Spotify API setup instructions and Google Sheets configuration
- [ ] T088 Update CLAUDE.md with import command examples (already done, verify completeness)
- [ ] T089 Add Django Debug Toolbar configuration for development environment
- [ ] T090 Run ruff check and fix any linting issues
- [ ] T091 Run ruff format to ensure consistent code formatting
- [ ] T092 Run pyright and fix any type checking errors
- [ ] T093 Run pytest with coverage report (pytest --cov=catalog --cov-report=html)
- [ ] T094 Verify coverage >= 80% per constitution requirement
- [ ] T095 Run quickstart.md validation (follow setup steps, verify application works)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P3)
- **Daily Sync (Phase 7)**: Depends on Foundational phase (uses AlbumImporter)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories (independent)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories (independent)
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories (independent, but naturally extends US3)
- **Daily Sync (Phase 7)**: Can start after Foundational (Phase 2) - Uses same infrastructure as US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD requirement)
- Models before services (T006-009 before T015-018)
- Services before views (T015-020 before T033)
- Views before templates (T033 before T035-037)
- Templates before CSS styling (T035-037 before T038)
- Core implementation before integration (T032-040 in order)

### Parallel Opportunities

- **Setup (Phase 1)**: T001-T005 can all run in parallel
- **Foundational (Phase 2)**:
  - T006-T008 (models) can run in parallel
  - T016-T017 (services) can run in parallel after models
- **User Story 1 Tests**: T024-T031 can all run in parallel (all are test files)
- **User Story 1 Implementation**: T032, T040 can run in parallel (different concerns)
- **User Story 2 Tests**: T041-T044 can all run in parallel
- **User Story 2 Implementation**: T045, T047 can run in parallel initially
- **User Story 3 Tests**: T051-T054 can all run in parallel
- **User Story 3 Implementation**: T055-T056 can run in parallel
- **User Story 4 Tests**: T062-T064 can all run in parallel
- **User Story 4 Implementation**: T065-T066 can run in parallel
- **Daily Sync Tests**: T071-T074 can all run in parallel
- **Polish**: T082-T086 (documentation) can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - write these first):
- T024: Unit test Album __str__
- T025: Unit test get_cover_art_or_placeholder()
- T026: Unit test formatted_release_date()
- T027: Integration test album_list view
- T028: Integration test tile display
- T029: Integration test responsive CSS
- T030: Contract test CSV parsing
- T031: Contract test Spotify API

# After tests fail, launch parallelizable implementation tasks:
- T032: Create base template
- T040: Add placeholder fallback logic

# Then sequential implementation:
- T033: Create album_list view (needs models from Phase 2)
- T034: Create URL pattern
- T035: Create album_list.html
- T036: Create album_list_tiles.html fragment
- T037: Create album_tile component
- T038: Implement responsive CSS
- T039: Add HTMX detection logic
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T023) - CRITICAL
3. Complete Phase 3: User Story 1 (T024-T040)
4. **STOP and VALIDATE**:
   - Run tests: `pytest tests/unit/ tests/integration/test_album_views.py tests/contract/`
   - Manual test: Load /catalog/albums/, verify tiles display
   - Import data: `python manage.py import_albums`
   - Verify responsive layout at different screen sizes
5. **Commit atomically**: Follow constitution's atomic commits policy
   - Commit 1: Tests (T024-T031)
   - Commit 2: Models and infrastructure (Phase 2)
   - Commit 3: Views and templates (T032-T040)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Commit → **MVP DEPLOYED**
3. Add User Story 2 → Test independently → Commit → Deploy
4. Add User Story 3 → Test independently → Commit → Deploy
5. Add User Story 4 → Test independently → Commit → Deploy
6. Add Daily Sync → Test independently → Commit → Deploy
7. Polish → Final commit → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T023)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T024-T040) - MVP priority
   - **Developer B**: User Story 2 (T041-T050) - Can start immediately after Foundational
   - **Developer C**: Daily Sync infrastructure (T071-T081) - Can start immediately after Foundational
3. After US1-2 complete:
   - **Developer A**: User Story 3 (T051-T061)
   - **Developer B**: User Story 4 (T062-T070)
4. All developers: Polish phase together (T082-T095)

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- **Each user story is independently completable and testable**
- **TDD REQUIRED**: Verify tests fail (red) before implementing (green), then refactor
- **Commit after each user story phase** or logical atomic group
- **Stop at any checkpoint** to validate story independently
- **Constitution compliance**: All tests must pass, linting clean, type checking pass before commit
- **Daily sync** is implemented as Phase 7 and can be developed in parallel with user stories 3-4
- **Spotify API rate limiting**: Import script includes exponential backoff, may take 5-10 minutes for 100+ albums

---

## Task Count Summary

- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 18 tasks
- **Phase 3 (User Story 1 - P1)**: 17 tasks (8 tests + 9 implementation)
- **Phase 4 (User Story 2 - P2)**: 10 tasks (4 tests + 6 implementation)
- **Phase 5 (User Story 3 - P3)**: 11 tasks (4 tests + 7 implementation)
- **Phase 6 (User Story 4 - P3)**: 10 tasks (3 tests + 7 implementation)
- **Phase 7 (Daily Sync)**: 11 tasks (4 tests + 7 implementation)
- **Phase 8 (Polish)**: 14 tasks

**Total**: 96 tasks

**MVP Scope (Recommended)**: Phase 1 + Phase 2 + Phase 3 = 40 tasks (Setup + Foundational + Browse Catalog)
