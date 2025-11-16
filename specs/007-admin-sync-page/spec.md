# Feature Specification: Admin Sync Page

**Feature Branch**: `007-admin-sync-page`
**Created**: 2025-11-16
**Status**: Draft
**Input**: User description: "Separate admin page. Move the sync now button and status into a separate page."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access Dedicated Sync Administration Page (Priority: P1)

As a site administrator, I need a dedicated page for managing the album synchronization process so that sync controls are separated from the main catalog view and provide a focused administration experience.

**Why this priority**: This is the core requirement - creating the dedicated admin page. Without this, the feature cannot exist. It establishes the foundation for better separation of concerns between user-facing catalog browsing and administrative sync operations.

**Independent Test**: Can be fully tested by navigating to the new admin sync page URL and verifying that the page loads with a proper title, header, and basic layout. Delivers immediate value by providing a dedicated space for sync administration.

**Acceptance Scenarios**:

1. **Given** I am accessing the application, **When** I navigate to the admin sync page URL, **Then** I see a dedicated page with "Sync Administration" or similar title
2. **Given** I am on the admin sync page, **When** the page loads, **Then** I see appropriate navigation options to return to the main catalog
3. **Given** I am on the main catalog page, **When** I look for sync controls, **Then** I do not see the sync button or status (they have been moved to the admin page)
4. **Given** I am on the main catalog page, **When** I look for a link to admin functions, **Then** I see a navigation link or button to access the admin sync page

---

### User Story 2 - Trigger Manual Sync from Admin Page (Priority: P1)

As a site administrator, I need to manually trigger album synchronization from the admin page so that I can update the catalog with the latest data from the Google Sheets source when needed.

**Why this priority**: This is essential functionality - the sync button is the primary action on the admin page. Without it, administrators cannot perform the core administrative task.

**Independent Test**: Can be fully tested by clicking the sync button on the admin page and verifying that synchronization begins. Delivers immediate value by enabling administrators to update the catalog on demand.

**Acceptance Scenarios**:

1. **Given** I am on the admin sync page and no sync is running, **When** I click the "Sync Now" button, **Then** the synchronization process begins
2. **Given** I am on the admin sync page, **When** I click the sync button, **Then** the button state changes to indicate sync is in progress (disabled or shows loading indicator)
3. **Given** I am on the admin sync page and a sync is already running, **When** I view the sync button, **Then** it is disabled or shows a "Sync in Progress" state
4. **Given** I have triggered a sync, **When** the sync completes successfully, **Then** the button returns to its enabled "Sync Now" state

---

### User Story 3 - Monitor Sync Status and Progress (Priority: P1)

As a site administrator, I need to see real-time sync status and progress information on the admin page so that I can monitor the synchronization process and understand what the system is currently doing.

**Why this priority**: Essential for administrators to understand what's happening during sync operations. Without status visibility, the sync process would be a black box, leading to confusion and inability to diagnose issues.

**Independent Test**: Can be fully tested by triggering a sync and observing the status display update with progress information. Delivers immediate value by providing visibility into sync operations.

**Acceptance Scenarios**:

1. **Given** I am on the admin sync page and no sync is running, **When** the page loads, **Then** I see a status message indicating "Ready to synchronize" or similar
2. **Given** I trigger a sync operation, **When** the sync is running, **Then** I see real-time progress updates showing current operation (e.g., "Processing tab: 2025 Prog-metal", "Fetching album 15 of 47")
3. **Given** a sync is in progress, **When** the status updates, **Then** the page refreshes the status information without requiring a full page reload
4. **Given** a sync operation completes, **When** I view the status, **Then** I see a completion message with summary information (e.g., "Sync completed: 47 albums processed, 5 new, 2 updated")
5. **Given** a sync operation fails, **When** I view the status, **Then** I see an error message with details about what went wrong

---

### User Story 4 - View Last Sync Timestamp (Priority: P2)

As a site administrator, I need to see when the last successful synchronization occurred so that I can understand how current the catalog data is and decide if a new sync is needed.

**Why this priority**: Important for operational awareness but not critical for the core sync functionality. Administrators can still perform syncs without this information, but it helps them make informed decisions.

**Independent Test**: Can be fully tested by performing a sync and verifying the timestamp appears and updates correctly. Delivers value by providing historical context for sync operations.

**Acceptance Scenarios**:

1. **Given** I am on the admin sync page, **When** the page loads after at least one successful sync, **Then** I see a timestamp showing when the last sync completed (e.g., "Last synced: 5 minutes ago")
2. **Given** no sync has ever been performed, **When** I view the admin page, **Then** I see a message indicating "Never synced"
3. **Given** I complete a sync operation, **When** the sync finishes successfully, **Then** the "Last synced" timestamp updates to reflect the current completion time
4. **Given** I am viewing the last sync timestamp, **When** time passes, **Then** the relative time updates (e.g., "5 minutes ago" → "6 minutes ago") without requiring page refresh

