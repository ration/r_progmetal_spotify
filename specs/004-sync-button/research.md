# Research: Synchronization Button with Status Display

**Feature**: 004-sync-button
**Date**: 2025-11-04
**Purpose**: Resolve technical uncertainties and establish implementation approach for sync button with real-time status updates

## Research Questions

### 1. Real-Time Update Mechanism (SSE vs Polling vs WebSockets)

**Question**: What is the best approach for delivering real-time sync status updates to the browser?

**Options Evaluated**:

1. **HTTP Polling with HTMX** (RECOMMENDED)
   - Browser sends GET request to `/catalog/sync-status/` every 2 seconds
   - Server returns HTML fragment with current status
   - HTMX `hx-trigger="every 2s"` automatically handles polling
   - Polling stops when sync completes (server returns `HX-Trigger: stopPolling` header)

2. **Server-Sent Events (SSE)**
   - Unidirectional server-to-client event stream
   - Requires Django Channels or third-party library (django-sse)
   - HTMX supports SSE via `hx-sse` extension
   - More complex setup, additional dependencies

3. **WebSockets**
   - Bidirectional communication
   - Requires Django Channels + Redis/ASGI server
   - Overkill for one-way status updates
   - Significant complexity increase

**Decision**: **HTTP Polling with HTMX**

**Rationale**:
- Simplest implementation with zero additional dependencies
- HTMX built-in support for polling (`hx-trigger="every 2s"`)
- Fits existing architecture (no Channels/ASGI required)
- 2-second polling interval acceptable for user experience (SC-002: updates every 2s)
- Polling automatically stops when server indicates completion
- Browser compatibility: works everywhere HTTP works
- Stateless: no persistent connections, easier to scale

**Alternatives Considered**:
- SSE: Better real-time experience but requires additional dependencies and ASGI compatibility
- WebSockets: Too complex for unidirectional updates, requires infrastructure changes

**Implementation Details**:
```html
<!-- Status display polls every 2 seconds while sync is active -->
<div id="sync-status"
     hx-get="/catalog/sync-status/"
     hx-trigger="every 2s"
     hx-swap="innerHTML">
    <!-- Server returns status HTML here -->
</div>
```

Server response headers when sync completes:
```python
response = render(request, 'catalog/components/sync_status.html', context)
response['HX-Trigger'] = 'stopPolling'  # HTMX stops polling
return response
```

---

### 2. Background Task Execution

**Question**: How should long-running sync operations execute without blocking HTTP requests?

**Options Evaluated**:

1. **Synchronous View with Thread** (RECOMMENDED for MVP)
   - Django view spawns `threading.Thread` to run sync in background
   - HTTP response returns immediately
   - Thread updates `SyncOperation` model with progress
   - Polling endpoint reads `SyncOperation` status from database

2. **Celery Task Queue**
   - Dedicated task queue with workers
   - Robust, production-ready
   - Requires Redis/RabbitMQ, additional infrastructure
   - Complex setup for single feature

3. **Django Q or Huey**
   - Lighter-weight task queues
   - Still require additional processes/dependencies

**Decision**: **Synchronous View with Thread (MVP), migrate to Celery later if needed**

**Rationale**:
- Simplest approach: no new dependencies or infrastructure
- Threading is built into Python standard library
- Sufficient for single-user/admin use case (1-2 concurrent syncs max)
- Database-backed status persistence works with threading
- Easy migration path to Celery if scale demands it
- Aligns with Constitution Principle V (incremental delivery)

**Trade-offs**:
- Threads share memory with Django process (less isolated than Celery)
- Limited to single server (no distributed workers)
- Acceptable for current scale (100s of albums, 1-2 admins)

**Implementation Pattern**:
```python
def sync_trigger_view(request):
    # Create SyncOperation record
    sync_op = SyncOperation.objects.create(status='pending')

    # Start sync in background thread
    thread = threading.Thread(target=run_sync, args=(sync_op.id,))
    thread.daemon = True
    thread.start()

    # Return immediately
    return HttpResponse("Sync started", status=202)

def run_sync(sync_op_id):
    # Update status as sync progresses
    # Write to database, polling endpoint reads it
    pass
```

---

### 3. Concurrent Sync Prevention

**Question**: How do we prevent multiple simultaneous sync operations?

**Options Evaluated**:

1. **Database-Level Lock with `select_for_update()`** (RECOMMENDED)
   - Query for active `SyncOperation` with status='running'
   - Use `select_for_update(nowait=True)` to acquire row lock
   - If lock fails, return "Sync already in progress" error
   - Atomic and race-condition safe

2. **Django Cache Lock**
   - Set cache key `sync_lock` when sync starts
   - Check/set atomically with cache backend
   - Requires Redis/Memcached for production
   - Works but less integrated with data model

3. **File-Based Lock**
   - Lock file on filesystem
   - Works but less portable (Docker volumes, permissions)

**Decision**: **Database-Level Lock with `select_for_update()`**

**Rationale**:
- Leverages existing PostgreSQL/SQLite database
- Atomic operations prevent race conditions
- Integrated with `SyncOperation` model (no separate locking mechanism)
- Supports both PostgreSQL and SQLite
- Most reliable approach for correctness (SC-007: 100% prevention)

