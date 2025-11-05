# Data Model: Synchronization Button with Status Display

**Feature**: 004-sync-button
**Date**: 2025-11-04
**Purpose**: Define data structures for sync operation tracking and status display

## Overview

This feature introduces one new model (`SyncOperation`) and leverages one existing model (`SyncRecord`). The `SyncOperation` model tracks real-time sync progress during execution, while `SyncRecord` stores the final results after completion. This separation allows active operations to be queried for status without mixing them with historical records.

## Entity Relationship Diagram

```
┌─────────────────────────────────┐
│       SyncOperation             │  (NEW - tracks active sync)
├─────────────────────────────────┤
│ id: AutoField (PK)              │
│ status: CharField               │◄─── Primary state machine
│ stage: CharField                │
│ stage_message: CharField        │
│ albums_processed: IntegerField  │
│ total_albums: IntegerField?     │
│ started_at: DateTimeField       │
│ completed_at: DateTimeField?    │
│ error_message: TextField        │
│ created_by_ip: GenericIPAddr?   │
└─────────────────────────────────┘
         │
         │ One-to-One (when complete)
         ▼
┌─────────────────────────────────┐
│       SyncRecord                │  (EXISTING - historical log)
├─────────────────────────────────┤
│ id: AutoField (PK)              │
│ sync_timestamp: DateTimeField   │
│ albums_created: IntegerField    │
│ albums_updated: IntegerField    │
│ albums_skipped: IntegerField    │
│ total_albums_in_catalog: Int    │
│ success: BooleanField           │
│ error_message: TextField?       │
└─────────────────────────────────┘
```

**Relationship**: When a `SyncOperation` completes successfully, a `SyncRecord` is created to log the final results. The `SyncOperation` may be deleted after completion (retention policy TBD), while `SyncRecord` persists indefinitely for historical analysis.

---

## Model Specifications

### SyncOperation (NEW)

**Purpose**: Track real-time status and progress of an active synchronization operation

**Lifecycle**:
1. Created with `status='pending'` when user clicks "Sync Now"
2. Status changes to `'running'` when background thread starts
3. `stage`, `stage_message`, and `albums_processed` updated during sync
4. Status changes to `'completed'` or `'failed'` when done
5. `SyncRecord` created for historical log (if successful)
6. `SyncOperation` may be deleted after retention period (e.g., 24 hours)

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `AutoField` | Primary Key | Unique identifier |
| `status` | `CharField(20)` | Choices: `pending`, `running`, `completed`, `failed` | Current operation state |
| `stage` | `CharField(50)` | Choices: `fetching`, `processing`, `finalizing` | Current sync stage |
| `stage_message` | `CharField(200)` | | Human-readable status text (e.g., "Syncing album 15 of 47...") |
| `albums_processed` | `IntegerField` | Default: 0 | Number of albums processed so far |
| `total_albums` | `IntegerField` | Nullable | Total albums to process (set after fetching from Google Sheets) |
| `started_at` | `DateTimeField` | Auto-add | When sync operation began |
| `completed_at` | `DateTimeField` | Nullable | When sync operation finished (success or failure) |
| `error_message` | `TextField` | Blank | Error details if status is `failed` |
| `created_by_ip` | `GenericIPAddressField` | Nullable, Optional | IP address that triggered sync (for audit logging) |

**Indexes**:
- Primary index on `id` (default)
- Index on `status` (frequent queries for active syncs)
- Index on `started_at` (cleanup of old records)

**Validation Rules**:
- `status` must be one of: `pending`, `running`, `completed`, `failed`
- `stage` must be one of: `fetching`, `processing`, `finalizing` (or blank if not started)
- `albums_processed` >= 0
- `total_albums` >= 0 if not null
- `albums_processed` <= `total_albums` if both set
- `completed_at` must be >= `started_at` if set
- `error_message` required if `status='failed'`

**State Transitions**:
```
pending ──► running ──► completed
                   └──► failed
```

**Methods**:

```python
def progress_percentage(self) -> int | None:
    """Calculate completion percentage (0-100) or None if total unknown."""
    if self.total_albums and self.total_albums > 0:
        return min(100, int((self.albums_processed / self.total_albums) * 100))
    return None

def duration(self) -> timedelta | None:
    """Calculate sync duration (completed_at - started_at) or current duration if running."""
    if self.completed_at:
        return self.completed_at - self.started_at
    elif self.status == 'running':
        return timezone.now() - self.started_at
    return None

def is_active(self) -> bool:
    """Return True if sync is pending or running."""
    return self.status in ('pending', 'running')

def display_status(self) -> str:
    """Return human-readable status for UI display."""
    if self.stage_message:
        return self.stage_message
    return f"Status: {self.status.title()}"
```

---

### SyncRecord (EXISTING - Reference)

**Purpose**: Historical log of completed synchronization operations

**Note**: This model already exists (see `catalog/models.py:249-312`). No changes required for Phase 1 (basic sync trigger). May be extended in later phases to link to `SyncOperation` if needed.

