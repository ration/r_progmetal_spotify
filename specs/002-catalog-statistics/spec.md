# Feature Specification: Catalog Statistics

**Feature Branch**: `002-catalog-statistics`
**Created**: 2025-11-03
**Status**: Draft
**Input**: User description: "Catalog statistics. The main catalog page shows the time of last synchonization, total amount and the amount added in last syncrhonization."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Catalog Freshness (Priority: P1)

As a user visiting the catalog page, I want to see when the catalog was last updated so I can know if I'm looking at current release information.

**Why this priority**: This is the most critical piece of information as it directly answers "How current is this data?" - essential for user trust and decision-making about whether to check back later.

**Independent Test**: Can be fully tested by navigating to the catalog page and verifying that a "Last synchronized" timestamp is displayed, delivering immediate value by showing data freshness.

**Acceptance Scenarios**:

1. **Given** the catalog was synchronized 2 hours ago, **When** I visit the catalog page, **Then** I see "Last synchronized: 2 hours ago" displayed prominently
2. **Given** the catalog was synchronized yesterday, **When** I visit the catalog page, **Then** I see "Last synchronized: 1 day ago" or the exact date/time
3. **Given** the catalog has never been synchronized, **When** I visit the catalog page, **Then** I see "Not yet synchronized" or similar message

---

### User Story 2 - View Total Catalog Size (Priority: P2)

As a user browsing albums, I want to see the total number of albums in the catalog so I understand the scope and completeness of the collection.

**Why this priority**: Provides context about catalog size but is less critical than knowing if data is current. Adds value for users curious about the collection size.

**Independent Test**: Can be tested by navigating to the catalog page and verifying that a total count (e.g., "1,247 albums") is displayed, independent of synchronization status.

**Acceptance Scenarios**:

1. **Given** the catalog contains 1,247 albums, **When** I visit the catalog page, **Then** I see "1,247 albums" or "Total: 1,247" displayed
2. **Given** the catalog is empty, **When** I visit the catalog page, **Then** I see "0 albums" or "No albums yet"
3. **Given** the catalog count changes while I'm viewing, **When** I refresh the page, **Then** I see the updated count

---

### User Story 3 - See Recent Growth (Priority: P3)

As a regular visitor to the catalog, I want to see how many albums were added in the last synchronization so I can quickly identify if there's new content worth exploring.

**Why this priority**: Enhances user engagement by highlighting new content, but provides value only after the first two statistics are established. Most useful for returning visitors.

**Independent Test**: Can be tested by performing a synchronization that adds albums, then verifying the "Added recently" count displays correctly and resets on subsequent syncs.

**Acceptance Scenarios**:

1. **Given** the last sync added 15 new albums, **When** I visit the catalog page, **Then** I see "+15 new" or "15 added recently"
2. **Given** the last sync added 0 albums, **When** I visit the catalog page, **Then** I see "+0 new" or no growth indicator
3. **Given** the last sync removed albums (no new additions), **When** I visit the catalog page, **Then** I see "+0 new"

---

### Edge Cases

- What happens when the catalog has never been synchronized? (Display "Not yet synchronized" with total of 0)
- How does the system handle very large numbers (10,000+ albu
- ms)? (Use thousands separators for readability)
- What if the last sync failed or is in progress? (Show appropriate status like "Sync in progress..." or "Last successful sync: [time]")
- How are time displays localized? (Use relative time like "2 hours ago" for recent syncs, absolute dates for older syncs)
- What if multiple syncs happen rapidly (within minutes)? (Always show the most recent successful sync)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display the timestamp of the most recent successful catalog synchronization
- **FR-002**: System MUST display the total count of albums currently in the catalog
- **FR-003**: System MUST display the count of albums added during the most recent synchronization
- **FR-004**: System MUST format large numbers with thousands separators (e.g., 1,247 not 1247)
- **FR-005**: System MUST display relative time (e.g., "2 hours ago") for synchronizations within the last 24 hours
- **FR-006**: System MUST display absolute date/time for synchronizations older than 24 hours
- **FR-007**: System MUST handle the case where no synchronization has occurred (display "Not yet synchronized")
- **FR-008**: System MUST display "0 albums" when the catalog is empty
- **FR-009**: System MUST show "+0 new" or hide the growth indicator when no albums were added in the last sync
- **FR-010**: Statistics MUST reflect the current state of the catalog (no caching issues)

### Key Entities *(include if feature involves data)*

- **Synchronization Record**: Represents a sync operation with timestamp, albums added count, and success/failure status
- **Album**: Existing entity whose total count is displayed in statistics
- **Catalog Statistics**: Aggregate view combining sync timestamp, total album count, and recent additions count

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view catalog freshness information (last sync time) within 2 seconds of page load
- **SC-002**: Statistics update immediately (within 5 seconds) after a synchronization completes
- **SC-003**: 95% of users can understand the statistics without additional explanation or help text
- **SC-004**: Time displays are human-readable and don't require users to calculate time differences
- **SC-005**: Numbers remain readable and formatted correctly even with catalogs exceeding 10,000 albums

## Assumptions *(optional)*

- Statistics will be displayed in a prominent location on the catalog page (header or info panel)
- Only successful synchronizations count toward "last synchronized" time
- "Albums added" refers to net additions (doesn't account for removals or updates)
- Users want to see these statistics on every visit without interaction
- Synchronization happens through existing import commands (`import_albums`, `sync_spotify`)
- Statistics should be visible on both full page loads and HTMX partial updates

## Constraints *(optional)*

- Must integrate with existing catalog page layout without major redesign
- Must work with current PostgreSQL schema (may require new fields or tables)
- Must maintain performance even with large catalogs (10,000+ albums)
- Statistics queries should not significantly impact page load time

## Dependencies *(optional)*

- Existing catalog page template (`catalog/templates/`)
- Current Album model and database schema
- Existing synchronization commands must track metadata (timestamp, albums added)

## Out of Scope *(optional)*

- Detailed synchronization history (showing multiple past syncs)
- Per-sync details (which specific albums were added)
- Synchronization error messages or troubleshooting info
- Manual refresh button for statistics
- Admin-only vs. public visibility controls
- Export or reporting features for statistics
- Comparison with previous time periods ("10% growth this month")
