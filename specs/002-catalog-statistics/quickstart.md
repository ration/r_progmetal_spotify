# Quickstart: Catalog Statistics

**Feature**: Display synchronization statistics on catalog page
**Date**: 2025-11-03
**Status**: Ready for implementation

## Overview

This quickstart guide provides manual testing procedures for the catalog statistics feature. Follow these steps to verify all user stories work correctly after implementation.

## Prerequisites

Before testing, ensure:

1. **Development environment running**:
   ```bash
   # Docker setup
   make up

   # OR local development
   python manage.py runserver
   ```

2. **Database migrated**:
   ```bash
   python manage.py migrate
   ```

3. **Django humanize app enabled** in `config/settings.py`:
   ```python
   INSTALLED_APPS = [
       # ... existing apps ...
       'django.contrib.humanize',
   ]
   ```

4. **Spotify credentials configured** in `.env`:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   GOOGLE_SHEETS_XLSX_URL=https://docs.google.com/...
   ```

## Testing Scenarios

### Scenario 1: First Time User (Never Synchronized)

**User Story**: P1 - View Catalog Freshness
**Acceptance Criteria**: Display "Not yet synchronized" when no sync has occurred

#### Steps

1. **Start with empty SyncRecord table**:
   ```bash
   python manage.py shell
   >>> from catalog.models import SyncRecord
   >>> SyncRecord.objects.all().delete()
   >>> exit()
   ```

2. **Visit catalog page**:
   ```
   http://localhost:8000/catalog/albums/
   ```

3. **Verify display**:
   - ✅ Statistics panel visible above filters
   - ✅ Text shows "Not yet synchronized" or similar message
   - ✅ Total albums shows "0 albums" or current count if albums exist
   - ✅ No "new albums" indicator shown

**Expected Result**: User sees clear indication that catalog has never been synced.

---

### Scenario 2: After First Synchronization

**User Story**: P1 - View Catalog Freshness, P2 - View Total Catalog Size
**Acceptance Criteria**: Display sync time and total album count

#### Steps

1. **Run import command** (limit to 3 albums for speed):
   ```bash
   python manage.py import_albums --limit 3
   ```

2. **Verify command output**:
   ```
   Expected output:
   Created: 3 albums
   Updated: 0 albums
   Skipped: 0 albums
   Total albums in catalog: 3
   ```

3. **Visit catalog page** immediately after sync:
   ```
   http://localhost:8000/catalog/albums/
   ```

4. **Verify display**:
   - ✅ "Last synchronized: X seconds ago" or "X minutes ago"
   - ✅ "Total: 3 albums" (with no thousands separator for small numbers)
   - ✅ "+3 new" indicator displayed

**Expected Result**: User sees fresh sync timestamp (< 1 minute ago) and correct album count.

---

### Scenario 3: Relative Time Display (< 24 Hours)

**User Story**: P1 - View Catalog Freshness
**Acceptance Criteria**: Syncs within 24 hours show relative time ("2 hours ago")

#### Steps

1. **Wait 2 minutes** after previous sync (or manually set sync_timestamp if testing quickly)

2. **Refresh catalog page**:
   ```
   http://localhost:8000/catalog/albums/
   ```

3. **Verify relative time format**:
   - ✅ "Last synchronized: 2 minutes ago" (not absolute date/time)
   - ✅ Humanreadable format (no "120 seconds ago")

4. **Test with older sync** (optional - requires waiting or manual DB edit):
   ```bash
   # Manually set sync_timestamp to 5 hours ago
   python manage.py shell
   >>> from catalog.models import SyncRecord
   >>> from datetime import timedelta
   >>> from django.utils import timezone
   >>> sync = SyncRecord.objects.first()
   >>> sync.sync_timestamp = timezone.now() - timedelta(hours=5)
   >>> sync.save(update_fields=['sync_timestamp'])
   >>> exit()
   ```

5. **Refresh page** and verify:
   - ✅ "Last synchronized: 5 hours ago"

**Expected Result**: Recent syncs display in human-friendly relative time.

---

### Scenario 4: Absolute Time Display (> 24 Hours)

**User Story**: P1 - View Catalog Freshness
**Acceptance Criteria**: Syncs older than 24 hours show absolute date/time

#### Steps

1. **Set sync_timestamp to yesterday**:
   ```bash
   python manage.py shell
   >>> from catalog.models import SyncRecord
   >>> from datetime import timedelta
   >>> from django.utils import timezone
   >>> sync = SyncRecord.objects.first()
   >>> sync.sync_timestamp = timezone.now() - timedelta(hours=30)
   >>> sync.save(update_fields=['sync_timestamp'])
   >>> exit()
   ```

2. **Refresh catalog page**

3. **Verify absolute time format**:
   - ✅ "Last synchronized: Nov. 2, 2025, 4:30 p.m." (or similar absolute format)
   - ✅ NOT "30 hours ago"

**Expected Result**: Old syncs display full date/time for clarity.

---

### Scenario 5: Large Album Catalog (Thousands Separator)

**User Story**: P2 - View Total Catalog Size
**Acceptance Criteria**: Numbers formatted with thousands separators (1,247)

#### Steps

1. **Run full import** (imports 2,000+ albums):
   ```bash
   # This takes ~10 minutes due to Spotify API rate limits
   python manage.py import_albums
   ```

2. **Visit catalog page after import completes**

3. **Verify number formatting**:
   - ✅ Total shows "2,147 albums" (with comma separator)
   - ✅ NOT "2147 albums" (no separator)
   - ✅ "+2,147 new" also uses separator

**Expected Result**: Large numbers are readable with proper formatting.

---

### Scenario 6: Subsequent Sync with New Albums

**User Story**: P3 - See Recent Growth
**Acceptance Criteria**: Display count of albums added in latest sync

#### Steps

1. **Run sync again** (should add new albums if source updated):
   ```bash
   python manage.py import_albums --sync
   ```

2. **Note output counts**:
   ```
   Example output:
   Created: 15 albums
   Updated: 10 albums
   Skipped: 2125 albums
   Total albums in catalog: 2150
   ```

3. **Refresh catalog page**

4. **Verify display**:
   - ✅ "Last synchronized: X seconds ago" (updated timestamp)
   - ✅ "Total: 2,150 albums" (new total)
   - ✅ "+15 new" (only shows created, not updated)

**Expected Result**: Statistics update to reflect latest sync, showing only newly created albums.

---

### Scenario 7: Sync with Zero New Albums

**User Story**: P3 - See Recent Growth
**Acceptance Criteria**: Show "+0 new" or hide indicator when no albums added

#### Steps

1. **Run sync immediately after previous sync**:
   ```bash
   python manage.py import_albums --sync
   ```

2. **Verify command output**:
   ```
   Expected:
   Created: 0 albums
   Updated: 0 albums (or some updates)
   Skipped: 2150 albums
   ```

3. **Refresh catalog page**

4. **Verify display**:
   - ✅ "Last synchronized: X seconds ago" (updated)
   - ✅ "Total: 2,150 albums" (unchanged)
   - ✅ "+0 new" displayed OR growth indicator hidden (implementation choice)

**Expected Result**: User understands no new content was added.

---

### Scenario 8: HTMX Filter Interaction

**User Story**: All stories (verify statistics remain visible during filtering)
**Acceptance Criteria**: Statistics panel unchanged when filters applied

#### Steps

1. **Navigate to catalog page with statistics visible**

2. **Apply genre filter**:
   - Click genre dropdown
   - Select "Djent" or any genre

3. **Observe behavior**:
   - ✅ Album tiles update (HTMX partial update)
   - ✅ Statistics panel remains unchanged
   - ✅ No flicker or reload of statistics
   - ✅ Same "Last synchronized" timestamp displayed

4. **Apply vocal style filter**:
   - Select "Clean Vocals" or any vocal style

5. **Verify**:
   - ✅ Statistics still show total catalog count (not filtered count)
   - ✅ Statistics panel did not re-render

6. **Clear filters**:
   - Reset filters to "All"

7. **Verify**:
   - ✅ Statistics remain unchanged

**Expected Result**: Filtering albums does not affect statistics display (statistics show catalog-wide data, not filtered subset).

---

### Scenario 9: Empty Catalog

**User Story**: P2 - View Total Catalog Size
**Acceptance Criteria**: Handle empty catalog gracefully

#### Steps

1. **Delete all albums** (use test database):
   ```bash
   python manage.py shell
   >>> from catalog.models import Album
   >>> Album.objects.all().delete()
   >>> exit()
   ```

2. **Visit catalog page**

3. **Verify display**:
   - ✅ "Last synchronized: [time]" (if sync record exists)
   - ✅ "Total: 0 albums" (with proper formatting)
   - ✅ No crash or error
   - ✅ "+0 new" or no growth indicator

**Expected Result**: System handles edge case without errors.

---

### Scenario 10: Multiple Syncs (Verify Latest Shown)

**User Story**: P1 - View Catalog Freshness
**Acceptance Criteria**: Always show most recent successful sync

#### Steps

1. **Run multiple syncs** (wait 1 minute between each):
   ```bash
   python manage.py import_albums --sync
   # Wait 1 minute
   python manage.py import_albums --sync
   # Wait 1 minute
   python manage.py import_albums --sync
   ```

2. **Verify multiple SyncRecords created**:
   ```bash
   python manage.py shell
   >>> from catalog.models import SyncRecord
   >>> SyncRecord.objects.count()
   3  # or however many syncs run
   >>> list(SyncRecord.objects.values_list('sync_timestamp', flat=True))
   [datetime(...), datetime(...), datetime(...)]
   >>> exit()
   ```

3. **Visit catalog page**

4. **Verify display**:
   - ✅ Shows ONLY the most recent sync time (not oldest)
   - ✅ Albums added count from latest sync only

**Expected Result**: UI always reflects latest sync operation.

---

## Visual Verification Checklist

After implementing, verify UI layout and styling:

### Desktop View (1920x1080)

- [ ] Statistics panel prominent but not overwhelming
- [ ] Clear visual separation from filters
- [ ] Readable font size (14-16px)
- [ ] Proper alignment with album tile grid below
- [ ] No horizontal scrolling

### Tablet View (768x1024)

- [ ] Statistics panel still visible at top
- [ ] Text wraps appropriately if needed
- [ ] Does not interfere with filter dropdowns
- [ ] Album grid adjusts correctly

### Mobile View (375x667)

- [ ] Statistics panel stacks vertically if needed
- [ ] Text remains readable (not too small)
- [ ] No text truncation or overflow
- [ ] Touch targets for filters remain usable

## Performance Verification

### Page Load Time

1. **Clear browser cache**

2. **Open DevTools Network tab**

3. **Navigate to catalog page**

4. **Verify metrics**:
   - ✅ Page load < 2 seconds (SC-001 requirement)
   - ✅ Statistics query < 50ms (check Django Debug Toolbar if installed)
   - ✅ No N+1 query issues
   - ✅ Total queries < 10

### Large Catalog Performance

1. **With 10,000+ albums in catalog**:
   - ✅ Statistics query still < 50ms
   - ✅ Page load still < 2 seconds
   - ✅ No timeout errors

## Django Admin Verification

### Verify SyncRecord Admin Interface

1. **Navigate to Django admin**:
   ```
   http://localhost:8000/admin/
   ```

2. **Login** with superuser credentials

3. **Click "Sync Records"** in catalog section

4. **Verify list display**:
   - ✅ Shows sync_timestamp, albums_created, albums_updated, total_albums_in_catalog, success
   - ✅ Can filter by success and timestamp
   - ✅ Ordered by most recent first

5. **Try to add new record manually**:
   - ✅ "Add" button disabled or missing (records should only be created by command)

6. **Click on a sync record**:
   - ✅ Can view details
   - ✅ sync_timestamp is read-only

**Expected Result**: Admin provides visibility into sync history for debugging.

## Edge Cases & Error Handling

### Test Edge Cases

1. **Very recent sync (< 10 seconds ago)**:
   - ✅ Shows "X seconds ago" correctly

2. **Sync exactly at midnight**:
   - ✅ Time formatting still readable

3. **Database query timeout simulation** (advanced):
   - Temporarily break database connection
   - Verify graceful error (no 500 error to user)

4. **Missing humanize app**:
   - Remove `django.contrib.humanize` from INSTALLED_APPS
   - ✅ Should cause template error (caught during development)

## Rollback Testing

### Verify Rollback Safety

1. **Create backup of test database**

2. **Apply migration**:
   ```bash
   python manage.py migrate catalog 0003_syncrecord
   ```

3. **Verify feature works** (run scenarios above)

4. **Rollback migration**:
   ```bash
   python manage.py migrate catalog 0002_seed_genres_vocal_styles
   ```

5. **Verify**:
   - ✅ Catalog page still loads (gracefully handles missing SyncRecord table)
   - ✅ Album display unchanged
   - ✅ No 500 errors

6. **Re-apply migration**:
   ```bash
   python manage.py migrate catalog 0003_syncrecord
   ```

**Expected Result**: Migration is safely reversible.

##Acceptance Criteria Summary

All acceptance criteria from spec.md must pass:

### User Story 1 (P1)
- [x] **AC1**: Recent sync shows "X hours ago"
- [x] **AC2**: Old sync shows absolute date/time
- [x] **AC3**: Never synchronized shows appropriate message

### User Story 2 (P2)
- [x] **AC1**: Total album count displays with formatting
- [x] **AC2**: Empty catalog shows "0 albums"
- [x] **AC3**: Count updates after sync

### User Story 3 (P3)
- [x] **AC1**: New albums count displays ("+15 new")
- [x] **AC2**: Zero new albums handled gracefully
- [x] **AC3**: Only shows new additions (not removals)

### Success Criteria (SC)
- [x] **SC-001**: Page load < 2 seconds
- [x] **SC-002**: Statistics update within 5 seconds after sync
- [x] **SC-003**: 95% of users understand without help (manual observation)
- [x] **SC-004**: Time displays are human-readable
- [x] **SC-005**: Numbers formatted correctly for 10,000+ albums

## Manual Test Checklist

Copy this checklist for each test run:

```
Date: __________
Tester: __________
Environment: [ ] Local SQLite  [ ] Docker PostgreSQL

