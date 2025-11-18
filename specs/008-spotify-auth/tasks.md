# Tasks: Spotify Authentication

**Input**: Design documents from `/specs/008-spotify-auth/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-endpoints.md, quickstart.md

**Tests**: Contract tests and integration tests explicitly requested in spec - test tasks included with TDD approach (tests first, must fail before implementation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a Django web application. File paths are relative to repository root:
- `catalog/` - Django app for album catalog (authentication extends this)
- `catalog/services/` - Service layer for business logic
- `catalog/templates/catalog/` - Template files
- `config/` - Django project configuration
- `tests/` - Test files (contract, integration, unit)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: External setup and environment configuration before implementation

- [ ] T001 Register application at Spotify Developer Dashboard (https://developer.spotify.com/dashboard)
- [ ] T002 Configure Spotify redirect URIs (dev: http://localhost:9000/catalog/auth/callback/, prod: https://yourdomain.com/catalog/auth/callback/)
- [ ] T003 Add environment variables to .env file (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)
- [ ] T004 [P] Verify Python 3.14 and Django 5.2.8 environment is active
- [ ] T005 [P] Add requests library to dependencies if not present (likely already included via spotipy)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create User model in catalog/models.py with fields: spotify_user_id (unique), email, display_name, profile_picture_url, is_admin (boolean, default False), created_at, updated_at
- [ ] T007 Add type annotations and docstring to User model following project standards
- [ ] T008 Create SpotifyToken model in catalog/models.py with fields: user (OneToOneField), access_token, refresh_token, expires_at, created_at, updated_at
- [ ] T009 Add expires_soon() method to SpotifyToken model (returns True if expires_at < now + 5 minutes)
- [ ] T010 Add refresh() method to SpotifyToken model to update tokens atomically
- [ ] T011 Add type annotations and docstring to SpotifyToken model following project standards
- [ ] T012 Create and run migrations: python manage.py makemigrations catalog
- [ ] T013 Apply migrations: python manage.py migrate catalog
- [ ] T014 Create catalog/services/ directory if it doesn't exist
- [ ] T015 Create SpotifyAuthService class in catalog/services/spotify_auth.py with OAuth utility methods
- [ ] T016 Implement generate_auth_url() method in SpotifyAuthService
- [ ] T017 Implement exchange_code_for_tokens() method in SpotifyAuthService
- [ ] T018 Implement fetch_user_profile() method in SpotifyAuthService
- [ ] T019 Implement refresh_access_token() method in SpotifyAuthService
- [ ] T020 Implement create_or_update_user() method in SpotifyAuthService (includes first-user-is-admin logic)
- [ ] T021 Add type annotations and docstrings to all SpotifyAuthService methods
- [ ] T022 Create RefreshTokenExpiredError exception class in catalog/services/spotify_auth.py
- [ ] T023 Create global spotify_auth_service instance in catalog/services/spotify_auth.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Login with Spotify Account (Priority: P1) 🎯 MVP

**Goal**: Users can log into the application using their Spotify account, with OAuth flow, session management, and logout functionality.

**Independent Test**: Click "Login with Spotify" button, complete Spotify OAuth flow, land back in application as authenticated user, verify access to protected pages, then logout successfully.

### Tests for User Story 1 (TDD Approach)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T024 [P] [US1] Create contract test file tests/contract/test_spotify_oauth_flow.py
- [ ] T025 [P] [US1] Write contract test: test_login_page_renders() - Verify login page loads with "Login with Spotify" button
- [ ] T026 [P] [US1] Write contract test: test_oauth_flow_initiates() - Verify OAuth redirect to Spotify with correct parameters
- [ ] T027 [P] [US1] Write contract test: test_oauth_callback_invalid_state() - Verify state parameter validation (CSRF protection)
- [ ] T028 [P] [US1] Write contract test: test_oauth_callback_user_denied() - Verify error handling when user denies authorization
- [ ] T029 [P] [US1] Write contract test: test_logout_clears_session() - Verify logout removes session and redirects to login
- [ ] T030 [P] [US1] Create integration test file tests/integration/test_user_authentication.py
- [ ] T031 [P] [US1] Write integration test: test_complete_login_flow() - End-to-end login journey from login page to authenticated state
- [ ] T032 [P] [US1] Write integration test: test_protected_route_redirects_unauthenticated() - Verify middleware protects catalog pages
- [ ] T033 [P] [US1] Run tests and verify they fail (expected before implementation): pytest tests/contract/test_spotify_oauth_flow.py tests/integration/test_user_authentication.py

### Implementation for User Story 1

- [ ] T034 [P] [US1] Create login template at catalog/templates/catalog/login.html with "Login with Spotify" button
- [ ] T035 [P] [US1] Add login_page view in catalog/views.py to render login template
- [ ] T036 [US1] Add spotify_oauth_initiate view in catalog/views.py to generate state, store in session, redirect to Spotify
- [ ] T037 [US1] Add spotify_oauth_callback view in catalog/views.py to handle OAuth callback, validate state, exchange code for tokens, create/update user, set session
- [ ] T038 [US1] Add logout_view in catalog/views.py to clear session and redirect to login (@require_http_methods(["POST"]))
- [ ] T039 [US1] Add type annotations and docstrings to all new views following project standards
- [ ] T040 [US1] Add URL patterns to catalog/urls.py: auth/login/, auth/spotify/, auth/callback/, auth/logout/
- [ ] T041 [US1] Create catalog/middleware.py file
- [ ] T042 [US1] Implement AuthenticationMiddleware in catalog/middleware.py to load user from session
- [ ] T043 [US1] Add route protection logic to AuthenticationMiddleware (redirect unauthenticated users to login for non-public paths)
- [ ] T044 [US1] Add type annotations and docstrings to AuthenticationMiddleware
- [ ] T045 [US1] Register AuthenticationMiddleware in config/settings.py MIDDLEWARE list (after SessionMiddleware)
- [ ] T046 [US1] Update catalog/templates/catalog/base.html navigation to show login link when logged out
- [ ] T047 [US1] Run contract tests and verify they pass: pytest tests/contract/test_spotify_oauth_flow.py
- [ ] T048 [US1] Run integration tests and verify they pass: pytest tests/integration/test_user_authentication.py
- [ ] T049 [US1] Manual test: Navigate to /catalog/auth/login/ and verify page renders
- [ ] T050 [US1] Manual test: Click "Login with Spotify" and verify redirect to Spotify authorization
- [ ] T051 [US1] Manual test: Grant permission and verify redirect back to application as logged-in user
- [ ] T052 [US1] Manual test: Verify access to /catalog/ page works after login
- [ ] T053 [US1] Manual test: Logout and verify redirect to login page
- [ ] T054 [US1] Manual test: Verify /catalog/ redirects to login when logged out

**Checkpoint**: At this point, User Story 1 should be fully functional - complete OAuth login flow with session management

---

## Phase 4: User Story 2 - View Connected Spotify Profile (Priority: P2)

**Goal**: Users can view their Spotify profile information including display name, email, and profile picture.

**Independent Test**: After logging in with Spotify, navigate to profile page and verify Spotify username, email, and profile picture are displayed correctly.

### Tests for User Story 2 (TDD Approach)

- [ ] T055 [P] [US2] Write contract test: test_profile_page_displays_user_info() in tests/contract/test_spotify_oauth_flow.py - Verify profile page shows Spotify display name, email, profile picture
- [ ] T056 [P] [US2] Write contract test: test_profile_page_redirects_unauthenticated() in tests/contract/test_spotify_oauth_flow.py - Verify profile page requires authentication
- [ ] T057 [P] [US2] Write integration test: test_profile_display_after_login() in tests/integration/test_user_authentication.py - End-to-end login → profile view
- [ ] T058 [P] [US2] Run tests and verify they fail (expected before implementation): pytest tests/contract/test_spotify_oauth_flow.py::test_profile_page_displays_user_info tests/integration/test_user_authentication.py::test_profile_display_after_login

### Implementation for User Story 2

- [ ] T059 [P] [US2] Create profile template at catalog/templates/catalog/profile.html to display user's Spotify info (display name, email, profile picture, is_admin badge)
- [ ] T060 [US2] Add profile_page view in catalog/views.py to render profile template (requires authentication)
- [ ] T061 [US2] Add type annotations and docstring to profile_page view
- [ ] T062 [US2] Add URL pattern to catalog/urls.py: auth/profile/
- [ ] T063 [US2] Update catalog/templates/catalog/base.html navigation to show user dropdown with display name, profile picture, and "Profile" link
- [ ] T064 [US2] Add "Admin" link to dropdown if user.is_admin is True
- [ ] T065 [US2] Run contract tests and verify they pass: pytest tests/contract/test_spotify_oauth_flow.py
- [ ] T066 [US2] Run integration tests and verify they pass: pytest tests/integration/test_user_authentication.py
- [ ] T067 [US2] Manual test: Navigate to /catalog/auth/profile/ and verify profile displays correctly
- [ ] T068 [US2] Manual test: Verify navbar shows display name/profile picture after login
- [ ] T069 [US2] Manual test: Verify admin badge shows on profile page for first user

**Checkpoint**: At this point, User Stories 1 AND 2 should work - login + profile viewing

---

## Phase 5: User Story 3 - Disconnect Spotify Account (Priority: P2)

**Goal**: Users can disconnect their Spotify account, which deletes tokens and logs them out.

**Independent Test**: While logged in, navigate to profile page, click "Disconnect Spotify", verify user is logged out and tokens are deleted.

### Tests for User Story 3 (TDD Approach)

- [ ] T070 [P] [US3] Write contract test: test_disconnect_deletes_token_and_logs_out() in tests/contract/test_spotify_oauth_flow.py - Verify disconnect removes SpotifyToken and ends session
- [ ] T071 [P] [US3] Write contract test: test_disconnect_requires_authentication() in tests/contract/test_spotify_oauth_flow.py - Verify disconnect endpoint requires authentication
- [ ] T072 [P] [US3] Write integration test: test_disconnect_flow() in tests/integration/test_user_authentication.py - Login → disconnect → verify logged out
- [ ] T073 [P] [US3] Run tests and verify they fail (expected before implementation): pytest tests/contract/test_spotify_oauth_flow.py::test_disconnect_deletes_token tests/integration/test_user_authentication.py::test_disconnect_flow

### Implementation for User Story 3

- [ ] T074 [US3] Add disconnect_spotify view in catalog/views.py to delete SpotifyToken and flush session (@require_http_methods(["POST"]))
- [ ] T075 [US3] Add type annotations and docstring to disconnect_spotify view
- [ ] T076 [US3] Add URL pattern to catalog/urls.py: auth/disconnect/
- [ ] T077 [US3] Add "Disconnect Spotify" button to profile template (catalog/templates/catalog/profile.html) with POST form
- [ ] T078 [US3] Run contract tests and verify they pass: pytest tests/contract/test_spotify_oauth_flow.py
- [ ] T079 [US3] Run integration tests and verify they pass: pytest tests/integration/test_user_authentication.py
- [ ] T080 [US3] Manual test: Click "Disconnect Spotify" on profile page and verify logout
- [ ] T081 [US3] Manual test: Verify SpotifyToken deleted from database after disconnect
- [ ] T082 [US3] Manual test: Verify redirect to login page with disconnected message

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should work - full account lifecycle

---

## Phase 6: User Story 4 - Automatic Token Refresh (Priority: P3)

**Goal**: Application automatically refreshes expired Spotify access tokens in the background without user awareness.

**Independent Test**: Log in with Spotify, wait for access token to expire (or mock expiry), make a request, verify token is automatically refreshed without user intervention.

### Tests for User Story 4 (TDD Approach)

- [ ] T083 [P] [US4] Create unit test file tests/unit/test_spotify_auth_service.py
- [ ] T084 [P] [US4] Write unit test: test_refresh_token_success() in tests/unit/test_spotify_auth_service.py - Verify SpotifyAuthService.refresh_access_token() works
- [ ] T085 [P] [US4] Write unit test: test_refresh_token_expired_raises_error() in tests/unit/test_spotify_auth_service.py - Verify RefreshTokenExpiredError raised on 400 response
- [ ] T086 [P] [US4] Write integration test: test_automatic_token_refresh() in tests/integration/test_user_authentication.py - Mock token expiry, make request, verify refresh happens
- [ ] T087 [P] [US4] Write integration test: test_expired_refresh_token_logs_out() in tests/integration/test_user_authentication.py - Mock refresh failure, verify logout
- [ ] T088 [P] [US4] Run tests and verify they fail (expected before implementation): pytest tests/unit/test_spotify_auth_service.py tests/integration/test_user_authentication.py::test_automatic_token_refresh

### Implementation for User Story 4

- [ ] T089 [US4] Implement TokenRefreshMiddleware in catalog/middleware.py to check token expiry on each request
- [ ] T090 [US4] Add logic to TokenRefreshMiddleware to call SpotifyAuthService.refresh_access_token() if token expires soon
- [ ] T091 [US4] Add error handling for RefreshTokenExpiredError in TokenRefreshMiddleware (delete token, logout user, redirect to login)
- [ ] T092 [US4] Add type annotations and docstrings to TokenRefreshMiddleware
- [ ] T093 [US4] Register TokenRefreshMiddleware in config/settings.py MIDDLEWARE list (after AuthenticationMiddleware)
- [ ] T094 [US4] Run unit tests and verify they pass: pytest tests/unit/test_spotify_auth_service.py
- [ ] T095 [US4] Run integration tests and verify they pass: pytest tests/integration/test_user_authentication.py
- [ ] T096 [US4] Manual test: Login, manually set token expires_at to past time in database, make request, verify token refreshed
- [ ] T097 [US4] Manual test: Mock refresh token failure, verify user logged out gracefully

**Checkpoint**: All user stories complete - full authentication system with automatic token refresh

---

## Phase 7: Polish & Quality Assurance

**Purpose**: Code quality, documentation, and cross-cutting validation

- [ ] T098 [P] Run pyright on all authentication code: pyright catalog/models.py catalog/services/spotify_auth.py catalog/views.py catalog/middleware.py
- [ ] T099 [P] Resolve any type errors found by pyright (aim for zero errors)
- [ ] T100 [P] Run ruff check on catalog: ruff check catalog/
- [ ] T101 [P] Resolve any linting errors found by ruff
- [ ] T102 [P] Run ruff format on catalog: ruff format catalog/
- [ ] T103 [P] Verify all views, models, services have comprehensive docstrings per project standards
- [ ] T104 Run full test suite: pytest tests/contract/ tests/integration/ tests/unit/
- [ ] T105 Verify all tests pass (contract tests for endpoints, integration tests for user journeys, unit tests for service logic)
- [ ] T106 Test edge case: User denies authorization on Spotify - verify error message and redirect to login
- [ ] T107 Test edge case: Invalid OAuth state parameter - verify 400 error and CSRF protection
- [ ] T108 Test edge case: Network failure during OAuth - verify graceful error handling
- [ ] T109 Test edge case: Spotify API unavailable - verify appropriate error message
- [ ] T110 Test all acceptance scenarios from spec.md User Story 1 (5 scenarios)
- [ ] T111 Test all acceptance scenarios from spec.md User Story 2 (3 scenarios)
- [ ] T112 Test all acceptance scenarios from spec.md User Story 3 (3 scenarios)
- [ ] T113 Test all acceptance scenarios from spec.md User Story 4 (3 scenarios)
- [ ] T114 Verify first user automatically becomes admin (User.objects.count() == 1 → is_admin=True)
- [ ] T115 Verify session persistence across browser sessions (SESSION_COOKIE_SECURE in production)
- [ ] T116 Verify CSRF protection on POST endpoints (logout, disconnect)
- [ ] T117 Verify OAuth state validation prevents CSRF attacks
- [ ] T118 Manual performance check: OAuth flow completes in under 30 seconds per SC-001
- [ ] T119 Update CLAUDE.md "Recent Changes" section with feature summary if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Provides MVP
- **User Story 2 (Phase 4)**: Depends on User Story 1 (requires authentication to work)
- **User Story 3 (Phase 5)**: Depends on User Story 1 (requires authentication to disconnect)
- **User Story 4 (Phase 6)**: Depends on User Story 1 (requires authentication and tokens to refresh)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation - All other stories depend on this (authentication must work first)
- **User Story 2 (P2)**: Depends on US1 (must be logged in to view profile)
- **User Story 3 (P2)**: Depends on US1 (must be logged in to disconnect)
- **User Story 4 (P3)**: Depends on US1 (must have tokens to refresh)

**Note**: US2, US3, and US4 all depend on US1, but once US1 is complete, US2/US3/US4 can be worked on in parallel by different developers since they modify different views/templates.

### Within Each User Story

- Tests before implementation (TDD approach)
- Models before services
- Services before views
- Views before templates
- URL configuration after views
- Manual testing after automated tests pass

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T001-T005 can run in parallel (independent setup activities)

**Phase 2 (Foundational)**:
- T006-T013 (Models and migrations) can run sequentially
- After T013, T014-T023 (SpotifyAuthService) can run in parallel with other work

**Phase 3 (User Story 1) - Tests**:
- T024-T032 (All test file creation and test writing) can run in parallel

**Phase 3 (User Story 1) - Implementation**:
- After tests written (T033), these can run in parallel:
  - T034-T035 (Login template + view)
  - T041-T044 (Middleware creation)
- T036-T038 (OAuth views) must run sequentially (dependency chain)

**After User Story 1 Complete**:
- User Story 2 (T055-T069) can run in parallel with User Story 3 (T070-T082)
- User Story 4 (T083-T097) can start after US1, in parallel with US2/US3

**Phase 7 (Polish)**: Tasks T098-T103 can run in parallel (different validation tools)

---

## Parallel Example: After User Story 1

```bash
# Once US1 is complete, these can run in parallel by different developers:

# Developer A - User Story 2 (Profile Display):
Task: "Create profile template and view"
Task: "Update navigation bar with user dropdown"

# Developer B - User Story 3 (Disconnect):
Task: "Add disconnect view with token deletion"
Task: "Add disconnect button to profile"

# Developer C - User Story 4 (Token Refresh):
Task: "Implement TokenRefreshMiddleware"
Task: "Add automatic refresh logic"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (external Spotify config)
2. Complete Phase 2: Foundational (models, service)
3. Complete Phase 3: User Story 1 (login/logout flow)
4. **STOP and VALIDATE**: Test complete OAuth flow end-to-end
5. Demo/review working authentication before adding profile features

**Result**: Working OAuth authentication that can be demoed and validated

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation verified
2. Add User Story 1 → Test independently → **Demo authentication MVP**
3. Add User Story 2 → Test independently → **Demo profile viewing**
4. Add User Story 3 → Test independently → **Demo account disconnect**
5. Add User Story 4 → Test independently → **Demo automatic token refresh**
6. Complete Polish → Quality checks → **Final review and deploy**

Each step adds value and maintains working functionality throughout.

### Parallel Team Strategy

With 3 developers:

1. **All together**: Complete Setup + Foundational phases
2. **Developer A solo**: Complete User Story 1 (foundation for others)
3. **Once US1 done, split work**:
   - Developer A: User Story 2 (profile viewing)
   - Developer B: User Story 3 (disconnect)
   - Developer C: User Story 4 (token refresh)
