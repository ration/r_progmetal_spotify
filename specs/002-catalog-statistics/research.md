# Research: Catalog Statistics

**Feature**: Display synchronization statistics on catalog page
**Date**: 2025-11-03
**Status**: Complete

## Overview

This document captures research findings for implementing catalog statistics display. The feature requires adding persistent sync tracking to the existing import system and displaying statistics in the catalog UI.

## Existing Implementation Analysis

### Current Synchronization Architecture

**Management Command**: `catalog/management/commands/import_albums.py`

The current implementation:
- Single command with `--sync` and `--limit` options
- Orchestrates three services: GoogleSheetsService, SpotifyClient, AlbumImporter
- Returns tuple: `(albums_created, albums_updated, albums_skipped)`
- **Gap**: Counts are printed to stdout but not persisted

**Service Layer**:
- `catalog/services/album_importer.py` - Core import/sync logic
- `catalog/services/spotify_client.py` - Spotify API integration
- `catalog/services/google_sheets.py` - XLSX fetching from Google Sheets

**Data Model**:
- 4 existing models: Artist, Genre, VocalStyle, Album
- Album has `imported_at` and `updated_at` timestamps (per-album, not per-sync)
- **Gap**: No SyncRecord or sync history model

### Current Catalog UI

**Views**: `catalog/views.py`
- `AlbumListView` - Main catalog page with filtering
  - HTMX-aware: Returns partial template for filter changes
  - Query optimization: `select_related('artist', 'genre', 'vocal_style')`
  - Ordering: `release_date DESC, imported_at DESC`

**Templates**: `catalog/templates/catalog/`
- `album_list.html` - Full page with filters and tile grid
- `album_list_tiles.html` - HTMX partial (tiles only, no page chrome)
- `components/album_tile.html` - Individual tile
- `components/filters.html` - Genre/vocal style dropdowns

**HTMX Pattern**:
- Filter change triggers `GET /catalog/albums/?genre=<slug>`
- Server detects `HX-Request` header
- Returns `album_list_tiles.html` fragment
- HTMX swaps into `#album-tiles` container
- Browser URL updated via `HX-Push-Url`

## Design Decisions

### Decision 1: SyncRecord Model Location

**Chosen**: Add SyncRecord to `catalog/models.py` alongside existing models

**Rationale**:
- Sync operations are tightly coupled to Album model
- No need for separate app - single Django app keeps complexity low
- Follows existing pattern (all catalog-related models in one file)
- Easy to query relationships (SyncRecord → Album count)

**Alternatives Considered**:
- Separate `sync` app: Rejected - adds unnecessary complexity for single model
- Store in Album model: Rejected - sync is catalog-level event, not per-album

### Decision 2: Sync Metadata to Track

**Chosen**: Track these fields in SyncRecord:
- `sync_timestamp` (DateTimeField, auto_now_add)
- `albums_created` (IntegerField)
- `albums_updated` (IntegerField)
- `albums_skipped` (IntegerField)
- `total_albums_in_catalog` (IntegerField) - snapshot at sync time
- `success` (BooleanField)
- `error_message` (TextField, optional)

**Rationale**:
- Meets all spec requirements (FR-001, FR-002, FR-003)
- `total_albums_in_catalog` enables historical tracking
- `success` and `error_message` support future error handling (out of scope but cheap to add)
- Matches data already returned by `album_importer.import_albums()`

**Alternatives Considered**:
- Track only `albums_created`: Rejected - spec requires last sync time and total count
- Track albums_deleted: Rejected - out of scope, adds complexity

### Decision 3: Time Display Format

**Chosen**: Template filter `relative_time` that returns:
- "X minutes/hours ago" for syncs within 24 hours
- Absolute date/time for older syncs

**Rationale**:
- Meets FR-005 and FR-006 requirements
- Human-readable without mental math
- Django's `naturaltime` filter (from `humanize`) provides this functionality
- Falls back gracefully for "never synchronized" case

**Alternatives Considered**:
- Always show absolute time: Rejected - less user-friendly for recent syncs
- Client-side JavaScript formatting: Rejected - adds complexity, HTMX preference is server-side

### Decision 4: Number Formatting

**Chosen**: Template filter `format_number` using Python's built-in locale/formatting

**Rationale**:
- Meets FR-004 requirement (thousands separators)
- Django's `intcomma` filter (from `humanize`) provides this: `{{ value|intcomma }}`
- No external dependencies needed
- Works for catalogs of any size (10,000+ albums)

