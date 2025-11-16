# Data Model: Multi-Tab Google Sheets Parsing

**Feature**: 005-multi-tab-parsing
**Created**: 2025-01-05
**References**: [spec.md](./spec.md), [research.md](./research.md)

## Overview

This document defines data structures for multi-tab Google Sheets parsing. The design minimizes schema changes by adding a single field to the existing `SyncOperation` model and using ephemeral (non-persisted) metadata objects for tab processing.

---

## Database Schema Changes

### SyncOperation Model Enhancement

**File**: `catalog/models.py`

**New Field**:

```python
class SyncOperation(models.Model):
    # ... existing fields ...

    current_tab = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Name of the currently processing Google Sheets tab"
    )
```

**Field Details**:
- **Type**: CharField(max_length=100)
- **Nullable**: Yes (blank=True) - empty when not actively processing
- **Default**: Empty string
- **Purpose**: Track which tab is currently being processed for progress display
- **Update Frequency**: Set on each tab transition, cleared on completion

**Migration**: `catalog/migrations/0005_syncoperation_current_tab.py`

```python
# Generated migration
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0004_syncoperation'),
    ]

    operations = [
        migrations.AddField(
            model_name='syncoperation',
            name='current_tab',
            field=models.CharField(blank=True, default='', help_text='Name of the currently processing Google Sheets tab', max_length=100),
        ),
    ]
```

---

## Ephemeral Data Structures

### TabMetadata

**Purpose**: Represent metadata for a single Google Sheets tab during processing
**Lifecycle**: Created during tab enumeration, used for filtering/sorting, discarded after import
**Persistence**: Not stored in database

**Definition**:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TabMetadata:
    """
    Metadata for a single Google Sheets tab.

    Ephemeral object used during multi-tab synchronization to filter,
    sort, and track progress across tabs.
    """
    name: str                    # Original tab name from Google Sheets
    normalized_name: str         # Whitespace-trimmed, validated version
    year: Optional[int]          # Extracted year (e.g., 2025 from "2025 Prog-metal")
    order: int                   # Original position in workbook (0-indexed)
    is_prog_metal: bool          # True if tab passes Prog-metal filter
    estimated_rows: Optional[int] = None  # Optional: row count from initial scan

    def __str__(self) -> str:
        year_str = f" ({self.year})" if self.year else ""
        return f"TabMetadata('{self.name}'{year_str}, order={self.order})"
```

**Attributes**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | str | Original tab name from openpyxl | "2025 Prog-metal" |
| `normalized_name` | str | Trimmed, validated name | "2025 Prog-metal" |
| `year` | Optional[int] | Extracted year for sorting | 2025 |
| `order` | int | Original position (0-based) | 0 |
| `is_prog_metal` | bool | Passes filter criteria | True |
| `estimated_rows` | Optional[int] | Row count (if scanned) | 200 |

**Usage Example**:

```python
# Created during enumeration
tab = TabMetadata(
    name="2025 Prog-metal",
    normalized_name="2025 Prog-metal",
    year=2025,
    order=0,
    is_prog_metal=True,
    estimated_rows=200
)

# Used for filtering
prog_metal_tabs = [t for t in all_tabs if t.is_prog_metal]

# Used for sorting
sorted_tabs = sorted(prog_metal_tabs, key=lambda t: (t.year or 9999, t.order))
```

---

## Data Flow

### 1. Tab Enumeration Phase

```
Google Sheets XLSX
    ↓
openpyxl workbook.sheetnames
    ↓
List[str] (raw tab names)
    ↓
GoogleSheetsService.enumerate_tabs()
    ↓
List[TabMetadata] (all tabs with metadata)
```

### 2. Tab Filtering Phase

```
List[TabMetadata] (all tabs)
    ↓
GoogleSheetsService.filter_tabs()
    ↓
List[TabMetadata] (only Prog-metal tabs)
    ↓
GoogleSheetsService.sort_tabs_chronologically()
    ↓
List[TabMetadata] (sorted oldest → newest)
```

### 3. Tab Processing Phase

```
For each TabMetadata in sorted list:
    ↓
Update SyncOperation.current_tab = tab.name
    ↓
GoogleSheetsService.fetch_albums_from_tab(tab.name)
    ↓
List[Dict[str, str]] (album data for this tab)
    ↓
SyncManager processes albums
    ↓
Update SyncOperation progress fields
```

### 4. Completion Phase

```
All tabs processed
    ↓
Clear SyncOperation.current_tab = ""
    ↓
Create SyncRecord with aggregated results
```

---

## Existing Models (No Changes)

### Album Model

**File**: `catalog/models.py`
**Changes**: None required

The existing `spotify_album_id` uniqueness constraint already handles cross-tab deduplication. Albums imported from multiple tabs are automatically skipped based on this field.

### SyncRecord Model

**File**: `catalog/models.py`
**Changes**: None required

Existing fields (`albums_created`, `albums_updated`, `albums_skipped`, `total_albums_in_catalog`) already aggregate results across all tabs. No tab-level granularity needed in historical records.

---

## State Transitions

### SyncOperation.current_tab Field

```
State Flow:
┌─────────────────────┐
│ current_tab = ""    │  (Initial/Completed)
└──────────┬──────────┘
           │
           ↓ (Sync starts)
┌─────────────────────┐
│ current_tab = "2017"│  (Processing oldest tab)
└──────────┬──────────┘
           │
           ↓ (Tab complete)
