# Feature Specification: Multi-Tab Google Sheets Parsing

**Feature Branch**: `005-multi-tab-parsing`
**Created**: 2025-01-05
**Status**: Draft
**Input**: User description: "Parse all tabs in the google sheet. The sheet has multiple tabs with similar information. Parse all of it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import Albums from All Years (Priority: P1)

Users can synchronize albums from all available year tabs in the Google Sheets document (2025, 2024, 2023, etc.) instead of just a single year, ensuring the complete historical catalog is available.

**Why this priority**: This is the core value of the feature - enabling comprehensive data import across all time periods. Without this, users only get a single year's worth of data.

**Independent Test**: Can be fully tested by triggering a sync operation and verifying that albums from multiple year tabs (e.g., 2025, 2024, 2023) appear in the catalog with correct release dates.

**Acceptance Scenarios**:

1. **Given** the Google Sheet has multiple tabs (2025, 2024, 2023), **When** user triggers synchronization, **Then** albums from all year tabs are imported into the catalog
2. **Given** synchronization is triggered, **When** the system processes multiple tabs, **Then** progress tracking shows the current tab being processed and total tab count
3. **Given** albums already exist from a previous tab, **When** the same album appears in another tab, **Then** the system skips duplicates based on spotify_album_id

---

### User Story 2 - View Multi-Year Statistics (Priority: P2)

Users can see catalog statistics that reflect albums from all imported year tabs, providing a complete historical view of the progressive metal releases collection.

**Why this priority**: Once multi-tab import works (P1), users need visibility into what data was imported. This enhances the existing statistics feature to be multi-year aware.

**Independent Test**: Can be tested by importing data from multiple tabs and verifying the statistics panel shows accurate counts across all years.

**Acceptance Scenarios**:

1. **Given** albums from multiple years are imported, **When** user views the catalog, **Then** statistics show total album count across all years
2. **Given** the catalog contains multi-year data, **When** user views statistics, **Then** the last sync timestamp reflects the most recent successful multi-tab sync operation

---

### User Story 3 - Handle Tab-Specific Errors Gracefully (Priority: P3)

When one year tab fails to parse or has data issues, the system continues processing remaining tabs and provides clear error reporting about which tabs succeeded or failed.

**Why this priority**: This improves resilience and user experience but isn't critical for initial functionality. Users can still get value even if error handling isn't perfect initially.

**Independent Test**: Can be tested by simulating a tab with invalid data format and verifying the sync continues with other tabs while reporting the specific tab failure.

**Acceptance Scenarios**:

1. **Given** one tab has invalid data format, **When** synchronization runs, **Then** system logs the error for that specific tab and continues processing remaining tabs
2. **Given** multiple tabs are processed, **When** some tabs fail and others succeed, **Then** sync status displays which tabs succeeded (e.g., "2025: 50 albums, 2024: 45 albums, 2023: Failed") and overall success/failure status
3. **Given** a tab is completely empty, **When** synchronization processes it, **Then** system logs a warning and skips to the next tab without failing the entire sync

---

### Edge Cases

- What happens when a tab has a different column structure than expected?
- How does the system handle tabs that don't follow the year naming convention?
- What if two different tabs contain the exact same album (duplicate across years)?
- How does the system behave if there are 10+ year tabs?
- What happens if a tab name changes between sync operations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect and enumerate all available tabs in the Google Sheets document
- **FR-002**: System MUST parse album data from each detected tab following the same data extraction logic used for single-tab imports
- **FR-003**: System MUST skip duplicate albums across tabs based on spotify_album_id to avoid redundant imports
- **FR-004**: System MUST track which tab is currently being processed and include this in progress updates
- **FR-005**: System MUST handle tab-specific parse failures without aborting the entire synchronization process
- **FR-006**: System MUST log which tabs were successfully processed and which failed with specific error messages
- **FR-007**: System MUST fully replace single-tab mode with multi-tab parsing (removing gid parameter requirement)
- **FR-008**: System MUST process tabs in chronological order from oldest to newest year (e.g., 2017 → 2018 → 2019 → ... → 2025)
- **FR-011**: System MUST filter tabs by name pattern to import only progressive metal tabs (ending with "Prog-metal" or year-only names like "2017", "2018") and skip prog-rock, statistics, and reissue tabs
- **FR-009**: System MUST update sync progress to show "Processing tab X of Y: [tab_name]" during multi-tab synchronization
- **FR-010**: System MUST create a single SyncRecord entry that aggregates results from all tabs (total created, updated, skipped across all tabs)

### Key Entities

- **Tab/Sheet**: Represents a worksheet within the Google Sheets document, typically corresponding to a year (e.g., "2025", "2024"). Contains album data with the same column structure as the single-tab import.
- **SyncOperation**: Existing entity that tracks synchronization progress - will be enhanced to track current tab being processed and tab-level progress
- **Album**: Existing entity - remains unchanged, uses spotify_album_id as unique identifier to prevent duplicates across tabs

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully imports albums from all available tabs in under 5 minutes for a sheet with 5 tabs containing 50 albums each
- **SC-002**: Duplicate detection prevents the same album from being imported multiple times when it appears in multiple tabs (0% duplicate imports)
- **SC-003**: Progress updates refresh every 2 seconds showing current tab name and albums processed for that tab
- **SC-004**: If 1 out of 5 tabs fails, the synchronization still completes successfully for the remaining 4 tabs with clear error reporting
- **SC-005**: Users can view the complete catalog spanning multiple years after a single sync operation
- **SC-006**: Sync status displays tab-level breakdown showing which tabs were processed and how many albums from each tab

## Assumptions

1. All tabs in the Google Sheet follow the same column structure (Artist, Album, Release Date, Spotify, etc.)
2. Tabs are primarily year-based (2025, 2024, 2023) but the system should handle any tab name
3. The Google Sheets document URL structure allows programmatic access to all tabs (not just single gid parameter)
4. The existing duplicate detection logic (spotify_album_id) is sufficient for cross-tab deduplication
5. Users expect a single sync operation to import all historical data, not require separate syncs per year
6. Tab processing can happen sequentially (not required to process multiple tabs in parallel)

## Out of Scope

- Filtering which tabs to import (all or none approach for initial implementation)
- User-configurable tab selection via UI
- Parallel processing of multiple tabs simultaneously
- Historical tracking of which tabs were imported in previous sync operations
- Tab-specific sync schedules or configurations
