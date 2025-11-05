# Quickstart Guide: Synchronization Button with Status Display

**Feature**: 004-sync-button
**Branch**: `004-sync-button`
**Prerequisites**: Album catalog feature (001-album-catalog) must be implemented and working

## Overview

This guide helps you get the synchronization button feature up and running quickly. Follow these steps in order to implement and test the feature.

---

## Step 1: Checkout Feature Branch

```bash
git checkout 004-sync-button
```

**Verify you're on the correct branch**:
```bash
git branch --show-current
# Should output: 004-sync-button
```

---

## Step 2: Review Documentation

Before coding, read these documents in order:

1. **spec.md** - Understand user stories and requirements
2. **research.md** - Technical decisions and rationale
3. **data-model.md** - Database schema and entities
4. **contracts/http-endpoints.md** - API contracts

**Estimated reading time**: 20-30 minutes

---

## Step 3: Create Database Migration

Generate the migration for the `SyncOperation` model:

```bash
python manage.py makemigrations catalog
```

**Expected output**:
```
Migrations for 'catalog':
  catalog/migrations/000X_add_syncoperation.py
    - Create model SyncOperation
```

**Apply the migration**:
```bash
python manage.py migrate catalog
```

**Verify migration applied**:
```bash
python manage.py showmigrations catalog
```

Should show `[X]` next to the new migration.

---

## Step 4: Run Type Checking and Linting

Before implementing, ensure your environment is ready:

```bash
# Type checking
pyright

# Linting
ruff check .

# Formatting
ruff format .
```

**Expected**: All checks should pass initially (no new code yet).

---

## Step 5: Implementation Order (User Story Sequence)

Implement features in priority order to enable incremental testing:

### Phase 1: P1 - Trigger Manual Synchronization

**Goal**: Users can click a button to start sync

**Files to create/modify**:
1. `catalog/models.py` - Add `SyncOperation` model
2. `catalog/services/sync_manager.py` - Sync orchestration (new file)
3. `catalog/views.py` - Add `sync_trigger` view
4. `catalog/urls.py` - Add sync trigger endpoint
5. `catalog/templates/catalog/components/sync_button.html` - Button component (new)
6. `catalog/templates/catalog/album_list.html` - Include button component

**Test manually**:
```bash
python manage.py runserver
# Visit http://localhost:8000/catalog/albums/
# Click "Sync Now" button
# Check database: SELECT * FROM catalog_syncoperation;
```

**Acceptance criteria**: Button click creates `SyncOperation` record and starts background sync.

---

### Phase 2: P2 - View Synchronization Progress

**Goal**: Show real-time status updates during sync

**Files to create/modify**:
1. `catalog/views.py` - Add `sync_status` view
2. `catalog/urls.py` - Add sync status endpoint
3. `catalog/templates/catalog/components/sync_status.html` - Status display (new)
4. `catalog/services/sync_manager.py` - Add progress callbacks
5. Update sync button template to include status polling

**Test manually**:
```bash
python manage.py runserver
# Visit http://localhost:8000/catalog/albums/
# Click "Sync Now" button
# Observe status updates every 2 seconds
# Check: "Fetching..." → "Syncing album X of Y..." → "Complete!"
```

**Acceptance criteria**: Status updates appear in real-time with progress counts.

---

### Phase 3: P2 - Handle Synchronization Errors

**Goal**: Display clear error messages for failures

**Files to modify**:
1. `catalog/services/sync_manager.py` - Add error handling and recovery
2. `catalog/views.py` - Add error response handling
3. `catalog/templates/catalog/components/sync_status.html` - Add error states

**Test manually**:
```bash
# Test 1: Missing credentials
unset SPOTIFY_CLIENT_ID
python manage.py runserver
# Click "Sync Now" → Should show "Credentials not configured" error

# Test 2: Network failure (simulate by blocking network)
# Click "Sync Now" → Should show "Network error" message

# Test 3: Partial failure (modify test data to cause some albums to fail)
# Click "Sync Now" → Should show "45/50 succeeded, 5 failed" warning
```

**Acceptance criteria**: All error scenarios display clear, actionable messages.

---

### Phase 4: P3 - View Last Synchronization Timestamp

**Goal**: Show "Last synced: X ago" on page load

**Files to modify**:
1. `catalog/templatetags/catalog_extras.py` - Add `timeago` filter (optional, or use JS)
2. `catalog/templates/catalog/album_list.html` - Add timestamp display
3. `catalog/views.py` - Pass `last_sync` to template context

**Test manually**:
```bash
python manage.py runserver
# Visit http://localhost:8000/catalog/albums/
# Should see "Last synced: X minutes ago" near sync button
# Wait 1 minute, refresh, check timestamp updates
```

**Acceptance criteria**: Timestamp appears and updates automatically every minute.

---

## Step 6: Run Automated Tests

After implementing each phase, run the test suite:

```bash
# Run all tests
pytest

# Run specific test file (example)
pytest tests/test_sync_trigger.py -v

# Run with coverage
pytest --cov=catalog --cov-report=html
```

**Minimum test coverage**: 80% for new code (sync views, sync_manager service)

---

## Step 7: Manual Integration Testing

Test the complete user journey:

### Test Case 1: Successful Sync
1. Clear existing sync records: `python manage.py shell` → `SyncOperation.objects.all().delete()`
2. Start server: `python manage.py runserver`
3. Visit catalog page: `http://localhost:8000/catalog/albums/`
4. Click "Sync Now" button
5. Verify:
   - Button disables immediately
   - Status shows "Fetching from Google Sheets..."
   - Progress updates every 2 seconds
   - Final message: "Sync complete! Updated X albums"
   - Album tiles refresh automatically
   - "Last synced: just now" appears