**Implementation**:
```python
from django.db import transaction
from django.db.models import Q

with transaction.atomic():
    # Check for active sync
    active_sync = SyncOperation.objects.filter(
        Q(status='pending') | Q(status='running')
    ).select_for_update(nowait=True).first()

    if active_sync:
        return HttpResponseConflict("Sync already in progress")

    # Create new sync operation
    sync_op = SyncOperation.objects.create(status='pending')
```

---

### 4. Progress Tracking Granularity

**Question**: How should the sync process report progress to the status display?

**Decision**: **Stage-based progress with album count**

**Stages**:
1. **Fetching from Google Sheets** (10% of time)
   - Status: "Fetching albums from Google Sheets..."
   - No album count yet

2. **Processing Albums** (80% of time)
   - Status: "Syncing album 15 of 47..."
   - Update every N albums (e.g., every 5 albums)

3. **Finalizing** (10% of time)
   - Status: "Finalizing synchronization..."
   - Updating statistics, cleanup

**Rationale**:
- Matches user stories in spec (US-002: stage visibility)
- Balances detail vs. database write frequency
- Provides meaningful progress indicators
- Easy to implement with progress callbacks

**Implementation**:
```python
class SyncOperation(models.Model):
    status = models.CharField(max_length=20)  # pending, running, completed, failed
    stage = models.CharField(max_length=50)   # 'fetching', 'processing', 'finalizing'
    stage_message = models.CharField(max_length=200)  # Display text
    albums_processed = models.IntegerField(default=0)
    total_albums = models.IntegerField(null=True)
    error_message = models.TextField(blank=True)
```

---

### 5. Timestamp Display and Auto-Update

**Question**: How should "Last synced: X ago" update in real-time?

**Options Evaluated**:

1. **Client-Side JavaScript** (RECOMMENDED)
   - Server sends timestamp as data attribute
   - JavaScript calculates relative time ("2 hours ago")
   - Updates every minute without server requests

2. **Server-Side with Polling**
   - Server recalculates on every status poll
   - More server load, same UX

**Decision**: **Client-Side JavaScript for relative time**

**Rationale**:
- Reduces server load (no calculation on every poll)
- Better UX: timestamp updates smoothly every minute
- Standard pattern (GitHub, Twitter use this approach)
- Easy to implement with libraries like `timeago.js` or vanilla JS

**Implementation**:
```html
<div class="last-sync" data-timestamp="{{ last_sync.sync_timestamp.isoformat }}">
    Last synced: <span class="timeago"></span>
</div>

<script>
// Update relative time every minute
function updateTimeago() {
    const timestamp = document.querySelector('.last-sync').dataset.timestamp;
    const relativeTime = calculateRelativeTime(new Date(timestamp));
    document.querySelector('.timeago').textContent = relativeTime;
}
setInterval(updateTimeago, 60000);  // Update every minute
updateTimeago();  // Initial update
</script>
```

---

## Best Practices

### Django + HTMX Real-Time Updates
- Use `hx-trigger="every Ns"` for polling
- Return `HX-Trigger: stopPolling` header when done
- Keep poll interval >= 1s to avoid server overload
- Use partial templates for status fragments

### Threading in Django Views
- Always use `daemon=True` threads (terminate with main process)
- Never access request object from thread (pass IDs, not objects)
- Use database transactions for thread-safe state updates
- Log exceptions within threads (they don't propagate to view)

### Progress Tracking Patterns
- Update database every N items, not every item (reduces I/O)
- Use separate progress model (`SyncOperation`) from result model (`SyncRecord`)
- Store structured progress (stage, count) not just free-text messages
- Write final results to separate model when complete

### Error Handling
- Catch all exceptions in background thread
- Store error details in `SyncOperation.error_message`
- Set status to 'failed' so UI can display error
- Preserve partial results where possible (don't roll back on partial failure)

---

## Dependencies Summary

**No new dependencies required**:
- HTTP polling: Built into HTMX (already in project)
- Threading: Python standard library
- Database locking: Django ORM feature
- Relative time display: Vanilla JavaScript (or optional: `timeago.js` CDN)

**Rationale**: Aligns with Constitution Principle (keep it simple). All required functionality available in existing stack.

---

## References

- HTMX Polling Documentation: https://htmx.org/docs/#polling
- Django select_for_update(): https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
- Python Threading: https://docs.python.org/3/library/threading.html
- Relative Time Display: https://github.com/hustcc/timeago.js (optional)

---

## Decisions Summary

| Question | Decision | Key Rationale |
|----------|----------|---------------|
| Real-time updates | HTTP Polling (HTMX) | Simplest, no new dependencies, fits existing architecture |
| Background execution | Threading (MVP) | Built-in, sufficient for scale, easy Celery migration later |
| Concurrent prevention | DB lock (`select_for_update`) | Atomic, race-condition safe, integrated with model |
| Progress granularity | Stage + album count | Meaningful to users, balances detail vs. writes |
| Timestamp updates | Client-side JS | Reduces server load, smooth UX, standard pattern |

**All NEEDS CLARIFICATION items resolved. Ready for Phase 1: Design & Contracts.**
