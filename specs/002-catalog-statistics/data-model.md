# Data Model: Catalog Statistics

**Feature**: Catalog Statistics Display
**Date**: 2025-11-03
**Status**: Final

## Overview

This document defines the data model for tracking catalog synchronization operations. The model enables displaying synchronization statistics to users (last sync time, total albums, recent additions).

## Entity Relationship Diagram

```
┌─────────────────────────┐
│      SyncRecord         │
│─────────────────────────│
│ id (PK)                 │
│ sync_timestamp          │◀─── Indexed for fast "latest sync" queries
│ albums_created          │
│ albums_updated          │
│ albums_skipped          │
│ total_albums_in_catalog │◀─── Snapshot at sync time
│ success                 │
│ error_message           │
└─────────────────────────┘
         │
         │ (Conceptual relationship -
         │  no foreign key)
         ▼
┌─────────────────────────┐
│        Album            │◀─── Existing model (no changes)
│─────────────────────────│
│ id (PK)                 │
│ spotify_album_id        │
│ name                    │
│ artist_id (FK)          │
│ genre_id (FK)           │
│ vocal_style_id (FK)     │
│ release_date            │
│ cover_art_url           │
│ spotify_url             │
│ imported_at             │
│ updated_at              │
└─────────────────────────┘
```

**Note**: No direct foreign key from SyncRecord to Album. SyncRecord stores aggregate counts, not individual album references.

## Models

### SyncRecord (New)

**Purpose**: Records metadata about each catalog synchronization operation for display to users.

**Table Name**: `catalog_syncrecord`

#### Fields

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | BigAutoField | Primary Key, Auto-increment | Django default primary key |
| `sync_timestamp` | DateTimeField | NOT NULL, Indexed, auto_now_add=True | When sync completed |
| `albums_created` | IntegerField | NOT NULL, default=0 | New albums added in this sync |
| `albums_updated` | IntegerField | NOT NULL, default=0 | Existing albums updated in this sync |
| `albums_skipped` | IntegerField | NOT NULL, default=0 | Albums already current (no changes) |
| `total_albums_in_catalog` | IntegerField | NOT NULL | Total album count after sync (snapshot) |
| `success` | BooleanField | NOT NULL, default=True | Whether sync completed successfully |
| `error_message` | TextField | NULL, blank=True | Error details if sync failed |

#### Indexes

```python
indexes = [
    models.Index(fields=["-sync_timestamp"], name="idx_sync_timestamp_desc")
]
```

**Rationale**: Descending index optimizes "get latest sync" query used on every page load.

#### Meta Options

```python
class Meta:
    ordering = ["-sync_timestamp"]  # Most recent first
    verbose_name = "Sync Record"
    verbose_name_plural = "Sync Records"
    db_table = "catalog_syncrecord"  # Django default
```

#### Methods

```python
def __str__(self) -> str:
    """String representation for admin interface."""
    status = "Success" if self.success else "Failed"
    return f"Sync at {self.sync_timestamp.strftime('%Y-%m-%d %H:%M')} - {status}"

def albums_added_display(self) -> str:
    """Format albums_created for display (e.g., '+15' or '+0')."""
    return f"+{self.albums_created}"

@property
def total_changes(self) -> int:
    """Total albums affected (created + updated)."""
    return self.albums_created + self.albums_updated
```

#### Django Model Code

```python
from django.db import models
from typing import Optional


class SyncRecord(models.Model):
    """
    Records catalog synchronization operations.

    Tracks metadata about each sync run to enable display of synchronization
    statistics to users (last sync time, albums added, total count).
    """

    sync_timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this synchronization completed"
    )
    albums_created = models.IntegerField(
        default=0,
        help_text="Number of new albums added during this sync"
    )
    albums_updated = models.IntegerField(
        default=0,
        help_text="Number of existing albums updated during this sync"
    )
    albums_skipped = models.IntegerField(
        default=0,
        help_text="Number of albums skipped (already current)"
    )
    total_albums_in_catalog = models.IntegerField(
        help_text="Total album count in catalog after this sync"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether sync completed successfully"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error details if sync failed"
    )

    class Meta:
        ordering = ["-sync_timestamp"]
        verbose_name = "Sync Record"
        verbose_name_plural = "Sync Records"
        indexes = [
            models.Index(fields=["-sync_timestamp"], name="idx_sync_timestamp_desc")
        ]

    def __str__(self) -> str:
        """String representation for admin interface."""
        status = "Success" if self.success else "Failed"
        timestamp_str = self.sync_timestamp.strftime("%Y-%m-%d %H:%M")
        return f"Sync at {timestamp_str} - {status}"

    def albums_added_display(self) -> str:
        """Format albums_created for display (e.g., '+15 new' or '+0 new')."""
        return f"+{self.albums_created} new" if self.albums_created > 0 else "+0 new"

    @property
    def total_changes(self) -> int:
        """Total albums affected by this sync (created + updated)."""
        return self.albums_created + self.albums_updated
```