### Test Case 2: Concurrent Sync Prevention
1. Open two browser tabs to catalog page
2. Click "Sync Now" in Tab 1
3. Immediately click "Sync Now" in Tab 2
4. Verify: Tab 2 shows "Sync already in progress" warning

### Test Case 3: Error Recovery
1. Stop the server mid-sync (simulate crash)
2. Restart server
3. Check database: `SyncOperation` should have `status='running'`
4. Manual cleanup or automatic timeout handling (depends on implementation)

### Test Case 4: Page Refresh During Sync
1. Click "Sync Now" button
2. While sync is running, refresh the page (F5)
3. Verify: Status display immediately shows in-progress sync

---

## Step 8: Performance Validation

Verify success criteria from spec:

```bash
# SC-001: Trigger response < 1 second
time curl -X POST http://localhost:8000/catalog/sync/trigger/
# Should complete in < 1s

# SC-002: Status updates every 2 seconds
# Observe network tab in browser DevTools during sync
# Check: GET /catalog/sync/status/ every ~2s

# SC-003: Sync 50 albums in < 5 minutes
# Run full sync and time it
# Import 50 albums, measure duration
```

---

## Step 9: Code Quality Validation

Before committing, ensure all quality checks pass:

```bash
# Type checking (zero errors)
pyright

# Linting (zero errors)
ruff check .

# Formatting
ruff format .

# Tests (all passing)
pytest

# Check for missing docstrings
ruff check --select D
```

**Constitution Compliance**: All checks must pass (Principle II: Type Safety & Code Quality)

---

## Step 10: Commit Changes

Follow git commit best practices:

```bash
# Stage changes
git add catalog/models.py catalog/views.py catalog/services/sync_manager.py
git add catalog/templates/catalog/components/sync_*.html
git add catalog/urls.py tests/test_sync_*.py

# Check status
git status

# Commit with descriptive message
git commit -m "Implement User Stories 1-4: Sync button with real-time status (004-sync-button)

- Add SyncOperation model for progress tracking
- Implement sync trigger and status polling endpoints
- Add HTMX-based real-time status updates (2s polling)
- Handle errors with clear user-facing messages
- Display last sync timestamp with auto-updating relative time
- Prevent concurrent sync operations with DB locks
- Add comprehensive test coverage for sync workflows

Closes: FR-001 through FR-012
User Stories: P1 (trigger), P2 (progress, errors), P3 (timestamp)"
```

---

## Troubleshooting

### Issue: Migration fails with "relation already exists"

**Solution**: Check if migration was already applied
```bash
python manage.py showmigrations catalog
# If already applied, skip migration step
```

---

### Issue: Button click does nothing

**Debug steps**:
1. Check browser console for JavaScript errors
2. Verify HTMX is loaded: `<script src="https://unpkg.com/htmx.org@..."></script>`
3. Check Django logs for POST request: `python manage.py runserver` output
4. Verify URL mapping: `python manage.py show_urls | grep sync`

---

### Issue: Status polling doesn't stop

**Debug steps**:
1. Check response headers in Network tab: Should include `HX-Trigger: stopPolling`
2. Verify `SyncOperation.status` is set to `'completed'` or `'failed'`
3. Check Django view returns correct header:
   ```python
   response['HX-Trigger'] = 'stopPolling'
   ```

---

### Issue: "Sync already in progress" error even when no sync is running

**Solution**: Clean up stale `SyncOperation` records
```bash
python manage.py shell

from catalog.models import SyncOperation
# Check for stuck syncs
SyncOperation.objects.filter(status='running')

# Manual cleanup (if needed)
SyncOperation.objects.filter(status__in=['pending', 'running']).delete()
```

**Future**: Implement automatic timeout/cleanup (10 minute timeout for stuck syncs)

---

## Environment Setup Checklist

- [ ] Python 3.14 installed
- [ ] Django 5.2.8 installed (`uv sync`)
- [ ] PostgreSQL running (Docker or local)
- [ ] Spotify credentials configured (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`)
- [ ] Google Sheets URL configured (`GOOGLE_SHEETS_XLSX_URL`)
- [ ] Database migrations applied (`python manage.py migrate`)
- [ ] Test data available (`tests/testdata/2025.csv`)

---

## Next Steps

After completing this feature:

1. **Merge to main**: Create pull request, get code review
2. **Update documentation**: Add to `README.md` and `CLAUDE.md`
3. **Deploy to production**: Follow deployment checklist
4. **Monitor**: Check logs for sync errors, performance metrics

---

## Related Documentation

- **Specification**: [spec.md](./spec.md)
- **Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contracts**: [contracts/http-endpoints.md](./contracts/http-endpoints.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Task List**: [tasks.md](./tasks.md) (generated by `/speckit.tasks`)

---

## Estimated Timeline

- **Phase 1 (P1 - Trigger)**: 2-3 hours
- **Phase 2 (P2 - Progress)**: 3-4 hours
- **Phase 3 (P2 - Errors)**: 2-3 hours
- **Phase 4 (P3 - Timestamp)**: 1-2 hours
- **Testing & Polish**: 2-3 hours

**Total**: 10-15 hours for complete implementation and testing

---

**Quickstart Guide Status**: ✅ Complete and ready for implementation