# Feature Specification: Just-in-Time Spotify API Usage

**Feature Branch**: `006-jit-spotify-api`
**Created**: 2025-11-07
**Status**: Draft
**Input**: User description: "Just in time usage of spotify API. Populate the database only with google data. Use the spotify api only when the cover art needs to be visible on the UI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Album Catalog with Cover Art (Priority: P1)

A user visits the album catalog and browses albums. As they scroll through the page, album cover images appear for albums that are visible on screen. The cover art is fetched from Spotify on-demand rather than being pre-loaded during data import.

**Why this priority**: This is the core value proposition - optimizing Spotify API usage while maintaining a seamless browsing experience. Without this, the application continues using excessive API calls during import.

**Independent Test**: Can be fully tested by loading the album catalog page, verifying that albums display with cover art from Spotify, and confirming that Spotify API calls only occur when albums become visible in the viewport. Delivers immediate value by reducing API rate limit issues and improving import performance.

**Acceptance Scenarios**:

1. **Given** the user opens the album catalog page, **When** the page loads, **Then** album tiles display with cover art fetched from Spotify API only for visible albums
2. **Given** albums are displayed on the page, **When** the user scrolls to reveal more albums, **Then** cover art is fetched from Spotify API as albums enter the viewport
3. **Given** an album's cover art has been fetched once, **When** the user returns to the catalog later, **Then** the cached cover art is displayed without additional API calls
4. **Given** the Spotify API is unavailable or rate-limited, **When** the user views an album, **Then** a placeholder image is displayed instead of causing an error

---

### User Story 2 - Import Albums Without Spotify Dependencies (Priority: P2)

An administrator runs the album import command to sync data from Google Sheets. The import process completes quickly by storing only the basic album information (name, artist, release date, Spotify URL) without fetching cover art or detailed metadata from Spotify.

**Why this priority**: This enables fast, reliable imports that aren't blocked by Spotify API rate limits. The catalog becomes operational immediately after import, with cover art loaded on-demand.

**Independent Test**: Can be tested by running the import command and verifying that albums are stored in the database with Google Sheets data and Spotify URLs, but without cover art URLs or other Spotify-specific metadata. Delivers value as a faster, more reliable import process.

**Acceptance Scenarios**:

1. **Given** new album data exists in Google Sheets, **When** the administrator runs the import command, **Then** albums are stored with basic information (name, artist, release date, Spotify URL) without making Spotify API calls
2. **Given** the import process is running, **When** the Spotify API is unavailable, **Then** the import completes successfully because it doesn't depend on Spotify
3. **Given** albums have been imported without cover art, **When** users view the catalog, **Then** cover art is fetched just-in-time from Spotify URLs stored during import
4. **Given** an album's Spotify URL is stored, **When** the cover art needs to be displayed, **Then** the system extracts the album ID from the URL and requests cover art from Spotify

---

### User Story 3 - View Album Detail Page with Full Metadata (Priority: P3)

A user clicks on an album tile to view detailed information. The detail page displays comprehensive album metadata (genres, tracks, popularity) by fetching this information from Spotify when the detail page is loaded, rather than during import.

**Why this priority**: This extends the just-in-time approach to detailed metadata, further reducing API usage during import while providing rich information when users need it.

**Independent Test**: Can be tested by clicking an album tile and verifying that the detail page displays full Spotify metadata, which is fetched on-demand. Delivers value as an enhanced information view without import-time API overhead.

**Acceptance Scenarios**:

1. **Given** the user clicks on an album tile, **When** the detail page loads, **Then** full album metadata (genres, track list, popularity) is fetched from Spotify and displayed
2. **Given** detailed metadata has been fetched for an album, **When** the user views that album's details again, **Then** the cached metadata is displayed without additional API calls
3. **Given** the user views an album detail page, **When** Spotify metadata cannot be fetched, **Then** the page displays available information from Google Sheets with a message about unavailable additional details

---