---

### Edge Cases

- What happens when a user tries to trigger a sync while one is already in progress? (System should prevent duplicate syncs and show appropriate status)
- What happens when a sync operation takes a very long time (30+ minutes)? (Status should continue updating and not timeout)
- What happens if the admin page is opened in multiple browser tabs/windows simultaneously? (All instances should show synchronized status updates)
- What happens when sync fails due to network issues or API errors? (Clear error message displayed with details)
- What happens when navigating away from the admin page while a sync is in progress? (Sync should continue in background, status visible when returning to page)
- What happens if synchronization was never run before (cold start)? (Appropriate messaging indicating no sync history)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated admin page accessible via a distinct URL path (e.g., `/admin/sync` or `/catalog/admin/sync`)
- **FR-002**: System MUST display a "Sync Now" button on the admin page that allows administrators to manually trigger album synchronization
- **FR-003**: System MUST display real-time sync status information on the admin page, including current operation and progress details
- **FR-004**: System MUST update sync status information automatically without requiring manual page refresh
- **FR-005**: System MUST remove the sync button and sync status components from the main catalog listing page (album_list.html)
- **FR-006**: System MUST prevent multiple simultaneous sync operations from being triggered
- **FR-007**: System MUST display the timestamp of the last successful synchronization on the admin page
- **FR-008**: System MUST display appropriate messaging when no synchronization has ever been performed ("Never synced")
- **FR-009**: System MUST provide navigation from the main catalog page to the admin sync page
- **FR-010**: System MUST provide navigation from the admin sync page back to the main catalog
- **FR-011**: System MUST display sync completion status (success or failure) with summary information
- **FR-012**: System MUST maintain existing sync functionality behavior (same sync logic, just different location)
- **FR-013**: System MUST display sync progress updates in real-time during synchronization operations

### Key Entities

- **Admin Sync Page**: A dedicated web page containing sync administration controls and status information, separate from the main catalog browsing interface
- **Sync Operation**: The existing album synchronization process that fetches data from Google Sheets and Spotify API
- **Sync Status**: Real-time information about current sync operations, including progress, current activity, and completion state
- **Sync Button Component**: The interactive control that triggers manual synchronization (moved from catalog page to admin page)
- **Sync History**: Historical information about past sync operations, including timestamps of last successful sync

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can access a dedicated admin sync page with all sync controls in under 2 clicks from the main catalog page
- **SC-002**: Sync status updates appear on the admin page within 2 seconds of sync state changes without manual page refresh
- **SC-003**: Main catalog page loads faster and has cleaner interface without sync controls (measurable by absence of sync UI components)
- **SC-004**: Administrators can successfully trigger and monitor sync operations from the new admin page with identical functionality to the previous embedded implementation
- **SC-005**: All existing sync functionality remains operational after the move (0 regression in sync behavior)
- **SC-006**: Admin page displays last sync timestamp accurately to the minute, updating in real-time

## Assumptions

1. **Authentication/Authorization**: The admin sync page will initially be accessible to all users. If access control is needed in the future, it will be added as a separate enhancement. This feature focuses solely on moving UI elements, not adding security.

2. **URL Structure**: The admin page will follow the existing URL convention for the catalog app (e.g., `/catalog/admin/sync`). The exact URL pattern will be determined during implementation but will be consistent with Django best practices.

3. **Existing Sync Logic**: All existing synchronization business logic, HTMX polling behavior, and backend views will remain unchanged. Only the template structure and routing will be modified to display components on a different page.

4. **Navigation Pattern**: A simple link or button will be added to navigate between the main catalog and admin page. Detailed navigation design (header menu, admin panel, etc.) is out of scope for this feature.

5. **Real-time Updates**: The existing HTMX-based real-time update mechanism for sync status will be preserved and will work identically on the new admin page.

6. **Responsive Design**: The admin page will follow the same responsive design patterns as the existing catalog pages using Tailwind CSS and DaisyUI.

7. **Browser Support**: The admin page will support the same browsers as the existing application (modern browsers with JavaScript enabled for HTMX functionality).

## Out of Scope

- Authentication or authorization mechanisms for the admin page
- Enhanced admin features beyond sync management (user management, settings, etc.)
- Detailed admin dashboard or analytics beyond existing sync information
- Email notifications or alerts for sync completion/failure
- Scheduled/automated sync operations (only manual triggering is in scope)
- Sync history log or detailed audit trail beyond last sync timestamp
- Changes to the underlying sync algorithm or business logic
- Performance optimizations to the sync process itself
- Multi-user concurrency controls beyond preventing duplicate syncs
