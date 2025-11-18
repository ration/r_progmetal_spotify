# Implementation Plan: Spotify Authentication

**Branch**: `008-spotify-auth` | **Date**: 2025-11-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-spotify-auth/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement Spotify OAuth 2.0 authentication for the Progressive Metal Catalog application. Users will log in using their Spotify accounts, with user profiles stored locally in a database including an administrator flag for access control. The feature enables passwordless authentication while maintaining local user management for application-specific roles and permissions.

**Key clarification from user**: "While authentication works via spotify, it should still have a local user database instance of it. Users can be marked as administrators."

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 5.2.8, django-allauth (for OAuth), spotipy (Spotify API client), psycopg (PostgreSQL adapter)
**Storage**: PostgreSQL (production/Docker), SQLite (local development/tests)
**Testing**: pytest with Django test client, contract tests for OAuth endpoints
**Target Platform**: Linux server (Docker deployment), HTTPS required for production OAuth callbacks
**Project Type**: Web application (Django monolith with templates + HTMX)
**Performance Goals**: OAuth flow completes in <30 seconds, 95% success rate, token refresh transparent to user
**Constraints**: HTTPS required for Spotify OAuth callback, tokens must be encrypted at rest, CSRF protection mandatory
**Scale/Scope**: Single-tenant application, 100s of users expected, admin users manage sync operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` principles:

- [x] **Specification-Driven**: Feature spec completed and validated before planning (16/16 checklist items passed)
- [x] **Type Safety & Code Quality**: Implementation will include type annotations (pyright), linting (ruff), and docstrings per project standards
- [x] **User-Centric Design**: Implementation organized by prioritized user stories (P1 MVP: Login, P2: Profile/Disconnect, P3: Token refresh)
- [x] **Test Independence**: Test requirements explicitly defined in spec (contract tests for OAuth flow, integration tests for user journeys)
- [x] **Incremental Delivery**: Tasks structured to deliver each user story independently (US1 provides working MVP)

**Violations**: None

## Project Structure

### Documentation (this feature)

```text
specs/008-spotify-auth/
├── spec.md              # Feature specification (completed)
├── checklists/
│   └── requirements.md  # Validation checklist (16/16 passed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── http-endpoints.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application (Django monolith)
catalog/  # Existing Django app - authentication extends this
├── models.py          # Add User model with is_admin field, SpotifyToken model
├── views.py           # Add OAuth callback view, login/logout views, profile view
├── urls.py            # Add OAuth routes (/auth/spotify/, /auth/callback/, /auth/logout/)
├── middleware.py      # Add authentication middleware for route protection
├── services/
│   └── spotify_auth.py  # OAuth flow service, token management
├── templates/catalog/
│   ├── login.html     # Login page with "Login with Spotify" button
│   └── profile.html   # Profile page showing Spotify info
├── migrations/
│   └── XXXX_add_user_and_spotify_token_models.py

config/
├── settings.py        # Add SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
└── urls.py            # Mount catalog auth URLs

tests/
├── contract/
│   └── test_spotify_oauth_flow.py  # Test OAuth endpoints
├── integration/
│   └── test_user_authentication.py  # Test complete login/logout flows
└── unit/
    └── test_spotify_auth_service.py  # Test token management logic
```

**Structure Decision**: Extend existing `catalog/` Django app with authentication models and views. This follows Django's "app per feature" pattern where the catalog app owns both album data and user authentication since authentication is needed to access catalog admin features.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - table not needed.

## Phase 0: Research & Technical Decisions

See [research.md](research.md) for detailed decisions on:
- OAuth library selection (django-allauth vs. custom implementation)
- Token storage strategy (encrypted database vs. session storage)
- Session management approach (Django sessions vs. JWT)
- Admin permission model (boolean field vs. Django groups)
- Token refresh strategy (middleware vs. background task)
- CSRF protection implementation
- HTTPS configuration for OAuth callbacks

## Phase 1: Design Artifacts

### Data Model
See [data-model.md](data-model.md) for:
- User model schema (spotify_user_id, email, display_name, profile_picture_url, is_admin)
- SpotifyToken model schema (user FK, access_token, refresh_token, expires_at)
- Relationships and constraints
- Migration strategy

### API Contracts
See [contracts/http-endpoints.md](contracts/http-endpoints.md) for:
- GET /catalog/auth/login/ - Display login page
- GET /catalog/auth/spotify/ - Initiate OAuth flow
- GET /catalog/auth/callback/ - Handle OAuth callback
- POST /catalog/auth/logout/ - End user session
- GET /catalog/auth/profile/ - View user profile
- POST /catalog/auth/disconnect/ - Disconnect Spotify account

### Implementation Guide
See [quickstart.md](quickstart.md) for step-by-step implementation instructions.

## Phase 2: Task Breakdown

Run `/speckit.tasks` to generate actionable task list organized by user story priority.
