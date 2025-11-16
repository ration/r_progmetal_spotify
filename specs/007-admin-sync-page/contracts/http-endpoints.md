# HTTP Endpoints Contract: Admin Sync Page

**Feature**: 007-admin-sync-page
**Date**: 2025-11-16
**Protocol**: HTTP/HTTPS
**Format**: HTML (Django templates)

## Overview

This document defines the HTTP endpoint contracts for the admin sync page feature. This feature introduces one new endpoint and reuses several existing endpoints that remain unchanged.

---

## New Endpoints

### GET /catalog/admin/sync

**Purpose**: Display the dedicated admin sync page with sync controls

**Authentication**: None (assumed accessible to all users per spec assumptions)

**Request**:
```http
GET /catalog/admin/sync HTTP/1.1
Host: example.com
Accept: text/html
```

**Response - Success (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
  <head><title>Sync Administration - Progressive Metal Catalog</title></head>
  <body>
    <!-- Full page with base template -->
    <h1>Sync Administration</h1>

    <!-- Sync button component (HTMX polling) -->
    <div id="sync-button-container" hx-get="/catalog/sync/button/" ...>
      <button class="btn btn-primary">Sync Now</button>
    </div>

    <!-- Sync status component (HTMX polling) -->
    <div id="sync-status" hx-get="/catalog/sync/status/" ...>
      <div>Ready to synchronize.</div>
    </div>

    <!-- Last sync timestamp -->
    <div>Last synced: <span class="timeago">5 minutes ago</span></div>

    <!-- Navigation back to catalog -->
    <a href="/catalog/">Back to Catalog</a>
  </body>
</html>
```

**Response - Error (500 Internal Server Error)**:
```http
HTTP/1.1 500 Internal Server Error
Content-Type: text/html

<!DOCTYPE html>
<html>
  <body>
    <h1>Server Error</h1>
    <p>Unable to load admin sync page.</p>
  </body>
</html>
```

**Context Data**:
- `latest_sync`: SyncRecord object or None
- `page_title`: String ("Sync Administration")

**Template**: `catalog/admin_sync.html`

**URL Name**: `catalog:admin-sync`

**State Changes**: None (read-only view)

**Side Effects**: None

**Performance**: Expected page load <2 seconds (per spec success criteria)

---

## Modified Endpoints

### GET /catalog/

**Purpose**: Display main album catalog listing

**Changes**:
- **REMOVED**: Sync button component include
- **REMOVED**: Sync status component include
- **REMOVED**: Last sync timestamp section
- **ADDED**: Link/button to navigate to admin sync page

**Before (Old Response)**:
```html
<body>
  <h1>Album Catalog</h1>

  <!-- Sync controls (TO BE REMOVED) -->
  <div id="sync-button-container">...</div>
  <div id="sync-status">...</div>
  <div>Last synced: ...</div>

  <!-- Catalog content (UNCHANGED) -->
  <div id="album-tiles">...</div>
</body>
```

**After (New Response)**:
```html
<body>
  <nav>
    <a href="/catalog/admin/sync/">Admin</a>
  </nav>

  <h1>Album Catalog</h1>

  <!-- Sync controls REMOVED -->

  <!-- Catalog content (UNCHANGED) -->
  <div id="album-tiles">...</div>
</body>
```

**Impact**:
- Faster page load (fewer components to render/poll)
- Cleaner UI (administrative controls separated)
- No breaking changes to URL or functionality

---

## Unchanged Endpoints (Reused)

The following existing endpoints remain unchanged and are used by components on the new admin page:

### POST /catalog/sync/trigger/

**Purpose**: Trigger manual synchronization

**Usage**: Called by sync button component when clicked

**Contract**: Unchanged - see existing implementation in `catalog/views.sync_trigger`

**Location**: Reused by `sync_button.html` component on admin page

---

### POST /catalog/sync/stop/

**Purpose**: Stop currently running synchronization

**Usage**: Called by sync button component when "Stop" clicked during active sync

**Contract**: Unchanged - see existing implementation in `catalog/views.sync_stop`

**Location**: Reused by `sync_button.html` component on admin page

---

### GET /catalog/sync/button/

**Purpose**: Render current sync button state (polling endpoint)

**Usage**: HTMX polls this every 2 seconds to update button state

**Contract**: Unchanged - see existing implementation in `catalog/views.sync_button`

**Polling**: `hx-trigger="every 2s"` (configured in component template)

**Location**: Polled by `sync_button.html` component on admin page

---

### GET /catalog/sync/status/

**Purpose**: Render current sync status and progress (polling endpoint)

**Usage**: HTMX polls this every 2 seconds to display real-time progress

**Contract**: Unchanged - see existing implementation in `catalog/views.sync_status`

**Polling**: `hx-trigger="every 2s"` (configured in component template)

**Location**: Polled by `sync_status.html` component on admin page

---

## Navigation Flow

```
┌─────────────────────────────────────────┐
│   GET /catalog/                         │
│   (Album Catalog List)                  │
│                                         │
│   [Admin] link/button                   │
└─────────────────┬───────────────────────┘
                  │
                  │ User clicks "Admin"
                  ▼
┌─────────────────────────────────────────┐
│   GET /catalog/admin/sync               │
│   (Admin Sync Page)                     │
│                                         │
│   [Back to Catalog] link                │
└─────────────────┬───────────────────────┘
                  │
                  │ User clicks "Back to Catalog"
                  ▼
┌─────────────────────────────────────────┐
│   GET /catalog/                         │
│   (Returns to Album Catalog)            │
└─────────────────────────────────────────┘
```

---

## HTMX Polling Behavior

Both sync button and sync status components use HTMX polling on the admin page:

**Sync Button Polling**:
```html
<div id="sync-button-container"
     hx-get="/catalog/sync/button/"
     hx-trigger="load, syncStarted from:body, syncStopped from:body, every 2s"
     hx-swap="innerHTML">
  <!-- Button content updated via HTMX -->
</div>
```

**Sync Status Polling**:
```html
<div id="sync-status"
     hx-get="/catalog/sync/status/"
     hx-trigger="syncStarted from:body, every 2s"
     hx-swap="innerHTML">
  <!-- Status content updated via HTMX -->
</div>
```

**Event-Based Updates**:
- `syncStarted from:body`: Triggered when sync begins
- `syncStopped from:body`: Triggered when sync stops
- `syncCompleted from:body`: Triggered when sync completes
- `syncFailed from:body`: Triggered when sync fails

These events are dispatched by existing sync views and work identically on the admin page.

---

## URL Routing Table

| URL Pattern | View Function | URL Name | Method | Purpose |
|-------------|---------------|----------|--------|---------|
| `/catalog/admin/sync/` | `admin_sync_page` | `catalog:admin-sync` | GET | **NEW**: Display admin sync page |
| `/catalog/` | `AlbumListView.as_view()` | `catalog:album-list` | GET | **MODIFIED**: Remove sync components |
| `/catalog/sync/trigger/` | `sync_trigger` | `catalog:sync-trigger` | POST | **UNCHANGED**: Trigger sync |
| `/catalog/sync/stop/` | `sync_stop` | `catalog:sync-stop` | POST | **UNCHANGED**: Stop sync |
| `/catalog/sync/button/` | `sync_button` | `catalog:sync-button` | GET | **UNCHANGED**: Render button state |
| `/catalog/sync/status/` | `sync_status` | `catalog:sync-status` | GET | **UNCHANGED**: Render sync status |

---

## Error Handling

### Admin Page Load Failure

**Scenario**: Database unavailable when querying `SyncRecord`

**Response**:
```http
HTTP/1.1 500 Internal Server Error
```

**User Experience**: Django error page or custom 500 template

**Mitigation**: Wrap query in try/except, provide graceful fallback

---

### Component Polling Failure

**Scenario**: Sync status/button endpoint unavailable during polling

**Response**:
```http
HTTP/1.1 500 Internal Server Error
```

**User Experience**: HTMX shows previous component state, retries on next poll interval

**Mitigation**: HTMX built-in retry logic handles transient failures

---

## Performance Criteria

Per spec success criteria:

- **SC-001**: Admin page accessible in <2 clicks from catalog page ✓
- **SC-002**: Sync status updates appear within 2 seconds ✓ (HTMX polls every 2s)
- **SC-003**: Catalog page loads faster without sync components ✓ (fewer includes/polls)

---

## Backward Compatibility

**Breaking Changes**: None

**Migration Path**:
1. Add new admin page endpoint (new functionality, no impact)
2. Add navigation to admin page (additive change)
3. Remove sync components from catalog page (visual change only, no API breaks)

**Rollback Plan**:
- Restore sync component includes to album_list.html
- Remove admin navigation link
- Admin page can remain (harmless) or be removed

---

## Security Considerations

Per spec assumptions:

- **Authentication**: Not implemented in this feature (future enhancement)
- **Authorization**: Not implemented in this feature (future enhancement)
- **CSRF Protection**: POST endpoints (`sync_trigger`, `sync_stop`) already CSRF-protected via Django middleware
- **Input Validation**: Not applicable (no user input on admin page)

---

## Testing Strategy

### Manual Testing

1. **Admin Page Access**:
   - Navigate to `/catalog/admin/sync`
   - Verify page loads with title "Sync Administration"
   - Verify sync button, status, and timestamp visible

2. **Sync Button Functionality**:
   - Click "Sync Now" button
   - Verify sync starts and button updates to "Sync in Progress"
   - Verify button returns to "Sync Now" when complete

3. **Status Updates**:
   - Trigger sync
   - Observe status updates every ~2 seconds
   - Verify progress messages appear ("Processing tab: ...", "Fetching album X of Y")

4. **Timestamp Display**:
   - Complete a sync
   - Verify "Last synced: X minutes ago" appears
   - Wait 1 minute, verify timestamp updates

5. **Navigation**:
   - From catalog page, click "Admin" link
   - Verify lands on admin sync page
   - Click "Back to Catalog"
   - Verify returns to catalog page

6. **Catalog Page Changes**:
   - Navigate to `/catalog/`
   - Verify sync button/status NOT present
   - Verify admin navigation link IS present

### Automated Testing (Optional)

Contract tests could verify:
- Admin page returns 200 status
- Admin page includes expected components
- Catalog page no longer includes sync components
- Navigation links use correct URL names

---

## Summary

This feature introduces one new endpoint (`GET /catalog/admin/sync`) and modifies one existing endpoint (`GET /catalog/`) to remove sync components. All sync functionality endpoints remain unchanged and are reused via HTMX component includes on the new admin page.

The HTTP contract is minimal and low-risk, with no breaking changes to existing API endpoints or behavior.