┌─────────────────────┐
│ current_tab = "2018"│  (Processing next tab)
└──────────┬──────────┘
           │
           ↓ (More tabs...)
┌───────────────────────┐
│ current_tab = "2025   │  (Processing newest tab)
│         Prog-metal"   │
└──────────┬────────────┘
           │
           ↓ (All tabs complete)
┌─────────────────────┐
│ current_tab = ""    │  (Cleared on success/failure)
└─────────────────────┘
```

**State Rules**:
- Empty string = No active tab processing
- Non-empty = Currently processing that tab
- Always cleared on sync completion (success or failure)
- Updated atomically with progress fields in single DB transaction

---

## Database Indexing

### No New Indexes Required

The `current_tab` field is:
- Only queried during active sync (1 concurrent operation at a time)
- Never used in WHERE clauses or JOINs
- Read frequently (UI polling) but writes are infrequent (tab transitions)

**Decision**: No index needed - sequential scan on single active row is faster than index overhead.

---

## Performance Considerations

### Memory Footprint

**TabMetadata List**:
- 11 tabs × ~100 bytes per dataclass = ~1.1 KB
- Negligible compared to album data (~50 KB per album)
- Safe to keep in memory for entire sync duration

**Database Load**:
- New field adds ~100 bytes per SyncOperation row
- Minimal impact: ~1.1 KB for last 10 syncs

### Query Impact

**Reads (UI polling every 2s)**:
```python
sync_op = SyncOperation.objects.filter(
    Q(status="pending") | Q(status="running")
).first()
# Now includes: sync_op.current_tab
```
- +0ms overhead (field already loaded with row)

**Writes (tab transitions)**:
```python
sync_op.current_tab = "2025 Prog-metal"
sync_op.save(update_fields=["current_tab", "stage_message"])
```
- ~11 writes per sync (one per tab)
- Negligible compared to 250+ album writes

---

## Validation Rules

### TabMetadata Validation

**During Creation**:

```python
def create_tab_metadata(name: str, order: int) -> Optional[TabMetadata]:
    """Create TabMetadata with validation."""
    # Normalize name
    normalized = name.strip()

    # Validate ASCII (Google Sheets tab names are ASCII)
    if not normalized.isascii():
        logger.warning(f"Non-ASCII tab name: {name}")
        return None

    # Extract year
    year = extract_year_from_tab_name(normalized)

    # Check if Prog-metal
    is_pm = is_prog_metal_tab(normalized)

    return TabMetadata(
        name=name,
        normalized_name=normalized,
        year=year,
        order=order,
        is_prog_metal=is_pm
    )
```

### SyncOperation.current_tab Validation

**Django Model Validation**:

```python
class SyncOperation(models.Model):
    # ... existing fields ...

    current_tab = models.CharField(
        max_length=100,  # Longest observed: "2020 Reissues & Special Release" (34 chars)
        blank=True,
        default="",
        validators=[
            # Optional: Add custom validator for tab name format
        ]
    )

    def clean(self):
        """Validate current_tab field."""
        if self.current_tab and len(self.current_tab) > 100:
            raise ValidationError("current_tab exceeds max length")
        # Tab name should be ASCII
        if self.current_tab and not self.current_tab.isascii():
            raise ValidationError("current_tab must be ASCII")
```

---

## Testing Data Structures

### Test Fixtures

**File**: `tests/fixtures/multi_tab_sheet.xlsx`

Expected structure:
- Tab "2023 Prog-metal" (5 test albums)
- Tab "2024 Prog-metal" (5 test albums)
- Tab "2025 Prog-metal" (5 test albums)
- Tab "2024 Prog-rock" (should be filtered out)
- Tab "Statistics" (should be filtered out)

**TabMetadata Test Cases**:

```python
# Valid Prog-metal tabs
assert TabMetadata("2025 Prog-metal", 0).is_prog_metal == True
assert TabMetadata("2017", 1).is_prog_metal == True

# Invalid tabs (should be filtered)
assert TabMetadata("2025 Prog-rock", 0).is_prog_metal == False
assert TabMetadata("Statistics", 1).is_prog_metal == False
assert TabMetadata("2020 Reissues & Special Release", 2).is_prog_metal == False

# Year extraction
assert TabMetadata("2025 Prog-metal", 0).year == 2025
assert TabMetadata("2017", 0).year == 2017
assert TabMetadata("Statistics", 0).year is None
```

---

## Migration Rollback Strategy

**Rollback Migration** (`0005_syncoperation_current_tab` → `0004_syncoperation`):

```python
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0005_syncoperation_current_tab'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='syncoperation',
            name='current_tab',
        ),
    ]
```

**Data Loss on Rollback**:
- `current_tab` field values are lost
- Safe because: Field only tracks ephemeral processing state
- Historical data (SyncRecord) unaffected

---

## Summary

| Entity | Type | Persistence | Purpose |
|--------|------|-------------|---------|
| `SyncOperation.current_tab` | CharField(100) | Database (new field) | Track active tab name for UI display |
| `TabMetadata` | dataclass | Ephemeral (memory-only) | Store tab metadata during processing |
| `Album` | Existing model | Database (no changes) | Deduplicate via `spotify_album_id` |
| `SyncRecord` | Existing model | Database (no changes) | Aggregate multi-tab results |

**Total Schema Changes**: 1 field added to existing model (minimal impact)