**Fields** (summary):
- `sync_timestamp`: When sync completed
- `albums_created`: Count of new albums added
- `albums_updated`: Count of albums updated
- `albums_skipped`: Count of albums skipped (already current)
- `total_albums_in_catalog`: Total album count after sync
- `success`: Whether sync succeeded
- `error_message`: Error details if failed

**Usage**: Created by `AlbumImporter` when sync completes. Displayed in UI as "Last synced: [timestamp]".

---

## Data Access Patterns

### 1. Check for Active Sync (Concurrency Control)

**Query**:
```python
from django.db import transaction
from django.db.models import Q

with transaction.atomic():
    active_sync = SyncOperation.objects.filter(
        Q(status='pending') | Q(status='running')
    ).select_for_update(nowait=True).first()

    if active_sync:
        return None  # Sync already in progress
    # Create new sync operation
```

**Purpose**: Prevent concurrent syncs (FR-002, SC-007)

**Frequency**: Every sync trigger (user clicks button)

---

### 2. Get Current Sync Status (Polling Endpoint)

**Query**:
```python
current_sync = SyncOperation.objects.filter(
    Q(status='pending') | Q(status='running')
).order_by('-started_at').first()
```

**Purpose**: Return status for HTMX polling (FR-004, FR-005)

**Frequency**: Every 2 seconds during active sync

**Response Data**:
- `status`, `stage`, `stage_message`
- `albums_processed`, `total_albums`
- `progress_percentage()` (calculated)
- `duration()` (calculated)

---

### 3. Get Last Successful Sync (Timestamp Display)

**Query**:
```python
last_sync = SyncRecord.objects.filter(success=True).order_by('-sync_timestamp').first()
```

**Purpose**: Display "Last synced: X ago" (FR-009, US-004)

**Frequency**: On page load

**Response Data**:
- `sync_timestamp` (passed to frontend for relative time calculation)

---

### 4. Update Sync Progress (Background Thread)

**Update**:
```python
sync_op = SyncOperation.objects.get(id=sync_id)
sync_op.stage = 'processing'
sync_op.stage_message = f"Syncing album {processed} of {total}..."
sync_op.albums_processed = processed
sync_op.total_albums = total
sync_op.save(update_fields=['stage', 'stage_message', 'albums_processed', 'total_albums'])
```

**Purpose**: Write progress from background thread (FR-004)

**Frequency**: Every N albums (e.g., every 5 albums to reduce DB writes)

**Optimization**: Use `update_fields` to minimize lock contention

---

### 5. Complete Sync Operation

**Update**:
```python
sync_op = SyncOperation.objects.get(id=sync_id)
sync_op.status = 'completed'
sync_op.stage = 'finalizing'
sync_op.stage_message = f"Sync complete! Updated {sync_op.albums_processed} albums"
sync_op.completed_at = timezone.now()
sync_op.save()

# Create SyncRecord for historical log
SyncRecord.objects.create(
    albums_created=created_count,
    albums_updated=updated_count,
    albums_skipped=skipped_count,
    total_albums_in_catalog=Album.objects.count(),
    success=True
)
```

**Purpose**: Mark sync complete and log results (FR-006)

**Frequency**: Once per sync operation (on completion)

---

## Migration Plan

### Migration 1: Add SyncOperation Model

**File**: `catalog/migrations/000X_add_syncoperation.py`

**Operations**:
1. Create `SyncOperation` table with all fields
2. Add indexes on `status` and `started_at`
3. No data migration needed (new feature)

**Generated by**: `python manage.py makemigrations`

**Rollback Strategy**: Drop `SyncOperation` table (no data loss concern since table will be empty)

---

## Future Enhancements (Out of Scope for Phase 1)

1. **Link SyncOperation to SyncRecord**: Add `ForeignKey(SyncRecord, null=True)` to preserve relationship
2. **User Attribution**: Add `ForeignKey(User)` if authentication is added
3. **Retention Policy**: Automatic cleanup of old `SyncOperation` records (e.g., delete after 7 days)
4. **Sync Scheduling**: `scheduled_at` field for future sync operations
5. **Partial Sync Tracking**: Track which specific albums failed during partial failures

---

## Validation Tests

**Test Coverage Required**:
1. Create `SyncOperation` with valid data → success
2. Create `SyncOperation` with invalid status → ValidationError
3. Query for active sync returns correct records
4. `progress_percentage()` calculates correctly (0%, 50%, 100%)
5. `progress_percentage()` returns None when total_albums is None
6. `duration()` calculates correctly for completed/running syncs
7. `is_active()` returns True for pending/running, False for completed/failed
8. `display_status()` returns stage_message if present, else formatted status
9. State transitions (pending → running → completed) persist correctly
10. Concurrent sync prevention works (two threads try to create sync simultaneously)

---

## Summary

**New Models**: 1 (`SyncOperation`)
**Modified Models**: 0 (no changes to existing models)
**New Fields**: 9 (in `SyncOperation`)
**Relationships**: 0 (may add link to `SyncRecord` in future)
**Indexes**: 2 (status, started_at)
**Migrations**: 1 (create table)

**Data Model Status**: ✅ Complete and ready for contract definition
