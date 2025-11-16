# Data Model: Admin Sync Page

**Feature**: 007-admin-sync-page
**Date**: 2025-11-16

## Overview

This feature is a UI refactoring that does **not require any data model changes**. All necessary data structures already exist in the codebase and remain unchanged.

## Existing Models (Unchanged)

The admin sync page will use existing models for displaying sync information:

### SyncRecord

**Purpose**: Tracks historical synchronization operations and their completion status.

**Usage in this feature**: Read-only access to display "Last synced" timestamp on admin page.

**Key Fields Used**:
- `sync_timestamp` (DateTime): When the sync operation completed
- `status` (String): Sync status - we filter for "completed" to find last successful sync

**Query Pattern**:
```python
latest_sync = SyncRecord.objects.filter(status="completed").order_by("-sync_timestamp").first()
```

**Location**: `catalog/models.py` (already defined)

---

### SyncOperation

**Purpose**: Tracks currently running or recently completed sync operations with detailed progress information.

**Usage in this feature**: Read by existing `sync_status` view to display real-time progress. Admin page includes `sync_status.html` component which polls this model.

**Key Fields Used** (via existing views):
- `status` (String): Current operation status (running, completed, failed, etc.)
- `current_tab` (String): Which Google Sheets tab is being processed
- `progress_message` (String): Detailed progress information
- `albums_fetched`, `albums_created`, `albums_updated` (Integer): Operation metrics

**Location**: `catalog/models.py` (already defined)

---

## Model Interaction Diagram

```
┌─────────────────────────────────────────┐
│   Admin Sync Page View                  │
│   (admin_sync_page)                     │
└─────────────────┬───────────────────────┘
                  │
                  │ Queries for context
                  ▼
         ┌────────────────┐
         │   SyncRecord   │
         │   (Read-Only)  │
         └────────────────┘
                  ▲
                  │ Last completed sync timestamp
                  │

┌─────────────────────────────────────────┐
│   Sync Status Component                 │
│   (sync_status.html via HTMX)          │
└─────────────────┬───────────────────────┘
                  │
                  │ Polled every 2s
                  ▼
         ┌────────────────┐
         │ SyncOperation  │
         │   (Read-Only)  │
         └────────────────┘
                  ▲
                  │ Real-time progress info
                  │

┌─────────────────────────────────────────┐
│   Sync Trigger View                     │
│   (sync_trigger - existing)             │
└─────────────────┬───────────────────────┘
                  │
                  │ Creates/updates
                  ▼
         ┌────────────────┐
         │ SyncOperation  │
         │   (Write)      │
         └────────────────┘
```

## Data Access Patterns

### Pattern 1: Display Last Sync Timestamp (Read-Only)

**View**: `admin_sync_page` (new view)
**Model**: `SyncRecord`
**Operation**: SELECT with filter and order

```python
latest_sync = SyncRecord.objects.filter(
    status="completed"
).order_by("-sync_timestamp").first()
```

**Template Usage**:
```django
{% if latest_sync %}
  Last synced: {{ latest_sync.sync_timestamp|date:"Y-m-d H:i:s" }}
{% else %}
  Never synced
{% endif %}
```

---

### Pattern 2: Trigger Sync (Existing, Unchanged)

**View**: `sync_trigger` (existing view, not modified)
**Model**: `SyncOperation`
**Operation**: CREATE new operation record, launches background sync

This pattern is unchanged - admin page simply links to existing `sync_trigger` endpoint via sync_button component.

---

### Pattern 3: Poll Sync Status (Existing, Unchanged)

**View**: `sync_status` (existing view, not modified)
**Model**: `SyncOperation`
**Operation**: SELECT current operation, return progress info

This pattern is unchanged - admin page includes existing `sync_status.html` component which polls existing endpoint.

---

## Database Schema Impact

**Changes Required**: NONE

**Rationale**: This feature only reorganizes UI templates and adds a new view. All data access patterns already exist and are simply reused on a different page.

---

## Migration Plan

**Migrations Required**: NONE

**Database Deployment**: Not applicable - no schema changes

**Data Migration**: Not applicable - no data structure changes

---

## Validation Rules

No new validation rules - feature uses existing model validation defined in `catalog/models.py`.

---

## State Transitions

No new state transitions - feature uses existing sync operation state machine:

```
[Idle] → [Running] → [Completed/Failed]
           ↓
       [Progress Updates]
```

This state machine is managed by existing `SyncManager` service and unchanged by this feature.

---

## Summary

This feature requires **zero data model changes**. It's a pure UI refactoring that:
- Reads existing `SyncRecord` model for timestamp display
- Reuses existing `SyncOperation` polling via unchanged HTMX components
- Maintains all existing data access patterns and business logic

The admin page is simply a new window into existing data structures.