### Album (Existing - No Changes)

**Purpose**: Represents a music album in the catalog.

**No modifications needed** for this feature. SyncRecord stores aggregate data about albums, not individual album references.

**Existing fields used**:
- Count of Album instances used for `total_albums` display
- Individual Album records unchanged by SyncRecord

## Relationships

### SyncRecord ↔ Album

**Type**: Conceptual (no database foreign key)

**Rationale**:
- SyncRecord stores aggregate counts, not references to individual albums
- No need to query "which albums were added in sync #123" (out of scope)
- Keeps model simple and query-efficient

**Query Pattern**:
```python
# Get latest sync metadata
latest_sync = SyncRecord.objects.filter(success=True).first()

# Get current total album count
total_albums = Album.objects.count()

# These queries are independent and efficient
```

## Data Constraints

### Business Rules

1. **Sync Timestamp**:
   - Automatically set on record creation (auto_now_add)
   - Never manually modified
   - Used for "last sync" display and ordering

2. **Counts Must Be Non-Negative**:
   - `albums_created >= 0`
   - `albums_updated >= 0`
   - `albums_skipped >= 0`
   - `total_albums_in_catalog >= 0`
   - Enforced at application level (validated in management command)

3. **Success/Error Correlation**:
   - If `success = False`, `error_message` should be set
   - If `success = True`, `error_message` should be empty
   - Not enforced at database level (application responsibility)

4. **Total Albums Integrity**:
   - `total_albums_in_catalog` should match `Album.objects.count()` at sync time
   - Calculated snapshot, not a foreign key sum
   - May drift if albums manually deleted outside sync process (acceptable)

### Database Constraints

```sql
-- Primary key constraint (auto-generated by Django)
ALTER TABLE catalog_syncrecord ADD PRIMARY KEY (id);

-- Index for fast "latest sync" queries
CREATE INDEX idx_sync_timestamp_desc ON catalog_syncrecord (sync_timestamp DESC);

-- Non-null constraints
ALTER TABLE catalog_syncrecord ALTER COLUMN sync_timestamp SET NOT NULL;
ALTER TABLE catalog_syncrecord ALTER COLUMN albums_created SET NOT NULL;
ALTER TABLE catalog_syncrecord ALTER COLUMN albums_updated SET NOT NULL;
ALTER TABLE catalog_syncrecord ALTER COLUMN albums_skipped SET NOT NULL;
ALTER TABLE catalog_syncrecord ALTER COLUMN total_albums_in_catalog SET NOT NULL;
ALTER TABLE catalog_syncrecord ALTER COLUMN success SET NOT NULL;
```

## Query Patterns

### Get Latest Successful Sync

**Use Case**: Display sync statistics on catalog page

```python
latest_sync: Optional[SyncRecord] = (
    SyncRecord.objects
    .filter(success=True)
    .first()  # Relies on ordering = ["-sync_timestamp"]
)

if latest_sync:
    last_sync_time = latest_sync.sync_timestamp
    albums_added = latest_sync.albums_created
else:
    # Handle "never synchronized" case
    last_sync_time = None
    albums_added = 0
```

**Performance**: O(1) with index, < 5ms

### Get Current Album Count

**Use Case**: Display total albums in catalog

```python
total_albums: int = Album.objects.count()
```

**Performance**: O(1) in PostgreSQL (uses table statistics), < 5ms

### Get Sync History (Future Enhancement)

**Use Case**: Admin dashboard showing recent sync operations

```python
recent_syncs: list[SyncRecord] = (
    SyncRecord.objects
    .all()[:10]  # Last 10 syncs
)
```

**Note**: Currently out of scope, but model supports this query

### Create Sync Record

**Use Case**: After successful import_albums command

```python
from catalog.models import Album, SyncRecord

# After import completes
created, updated, skipped = import_results
total = Album.objects.count()

sync_record = SyncRecord.objects.create(
    albums_created=created,
    albums_updated=updated,
    albums_skipped=skipped,
    total_albums_in_catalog=total,
    success=True
)
```

**Performance**: Single INSERT, < 10ms

## Migration Strategy

### Migration File

**File**: `catalog/migrations/0003_syncrecord.py`

Auto-generated by:
```bash
python manage.py makemigrations catalog
```

**Expected Operations**:
1. Create `catalog_syncrecord` table
2. Create primary key index
3. Create `idx_sync_timestamp_desc` index

**No data migration needed** - table starts empty, first sync populates it.