### Edge Cases

- What happens when a Spotify URL stored in the database is invalid or points to a deleted album?
- How does the system handle albums that don't have a Spotify URL in the Google Sheets data?
- What happens when multiple users request cover art for the same album simultaneously?
- How does the interface handle slow Spotify API responses that delay cover art loading?
- What happens when the Spotify API returns an error for a specific album but is working for others?
- How does the system cache cover art and metadata to minimize repeated API calls?
- What happens when an album's Spotify metadata changes after being cached (e.g., updated genres)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store album data from Google Sheets without making Spotify API calls during import
- **FR-002**: System MUST store Spotify album URLs from Google Sheets during import for later use
- **FR-003**: System MUST fetch album cover art from Spotify API only when albums are displayed in the user interface
- **FR-004**: System MUST cache fetched cover art to prevent duplicate API calls for the same album
- **FR-005**: System MUST display a placeholder image when cover art cannot be fetched from Spotify
- **FR-006**: System MUST extract Spotify album IDs from stored URLs to request cover art
- **FR-007**: System MUST handle Spotify API rate limits gracefully without breaking the user experience
- **FR-008**: System MUST fetch detailed album metadata (genres, tracks, popularity) from Spotify only when users view the album detail page
- **FR-009**: System MUST cache detailed album metadata to prevent duplicate API calls
- **FR-010**: System MUST complete album imports successfully even when Spotify API is unavailable
- **FR-011**: Users MUST be able to browse the album catalog with cover art loaded progressively as they scroll
- **FR-012**: System MUST handle missing or invalid Spotify URLs gracefully by using placeholder images
- **FR-013**: System MUST support concurrent requests for cover art from multiple users efficiently
- **FR-014**: System MUST log Spotify API errors for monitoring and debugging without exposing errors to users
- **FR-015**: System MUST provide an administrative command to manually refresh cached cover art and metadata when needed, without automatic expiration

### Key Entities

- **Album**: Represents a music album with basic information from Google Sheets (name, artist, release date) and a reference to its Spotify URL. Cover art URL and detailed metadata are populated on-demand.
- **Album Cover Cache**: Stores fetched cover art URLs and timestamps to minimize redundant Spotify API calls.
- **Album Metadata Cache**: Stores detailed Spotify metadata (genres, tracks, popularity) fetched for the album detail view.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Album import process completes without making Spotify API calls, reducing import time by at least 50% compared to the current eager-loading approach
- **SC-002**: Users see album cover art appear within 1 second of albums becoming visible in their viewport
- **SC-003**: Repeated views of the same album use cached cover art, resulting in zero additional Spotify API calls for previously viewed albums
- **SC-004**: System handles Spotify API rate limits without displaying errors to users, showing placeholder images instead
- **SC-005**: 95% of album cover art requests complete successfully on first attempt when Spotify API is available
- **SC-006**: System reduces total Spotify API calls by at least 80% by loading data only when needed rather than during import

## Constraints & Dependencies *(include if applicable)*

### Dependencies

- Google Sheets contains Spotify album URLs for albums being imported
- Spotify Web API access is available with appropriate credentials (client ID and secret)
- Existing album import infrastructure supports storing Spotify URLs without fetching metadata

### Constraints

- Spotify API has rate limits (~180 requests per 30 seconds) that must be respected
- Cover art fetching must not significantly delay page rendering or create a poor user experience
- The solution must work with the existing album catalog UI and data model
- Cached data must be stored efficiently without excessive database growth

## Assumptions *(include if applicable)*

- Most users will only view a subset of albums in the catalog, making just-in-time loading more efficient than pre-fetching all cover art
- Album cover art URLs from Spotify are stable and don't change frequently
- Network latency for Spotify API requests is acceptable for on-demand loading (typically under 500ms)
- The application has sufficient caching infrastructure (database or cache layer) to store cover art URLs and metadata
- Google Sheets data includes valid Spotify URLs for the majority of albums