[ ] Scenario 1: Never synchronized
[ ] Scenario 2: After first sync
[ ] Scenario 3: Relative time (< 24h)
[ ] Scenario 4: Absolute time (> 24h)
[ ] Scenario 5: Large catalog (thousands separator)
[ ] Scenario 6: Subsequent sync with new albums
[ ] Scenario 7: Sync with zero new albums
[ ] Scenario 8: HTMX filter interaction
[ ] Scenario 9: Empty catalog
[ ] Scenario 10: Multiple syncs (latest shown)

Visual Verification:
[ ] Desktop layout
[ ] Tablet layout
[ ] Mobile layout

Performance:
[ ] Page load < 2 seconds
[ ] Statistics query < 50ms

Admin Interface:
[ ] SyncRecord list display
[ ] Cannot manually add records
[ ] Read-only timestamp

Notes/Issues Found:
_________________________________
_________________________________
```

## Troubleshooting

### Common Issues

**Issue**: "Not yet synchronized" always displays even after sync

**Solution**:
- Check SyncRecord was created: `python manage.py shell` → `SyncRecord.objects.count()`
- Check view passes `latest_sync` to template context
- Check template uses correct variable name

---

**Issue**: Numbers not formatted with thousands separator

**Solution**:
- Verify `django.contrib.humanize` in INSTALLED_APPS
- Check template loads humanize: `{% load humanize %}`
- Verify template uses `{{ count|intcomma }}`

---

**Issue**: Relative time not showing ("2 hours ago")

**Solution**:
- Verify `django.contrib.humanize` enabled
- Check template uses `{{ sync.sync_timestamp|naturaltime }}`
- Verify sync_timestamp is timezone-aware datetime

---

**Issue**: Statistics not visible on page

**Solution**:
- Check template includes statistics panel before filters
- Verify view passes `latest_sync` and `total_albums` to context
- Check for template syntax errors in logs

## Next Steps

After all scenarios pass:

1. ✅ Mark feature as ready for production
2. ✅ Deploy to staging environment
3. ✅ Run full test suite on staging
4. ✅ Get user acceptance sign-off
5. ✅ Deploy to production
6. ✅ Monitor first few syncs in production
7. ✅ Document any production-specific quirks

## Documentation Links

- [Feature Spec](./spec.md) - Requirements and user stories
- [Implementation Plan](./plan.md) - Technical approach
- [Data Model](./data-model.md) - SyncRecord model details
- [Tasks](./tasks.md) - Implementation task breakdown (generated separately)