**Alternatives Considered**:
- JavaScript client-side formatting: Rejected - server-side keeps HTMX pattern consistent
- Custom template tag: Rejected - Django's built-in `intcomma` sufficient

### Decision 5: Statistics Display Location

**Chosen**: Statistics panel above filter controls in `album_list.html`

**Rationale**:
- Prominent but non-intrusive
- Visible immediately on page load (FR-001 requires < 2 second visibility)
- Works with both full page loads and HTMX partial updates
- Component-based: Create `components/stats_panel.html` for reusability

**Layout**:
```
┌─────────────────────────────────────────┐
│  Catalog Statistics                     │
│  Last sync: 2 hours ago                 │
│  Total: 1,247 albums | +15 new          │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Filters: [Genre ▼] [Vocal Style ▼]    │
└─────────────────────────────────────────┘
[Album tiles grid...]
```

**Alternatives Considered**:
- Sidebar: Rejected - reduces space for album tiles
- Footer: Rejected - not immediately visible (fails SC-001)
- Modal/popup: Rejected - requires user action

### Decision 6: HTMX Integration Strategy

**Chosen**: Statistics included in full page template only, not HTMX partials

**Rationale**:
- HTMX partial (`album_list_tiles.html`) only updates tile grid, not page chrome
- Statistics don't change during filtering - no need to re-render
- Keeps partial template minimal and focused on tiles
- Reduces unnecessary DOM updates

**Alternatives Considered**:
- Include in HTMX partial: Rejected - statistics unchanged by filters, wasteful
- Separate HTMX endpoint for stats: Rejected - adds complexity, no benefit

### Decision 7: Query Optimization Strategy

**Chosen**: Single query to get latest SyncRecord in view context

```python
latest_sync = SyncRecord.objects.filter(success=True).first()  # Already ordered by -sync_timestamp
total_albums = Album.objects.count()
```

**Rationale**:
- Meets SC-001 performance goal (< 2 seconds page load)
- Two simple queries: O(1) for latest sync (indexed), O(1) for count
- No joins needed
- SyncRecord table will be small (one row per sync, maybe daily)

**Alternatives Considered**:
- Aggregate query combining sync and count: Rejected - premature optimization
- Cache in Redis: Rejected - adds complexity, not needed for small table

## Integration Points

### 1. Model Layer

**File**: `catalog/models.py`

Add SyncRecord model after existing models:

```python
class SyncRecord(models.Model):
    """Records catalog synchronization operations."""
    sync_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    albums_created = models.IntegerField(default=0)
    albums_updated = models.IntegerField(default=0)
    albums_skipped = models.IntegerField(default=0)
    total_albums_in_catalog = models.IntegerField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-sync_timestamp"]
        indexes = [models.Index(fields=["-sync_timestamp"])]
```

**Migration**: Auto-generated `0003_syncrecord.py`

### 2. Service Layer

**File**: `catalog/services/album_importer.py`

Modify `import_albums()` method to:
1. Keep existing return tuple `(created, updated, skipped)`
2. Add optional return of sync metadata dict

**No breaking changes** - backward compatible enhancement

### 3. Management Command

**File**: `catalog/management/commands/import_albums.py`

After successful sync:
```python
from catalog.models import SyncRecord, Album

created, updated, skipped = importer.import_albums(limit=limit, sync_mode=sync)
total = Album.objects.count()

SyncRecord.objects.create(
    albums_created=created,
    albums_updated=updated,
    albums_skipped=skipped,
    total_albums_in_catalog=total,
    success=True
)
```

### 4. View Layer

**File**: `catalog/views.py`

Modify `AlbumListView.get_context_data()`:
```python
from catalog.models import SyncRecord, Album

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['latest_sync'] = SyncRecord.objects.filter(success=True).first()
    context['total_albums'] = Album.objects.count()
    return context
```

### 5. Template Layer

**New File**: `catalog/templatetags/catalog_extras.py`

Custom filters:
- `relative_time` - Humanize timestamps
- `format_number` - Add thousands separators

**Or** use Django's built-in `humanize` app:
- Load `{% load humanize %}` in template
- Use `{{ sync.sync_timestamp|naturaltime }}`
- Use `{{ count|intcomma }}`

**Recommendation**: Use Django's `humanize` - no custom code needed

**Modified File**: `catalog/templates/catalog/album_list.html`