4. **All together**: Complete Polish phase (testing, quality checks)

---

## Task Summary

**Total Tasks**: 119

- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 18 tasks (models + service)
- Phase 3 (User Story 1 - P1): 31 tasks (10 tests + 21 implementation)
- Phase 4 (User Story 2 - P2): 15 tasks (4 tests + 11 implementation)
- Phase 5 (User Story 3 - P2): 13 tasks (4 tests + 9 implementation)
- Phase 6 (User Story 4 - P3): 15 tasks (6 tests + 9 implementation)
- Phase 7 (Polish): 22 tasks (quality assurance)

**Parallel Opportunities**:
- Setup phase: 5 tasks can run in parallel
- Foundational phase: Service creation (T014-T023) after migrations
- User Story 1 tests: 9 test tasks can run in parallel (T024-T032)
- After US1 complete: US2, US3, US4 can run in parallel (43 implementation tasks)
- Polish phase: 6 quality check tasks can run in parallel (T098-T103)

**MVP Scope**: User Story 1 (Phase 3) = 31 tasks
- Creates functional OAuth authentication with login/logout
- Can be demoed and validated independently
- Provides foundation for all other user stories

**Independent Test Criteria**:
- **US1**: Click login, complete OAuth, verify authenticated access, logout successfully
- **US2**: Login, navigate to profile, verify display name/email/picture shown
- **US3**: Login, click disconnect, verify logout and token deletion
- **US4**: Login, mock token expiry, make request, verify automatic refresh

---

## Notes

- [P] tasks = Can run in parallel (different files, no dependencies on incomplete work)
- [US#] label = Maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD approach: Write tests first, ensure they fail, then implement to make them pass
- Stop at any checkpoint to validate story independently before proceeding
- All code must pass pyright (zero errors), ruff check (zero errors), and have comprehensive docstrings
- Commit after each user story phase for clean rollback points