### Migration Content (Preview)

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_seed_genres_vocal_styles'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_timestamp', models.DateTimeField(auto_now_add=True, db_index=True, help_text='When this synchronization completed')),
                ('albums_created', models.IntegerField(default=0, help_text='Number of new albums added during this sync')),
                ('albums_updated', models.IntegerField(default=0, help_text='Number of existing albums updated during this sync')),
                ('albums_skipped', models.IntegerField(default=0, help_text='Number of albums skipped (already current)')),
                ('total_albums_in_catalog', models.IntegerField(help_text='Total album count in catalog after this sync')),
                ('success', models.BooleanField(default=True, help_text='Whether sync completed successfully')),
                ('error_message', models.TextField(blank=True, help_text='Error details if sync failed', null=True)),
            ],
            options={
                'verbose_name': 'Sync Record',
                'verbose_name_plural': 'Sync Records',
                'ordering': ['-sync_timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='syncrecord',
            index=models.Index(fields=['-sync_timestamp'], name='idx_sync_timestamp_desc'),
        ),
    ]
```

### Rollback Safety

**Forward Migration**:
- Creates new table only
- No changes to existing tables
- Zero downtime

**Reverse Migration**:
```bash
python manage.py migrate catalog 0002_seed_genres_vocal_styles
```
- Drops `catalog_syncrecord` table
- Sync history lost (acceptable - can be regenerated)
- Zero impact on Album data

## Type Annotations

All model code includes full type annotations for pyright strict mode compliance:

```python
from typing import Optional
from django.db import models

class SyncRecord(models.Model):
    # Fields with explicit types via help_text and Django field types

    def __str__(self) -> str:
        """Explicit return type annotation."""
        ...

    def albums_added_display(self) -> str:
        """Explicit return type annotation."""
        ...

    @property
    def total_changes(self) -> int:
        """Explicit return type annotation."""
        ...
```

Django's QuerySet operations are properly typed:
```python
latest_sync: Optional[SyncRecord] = SyncRecord.objects.filter(...).first()
recent_syncs: list[SyncRecord] = list(SyncRecord.objects.all()[:10])
sync_count: int = SyncRecord.objects.count()
```

## Testing Considerations

### Model Tests (Optional)

If tests are added (not required by spec):

```python
from django.test import TestCase
from catalog.models import SyncRecord, Album


class SyncRecordModelTest(TestCase):
    def test_create_sync_record(self):
        """Test creating a SyncRecord with valid data."""
        sync = SyncRecord.objects.create(
            albums_created=10,
            albums_updated=5,
            albums_skipped=2,
            total_albums_in_catalog=100,
            success=True
        )
        self.assertEqual(sync.albums_created, 10)
        self.assertTrue(sync.success)

    def test_ordering(self):
        """Test SyncRecords are ordered by timestamp descending."""
        sync1 = SyncRecord.objects.create(total_albums_in_catalog=100)
        sync2 = SyncRecord.objects.create(total_albums_in_catalog=110)

        latest = SyncRecord.objects.first()
        self.assertEqual(latest.id, sync2.id)  # Most recent first

    def test_str_representation(self):
        """Test __str__ method returns readable format."""
        sync = SyncRecord.objects.create(
            total_albums_in_catalog=100,
            success=True
        )
        str_repr = str(sync)
        self.assertIn("Sync at", str_repr)
        self.assertIn("Success", str_repr)
```

## Admin Interface

Register SyncRecord in Django admin for visibility:

**File**: `catalog/admin.py`

```python
from django.contrib import admin
from catalog.models import SyncRecord


@admin.register(SyncRecord)
class SyncRecordAdmin(admin.ModelAdmin):
    """Admin interface for viewing sync history."""

    list_display = [
        'sync_timestamp',
        'albums_created',
        'albums_updated',
        'total_albums_in_catalog',
        'success'
    ]
    list_filter = ['success', 'sync_timestamp']
    readonly_fields = ['sync_timestamp']  # Prevent manual timestamp editing
    ordering = ['-sync_timestamp']

    def has_add_permission(self, request):
        """Disable manual creation - SyncRecords created by management command only."""
        return False
```

## Summary

**New Model**: SyncRecord
- 8 fields (1 auto-generated PK, 7 data fields)
- 1 index for query optimization
- Type-annotated for pyright compliance
- No foreign keys (stores aggregate data)

**Integration**:
- Created by `import_albums` management command after each sync
- Queried by `AlbumListView` for statistics display
- Visible in Django admin for monitoring

**Performance**:
- Latest sync query: < 5ms (indexed)
- Album count query: < 5ms (PostgreSQL table stats)
- Total page load impact: < 10ms

**Migration**:
- Single migration file (0003_syncrecord.py)
- Zero downtime deployment
- Reversible without data loss

Ready for Phase 1: quickstart.md generation.