Add before filters:
```django
{% load humanize %}

{% if latest_sync %}
<div class="stats-panel">
  <p>Last synchronized: {{ latest_sync.sync_timestamp|naturaltime }}</p>
  <p>Total: {{ total_albums|intcomma }} albums
     {% if latest_sync.albums_created > 0 %}
     | +{{ latest_sync.albums_created }} new
     {% endif %}
  </p>
</div>
{% else %}
<div class="stats-panel">
  <p>Not yet synchronized</p>
  <p>Total: {{ total_albums|intcomma }} albums</p>
</div>
{% endif %}
```

### 6. Admin Interface

**File**: `catalog/admin.py`

Register SyncRecord for admin visibility:
```python
from catalog.models import SyncRecord

@admin.register(SyncRecord)
class SyncRecordAdmin(admin.ModelAdmin):
    list_display = ['sync_timestamp', 'albums_created', 'albums_updated', 'success']
    list_filter = ['success', 'sync_timestamp']
    readonly_fields = ['sync_timestamp']
```

## Performance Considerations

### Query Performance

**Current Load**:
- Catalog page already queries Album with `select_related` (optimized)
- Adding 2 simple queries:
  1. `SyncRecord.objects.filter(success=True).first()` - O(1) with index
  2. `Album.objects.count()` - O(1) in PostgreSQL (uses table stats)

**Expected Impact**: < 10ms additional query time

**Scaling**:
- SyncRecord table growth: ~365 rows/year if daily syncs
- Even with 10 years of data (3,650 rows), indexed query remains fast
- Consider cleanup job if table grows beyond 10,000 rows (years of data)

### Template Rendering

**Humanize Filters**:
- `naturaltime`: Simple datetime math, negligible cost
- `intcomma`: String formatting, negligible cost

**Expected Impact**: < 1ms rendering time

**Total Performance Budget**: Well within SC-001 requirement (< 2 seconds page load)

## Testing Strategy

### Manual Testing (Recommended for this feature)

Spec does not require automated tests - manual testing sufficient:

1. **Before first sync**: Verify "Not yet synchronized" displays
2. **After sync**: Verify stats show correct counts and timestamp
3. **Multiple syncs**: Verify stats update to show latest sync
4. **Large numbers**: Test with 10,000+ albums (thousands separators)
5. **Time formatting**:
   - Sync < 24 hours ago shows relative time
   - Sync > 24 hours ago shows absolute date
6. **HTMX filtering**: Verify stats remain visible and unchanged during filter operations
7. **Edge cases**:
   - Empty catalog (0 albums)
   - Sync with 0 new albums
   - Very recent sync (< 1 minute ago)

### Optional Automated Tests

If tests are added later (not required by spec):

**Model Tests** (`tests/test_sync_record.py`):
- SyncRecord creation
- Ordering (most recent first)
- Default values

**View Tests** (`tests/test_views.py`):
- Context includes `latest_sync`
- Context includes `total_albums`
- Handles no sync records case

**Template Tests**:
- Stats panel renders with sync data
- Stats panel renders "Not yet synchronized"
- Humanize filters work correctly

## Dependencies

### New Dependencies

**None** - All functionality provided by:
- Django 5.2.8 (already installed)
- Django's `humanize` app (built-in, just needs activation in settings)

### Settings Changes

**File**: `config/settings.py`

Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    'django.contrib.humanize',  # NEW: For naturaltime and intcomma filters
]
```

## Migration Path

### Development Migration Steps

1. Create SyncRecord model in `catalog/models.py`
2. Run `python manage.py makemigrations catalog`
3. Run `python manage.py migrate`
4. Modify `album_importer.py` to return metadata
5. Modify `import_albums.py` command to create SyncRecord
6. Update view and template
7. Add `django.contrib.humanize` to INSTALLED_APPS
8. Test manually

### Production Migration Steps

1. Deploy code with migration
2. Run migration: `python manage.py migrate`
3. Run sync to create first SyncRecord: `python manage.py import_albums --sync`
4. Verify statistics display on catalog page

**Rollback Plan**:
- Migration is additive (new table only)
- Can be rolled back without data loss
- Old code continues to work (doesn't depend on SyncRecord)

## Open Questions

None - all requirements from spec are clear and researchable.

## Conclusion

Implementation is straightforward:
- Single new model (SyncRecord)
- Minor enhancements to existing command and view
- Template updates to display statistics
- No new dependencies (use Django's built-in humanize)
- Low risk, high value feature

All technical decisions align with:
- Constitution principles (type safety, incremental delivery)
- Existing Django patterns
- Performance requirements (< 2 second page load)
- HTMX integration strategy

Ready for Phase 1 (data model and contracts design).
