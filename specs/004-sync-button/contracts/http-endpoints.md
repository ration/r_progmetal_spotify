# HTTP Endpoint Contracts: Synchronization Button with Status Display

**Feature**: 004-sync-button
**Date**: 2025-11-04
**Purpose**: Define HTTP API contracts for sync trigger and status endpoints

## Overview

This feature exposes two primary HTTP endpoints:
1. **POST /catalog/sync/trigger/** - Initiate synchronization
2. **GET /catalog/sync/status/** - Poll for current sync status

Both endpoints return HTML fragments for HTMX integration (not JSON). Standard HTTP status codes indicate success/error states.

---

## Endpoint 1: Trigger Synchronization

### Request

**Method**: `POST`

**URL**: `/catalog/sync/trigger/`

**URL Pattern** (Django): `path('sync/trigger/', views.sync_trigger, name='sync-trigger')`

**Headers**:
```http
Content-Type: application/x-www-form-urlencoded
HX-Request: true
X-CSRFToken: <csrf_token>
```

**Body**: None (no parameters required for full sync)

**Authentication**: None (Phase 1). Future: may require staff/admin permission.

**Example**:
```http
POST /catalog/sync/trigger/ HTTP/1.1
Host: localhost:8000
Content-Type: application/x-www-form-urlencoded
HX-Request: true
X-CSRFToken: abc123def456
```

---

### Response: Success (202 Accepted)

**Status Code**: `202 Accepted`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
HX-Trigger: syncStarted
```

**Body** (HTML Fragment):
```html
<div class="alert alert-info">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
    </svg>
    <span>Synchronization started. Fetching albums...</span>
</div>
```

**Behavior**:
- Creates `SyncOperation` record with `status='pending'`
- Spawns background thread to run sync
- Returns immediately (non-blocking)
- `HX-Trigger: syncStarted` event triggers frontend to start polling

**Corresponds to**:
- **FR-001**: Trigger sync via button
- **FR-003**: Full synchronization starts
- **SC-001**: Response within 1 second

---

### Response: Error - Sync Already Running (409 Conflict)

**Status Code**: `409 Conflict`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
HX-Retarget: #sync-status
HX-Reswap: innerHTML
```

**Body** (HTML Fragment):
```html
<div class="alert alert-warning">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
    <span>Synchronization already in progress. Please wait for it to complete.</span>
</div>
```

**Corresponds to**:
- **FR-002**: Prevent concurrent syncs
- **SC-007**: 100% prevention of duplicate operations

---

### Response: Error - Missing Credentials (503 Service Unavailable)

**Status Code**: `503 Service Unavailable`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
```

**Body** (HTML Fragment):
```html
<div class="alert alert-error">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div>
        <div class="font-bold">Configuration Error</div>
        <div class="text-sm">Spotify credentials not configured. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.</div>
    </div>
</div>
```

**Corresponds to**:
- **FR-007**: Clear error messages
- **US-003** (Acceptance 1): Missing credentials error

---

### Response: Error - Network/External Service Failure (502 Bad Gateway)

**Status Code**: `502 Bad Gateway`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
```

**Body** (HTML Fragment):
```html
<div class="alert alert-error">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div>
        <div class="font-bold">Network Error</div>
        <div class="text-sm">Unable to reach external services. Please check your network connection and try again.</div>
    </div>
</div>
```

**Corresponds to**:
- **FR-007**: Clear error messages
- **US-003** (Acceptance 2): Network error handling

---

## Endpoint 2: Get Sync Status (Polling)

### Request

**Method**: `GET`

**URL**: `/catalog/sync/status/`

**URL Pattern** (Django): `path('sync/status/', views.sync_status, name='sync-status')`

**Headers**:
```http
HX-Request: true
```

**Query Parameters**: None

**Authentication**: None (Phase 1)

**Polling Interval**: Every 2 seconds (configured in frontend HTMX `hx-trigger="every 2s"`)

**Example**:
```http
GET /catalog/sync/status/ HTTP/1.1
Host: localhost:8000
HX-Request: true
```

---

### Response: Sync in Progress

**Status Code**: `200 OK`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
```

**Body** (HTML Fragment):
```html
<div class="flex items-center gap-4">
    <!-- Progress spinner -->
    <span class="loading loading-spinner loading-md"></span>

    <!-- Status message -->
    <div class="flex-1">
        <div class="font-semibold">Syncing album 15 of 47...</div>
        <div class="text-sm text-base-content/70">Processing albums from Google Sheets and Spotify</div>

        <!-- Progress bar -->
        <progress class="progress progress-primary w-full mt-2" value="32" max="100"></progress>
        <div class="text-xs text-base-content/60 mt-1">32% complete • Started 1 minute ago</div>
    </div>
</div>
```

**Data Source**:
```python
sync_op = SyncOperation.objects.filter(
    Q(status='pending') | Q(status='running')
).order_by('-started_at').first()

context = {
    'stage_message': sync_op.stage_message,
    'albums_processed': sync_op.albums_processed,
    'total_albums': sync_op.total_albums,
    'progress_percentage': sync_op.progress_percentage(),
    'duration': sync_op.duration(),
}
```

**Corresponds to**:
- **FR-004**: Real-time status updates
- **FR-005**: Album count display
- **SC-002**: Updates every 2 seconds
- **US-002**: View synchronization progress

---

### Response: Sync Complete (Success)

**Status Code**: `200 OK`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
HX-Trigger: syncCompleted, stopPolling
```

**Body** (HTML Fragment):
```html
<div class="alert alert-success">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div>
        <div class="font-bold">Sync Complete!</div>
        <div class="text-sm">Updated 47 albums successfully. Completed in 2 minutes, 15 seconds.</div>
    </div>
</div>
```

**Headers Explained**:
- `HX-Trigger: syncCompleted` - Triggers frontend to refresh album list
- `HX-Trigger: stopPolling` - Stops HTMX polling (sync is done)

**Corresponds to**:
- **FR-006**: Success message with album count
- **FR-010**: Re-enable sync button
- **FR-012**: Update catalog automatically

---

### Response: Sync Failed (Error)

**Status Code**: `200 OK` (still return HTML, error is in content)

**Headers**:
```http
Content-Type: text/html; charset=utf-8
HX-Trigger: syncFailed, stopPolling
```

**Body** (HTML Fragment):
```html
<div class="alert alert-error">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div>
        <div class="font-bold">Sync Failed</div>
        <div class="text-sm">Unable to fetch data from Google Sheets: Connection timeout. Please try again.</div>
    </div>
</div>
```

**Data Source**:
```python
sync_op = SyncOperation.objects.filter(status='failed').order_by('-started_at').first()
context = {
    'error_message': sync_op.error_message,
}
```

**Corresponds to**:
- **FR-007**: Clear error messages
- **FR-010**: Re-enable sync button (via `stopPolling` trigger)
- **US-003**: Error handling

---

### Response: Sync Complete with Warnings (Partial Success)

**Status Code**: `200 OK`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
HX-Trigger: syncCompleted, stopPolling
```

**Body** (HTML Fragment):
```html
<div class="alert alert-warning">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
    <div>
        <div class="font-bold">Sync Completed with Warnings</div>
        <div class="text-sm">45 of 50 albums updated successfully. 5 failed due to Spotify API errors.</div>
    </div>
</div>
```

**Corresponds to**:
- **FR-008**: Partial failure handling
- **US-003** (Acceptance 3): Partial success display

---

### Response: No Sync Active

**Status Code**: `200 OK`

**Headers**:
```http
Content-Type: text/html; charset=utf-8
```

**Body** (HTML Fragment):
```html
<div class="text-sm text-base-content/70">
    No synchronization in progress.
</div>
```

**When**: No `SyncOperation` with `status='pending'` or `status='running'` exists

**Corresponds to**: Initial state before first sync, or idle state after completion

---

## Endpoint 3: Get Last Sync Timestamp (Embedded in Page Load)

### Request

**Method**: `GET`

**URL**: `/catalog/albums/` (main catalog page)

**Note**: This is not a separate endpoint. The timestamp is embedded in the initial page HTML, not polled separately.

---

### Response: Page Load with Last Sync Info

**Status Code**: `200 OK`

**Embedded HTML** (within `album_list.html`):
```html
<div class="text-sm text-base-content/70" data-timestamp="{{ last_sync.sync_timestamp.isoformat }}">
    Last synced: <span class="timeago">2 hours ago</span>
</div>

<script>
// JavaScript updates relative time every minute
function updateTimeago() {
    const elem = document.querySelector('[data-timestamp]');
    if (!elem) return;

    const timestamp = new Date(elem.dataset.timestamp);
    const now = new Date();
    const diffMs = now - timestamp;
    const diffMins = Math.floor(diffMs / 60000);

    let relativeTime;
    if (diffMins < 1) relativeTime = 'just now';
    else if (diffMins < 60) relativeTime = `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    else if (diffMins < 1440) relativeTime = `${Math.floor(diffMins / 60)} hour${Math.floor(diffMins / 60) > 1 ? 's' : ''} ago`;
    else relativeTime = `${Math.floor(diffMins / 1440)} day${Math.floor(diffMins / 1440) > 1 ? 's' : ''} ago`;

    elem.querySelector('.timeago').textContent = relativeTime;
}

updateTimeago();
setInterval(updateTimeago, 60000);  // Update every minute
</script>
```

**Data Source**:
```python
last_sync = SyncRecord.objects.filter(success=True).order_by('-sync_timestamp').first()
context = {
    'last_sync': last_sync,
}
```

**Corresponds to**:
- **FR-009**: Display last sync timestamp
- **US-004**: View last synchronization timestamp
- **SC-006**: Visible within 2 seconds of page load

---

## Error Response Format (General)

All error responses follow DaisyUI alert component pattern:

```html
<div class="alert alert-{type}">
    <svg><!-- Icon --></svg>
    <div>
        <div class="font-bold">{Error Title}</div>
        <div class="text-sm">{Detailed explanation and remediation advice}</div>
    </div>
</div>
```

**Alert Types**:
- `alert-info`: Informational (sync starting)
- `alert-success`: Success (sync complete)
- `alert-warning`: Warning (partial success)
- `alert-error`: Error (sync failed, missing config)

---

## HTMX Integration Summary

### Sync Button Component

```html
<button class="btn btn-primary"
        hx-post="/catalog/sync/trigger/"
        hx-target="#sync-status"
        hx-swap="innerHTML"
        hx-disabled-elt="this"
        hx-indicator="#sync-spinner">
    <span id="sync-spinner" class="loading loading-spinner loading-sm htmx-indicator"></span>
    Sync Now
</button>

<div id="sync-status"
     hx-get="/catalog/sync/status/"
     hx-trigger="syncStarted from:body, every 2s"
     hx-swap="innerHTML">
    <!-- Status updates appear here -->
</div>
```

**Flow**:
1. User clicks "Sync Now" → POST to `/catalog/sync/trigger/`
2. Server returns 202 with `HX-Trigger: syncStarted`
3. `syncStarted` event triggers initial status poll
4. HTMX polls `/catalog/sync/status/` every 2 seconds
5. When sync completes, server returns `HX-Trigger: stopPolling`
6. Polling stops, button re-enables

---

## Testing Contracts

**Contract Tests Required**:

1. **POST /catalog/sync/trigger/** returns 202 when no active sync
2. **POST /catalog/sync/trigger/** returns 409 when sync already running
3. **POST /catalog/sync/trigger/** returns 503 when credentials missing
4. **GET /catalog/sync/status/** returns in-progress HTML when sync running
5. **GET /catalog/sync/status/** returns success HTML when sync completes
6. **GET /catalog/sync/status/** returns failure HTML when sync fails
7. **GET /catalog/sync/status/** returns "no sync" HTML when idle
8. Response headers include correct `HX-Trigger` values
9. HTML fragments are valid and render correctly
10. CSRF token validation works on POST endpoint

---

## Summary

**Endpoints Defined**: 2 (trigger, status) + 1 embedded (last sync)
**HTTP Methods**: POST, GET
**Response Format**: HTML fragments (not JSON)
**Status Codes**: 200, 202, 409, 502, 503
**HTMX Features**: Polling, triggers, swapping, headers
**Error Handling**: 5 error scenarios covered

**Contracts Status**: ✅ Complete and ready for implementation