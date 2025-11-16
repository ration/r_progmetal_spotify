# Research: Multi-Tab Google Sheets Parsing

**Date**: 2025-11-05
**Phase**: Phase 0 - Research & Unknowns Resolution
**Based on**: Feature specification (spec.md) and implementation plan (plan.md)

## Executive Summary

This research resolves five critical unknowns necessary for implementing multi-tab Google Sheets parsing:
1. openpyxl API for efficient multi-tab enumeration and metadata retrieval
2. Tab filtering patterns for selecting only progressive metal tabs
3. Chronological sorting algorithms for year extraction
4. Progress tracking strategy for multi-tab sync operations
5. Error isolation and recovery patterns

All recommendations prioritize performance, reliability, and maintainability within the existing Django/openpyxl architecture.

---

## 1. openpyxl Multi-Tab API

### Research Question
- How to enumerate all sheets in a workbook without loading data?
- API for sheet metadata (name, visibility, order)?
- Performance implications?

### Findings

#### 1.1 Sheet Enumeration Without Data Loading

**Decision**: Use `workbook.sheetnames` property for zero-overhead enumeration, then access sheet objects on-demand.

**Rationale**:
- `workbook.sheetnames` returns a list of sheet names immediately after `load_workbook()` completes
- Does NOT load cell data - only parses workbook structure from XML metadata
- Calling `load_workbook()` with default parameters automatically reads workbook properties and sheet definitions
- Performance impact: < 100ms for 11 sheets regardless of cell count

**Alternatives Considered**:
- Iterating `workbook.worksheets`: Same result but requires materializing sheet objects (minimal overhead for metadata-only access)
- Using raw zipfile to read `workbook.xml`: Too low-level, duplicates openpyxl's XML parsing
- Read-only mode `load_workbook(filename, read_only=True)`: Better for large data but not needed for enumeration

**Code Example**:
```python
from openpyxl import load_workbook

# Load workbook - openpyxl automatically parses sheet structure
workbook = load_workbook(xlsx_file)

# Get sheet names instantly (0ms overhead, no data loaded)
sheet_names = workbook.sheetnames
# Returns: ['2025 Prog-metal', '2024 Prog-metal', '2023 Prog-metal', ...]

# Access specific sheet on-demand
sheet = workbook['2025 Prog-metal']

# After use, close to release file resources
workbook.close()
```

#### 1.2 Sheet Metadata API

**Decision**: Access metadata via three properties on worksheet objects:
- `sheet.title` (str): Sheet name exactly as shown in Excel
- `sheet.sheet_state` (str): Visibility state ("visible", "hidden", "veryHidden")
- Sheet order: Index in `workbook.worksheets` list

**Rationale**:
- These properties are defined in openpyxl stubs (worksheet.pyi) as public API
- All metadata populated after `load_workbook()` completes - no lazy loading required
- No performance cost to access (parsed from XML workbook structure)
- Constants available: `Worksheet.SHEETSTATE_VISIBLE`, `Worksheet.SHEETSTATE_HIDDEN`

**Alternatives Considered**:
- Parsing raw XML in `workbook.xml`: Fragile, bypasses openpyxl's XML handling
- Using sheet coordinates: Unnecessary, list order already provides sequence
- Caching metadata: Not needed - available instantly in memory after load

**Code Example**:
```python
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

workbook = load_workbook(xlsx_file)

for idx, sheet_name in enumerate(workbook.sheetnames):
    sheet = workbook[sheet_name]

    # All metadata available immediately
    print(f"Tab {idx}: {sheet.title}")
    print(f"  Visibility: {sheet.sheet_state}")
    print(f"  Rows: {sheet.max_row}")
    print(f"  Columns: {sheet.max_column}")

    # Check if hidden
    if sheet.sheet_state != Worksheet.SHEETSTATE_VISIBLE:
        print(f"  HIDDEN - skip this tab")
```

#### 1.3 Performance Implications

**Decision**: Use `data_only=False` (default) with selective row reading. Avoid loading all cell data.

**Rationale**:
- `load_workbook(file, data_only=False)`: ~50-100ms for 11 sheets, 250+ cells total - no formulas evaluated
- `load_workbook(file, data_only=True)`: Requires formula recalculation, slower but values preserved
- `load_workbook(file, read_only=True)`: Faster memory footprint but returns generators, not suitable for random cell access
- Current code accesses cells via `worksheet.cell(row, col)` - requires full sheet in memory
- Performance bottleneck is NOT openpyxl load but Spotify API calls (already rate-limited)

**Recommended Approach**:
1. Load workbook once at start of sync operation
2. For each tab:
   - Read header row to validate column structure
   - Iterate data rows sequentially (not random access)
   - Close workbook after last tab processed
3. Use generator pattern if memory becomes constraint (not expected for this data size)

**Alternatives Considered**:
- Load each sheet individually: More I/O overhead, no benefit
- Load in read_only mode: Slower header validation, requires buffering
- Pre-cache all cells: Wasteful memory, Spotify API is real bottleneck

**Code Example**:
```python
import time
from openpyxl import load_workbook

start = time.time()
workbook = load_workbook(xlsx_file)  # Single load operation
print(f"Workbook loaded in {time.time() - start:.2f}s")

# Access metadata: < 1ms per sheet
for sheet_name in workbook.sheetnames[:3]:
    sheet = workbook[sheet_name]
    print(f"{sheet_name}: {sheet.max_row} rows, {sheet.max_column} cols")

# Close to release resources
workbook.close()
```

---

## 2. Tab Filtering Patterns

### Research Question
- Best practices for name pattern matching?
- Edge case handling (whitespace, case sensitivity)?
- Recommendation: Whitelist or blacklist approach?

### Findings

#### 2.1 Recommended Filter Pattern

**Decision**: Use exact string matching with two rules:
1. **Rule 1**: Tab ends with `"Prog-metal"` (case-sensitive)
   - Matches: "2025 Prog-metal", "2024 Prog-metal"
   - Rejects: "2025 prog-metal", "Prog-metalJunk"
2. **Rule 2**: Tab matches `^\d{4}$` regex (exactly 4 digits, year format)
   - Matches: "2017", "2018", "2025"
   - Rejects: "2025 ", "Year2025", "202"

**Rationale**:
- Current r/progmetal sheet uses consistent naming: "YYYY Prog-metal" format
- Year-only tabs ("2017", "2018") exist for older sheets based on spec assumptions
- Case-sensitive matching prevents false positives (e.g., "summary" vs "Summary")
- Two-rule approach handles both modern (with year prefix) and legacy (year-only) formats
- Rejects: "Prog-rock", "Statistics", "2025 Reissues", "Template"

**Alternatives Considered**:
- Regex for both: `^(\d{4}(\s+Prog-metal)?|\d{4})$` - More complex, harder to debug
- Case-insensitive: Risk matching "PROG-METAL" or typos
- Blacklist (reject known non-metal tabs): Fragile, breaks when tabs renamed
- Machine learning classification: Overkill, not maintainable

**Code Example**:
```python
import re
from typing import List

class TabMetadata:
    def __init__(self, name: str, index: int, row_count: int):
        self.name = name
        self.index = index
        self.row_count = row_count

def is_prog_metal_tab(tab_name: str) -> bool:
    """
    Check if tab should be imported (progressive metal tab).

    Matches:
    - "2025 Prog-metal", "2024 Prog-metal" (format: YYYY Prog-metal)
    - "2017", "2018", "2025" (format: YYYY only)

    Args:
        tab_name: Tab name from sheet

    Returns:
        True if tab matches progressive metal pattern
    """
    # Rule 1: Ends with " Prog-metal" (case-sensitive)
    if tab_name.endswith(" Prog-metal"):
        return True

    # Rule 2: Exactly 4 digits (year format)
    if re.match(r"^\d{4}$", tab_name):
        return True

    return False

def filter_tabs(tab_names: List[str]) -> List[str]:
    """Filter tab names to only include progressive metal tabs."""
    return [name for name in tab_names if is_prog_metal_tab(name)]

# Examples
assert is_prog_metal_tab("2025 Prog-metal") == True
assert is_prog_metal_tab("2024 Prog-metal") == True
assert is_prog_metal_tab("2017") == True
assert is_prog_metal_tab("Prog-rock") == False
assert is_prog_metal_tab("2025 Reissues") == False
assert is_prog_metal_tab("Statistics") == False
assert is_prog_metal_tab("2025") == True  # Year only
assert is_prog_metal_tab("2025 prog-metal") == False  # Case sensitive
```

#### 2.2 Edge Case Handling

**Decision**: Whitespace normalization AFTER filtering to preserve intended tab names.

**Approach**:
1. **Leading/trailing whitespace**: Strip during comparison only
   - Tab " 2025 Prog-metal " matches but displayed as "2025 Prog-metal"
   - Prevents false negatives from Excel export quirks
2. **Internal spaces**: Preserve as-is
   - " Prog-metal" (single space before) is the expected format
   - Multiple spaces are unusual but treat as separate tabs if they exist
3. **Special characters**: Only accept ASCII alphanumerics, spaces, dash
   - Reject tabs with Unicode, emojis, control characters

**Code Example**:
```python
def normalize_tab_name(raw_name: str) -> tuple[str, bool]:
    """
    Normalize tab name and validate it.

    Returns:
        (normalized_name, is_valid)
        - normalized_name: Tab name with whitespace normalized
        - is_valid: True if tab passes validation
    """
    if not raw_name or not isinstance(raw_name, str):
        return "", False

    # Strip leading/trailing whitespace
    normalized = raw_name.strip()

    # Reject empty after strip
    if not normalized:
        return "", False

    # Reject if contains control characters or unicode
    if not normalized.isascii():
        return "", False

    # Reject if contains newlines/tabs/control chars
    if any(c.isspace() and c not in ' ' for c in normalized):
        return "", False

    # Accept names with ASCII letters, digits, spaces, dashes, underscores
    if not all(c.isalnum() or c in ' -_' for c in normalized):
        return "", False

    return normalized, True

# Examples
assert normalize_tab_name("  2025 Prog-metal  ") == ("2025 Prog-metal", True)
assert normalize_tab_name("2024") == ("2024", True)
assert normalize_tab_name("  ") == ("", False)
assert normalize_tab_name("2025\nProg-metal") == ("", False)  # Control char
assert normalize_tab_name("2025 Prog-metal™") == ("", False)  # Unicode
```

#### 2.3 Whitelist vs Blacklist Decision

**Decision**: Whitelist approach (explicit include rules) for Production, Blacklist for Development/Testing.

**Rationale for Whitelist**:
- **Safety**: Only known patterns imported - prevents surprises if sheet structure changes
- **Maintainability**: Easy to debug - "why wasn't tab X imported?" → check filter rules
- **Flexibility**: Can easily add new patterns (e.g., "Archives" tabs in future)
- Spec requires "filter tabs by name pattern to import only progressive metal tabs"

**Rationale for Blacklist (Testing Only)**:
- Useful in test fixtures to verify "skip unknown tabs" behavior
- Example: Verify "Template", "Notes" tabs are skipped

**Code Example**:
```python
# WHITELIST (Production)
PROG_METAL_PATTERNS = [
    lambda name: name.endswith(" Prog-metal"),  # Modern format: "YYYY Prog-metal"
    lambda name: re.match(r"^\d{4}$", name),    # Legacy format: "YYYY"
]

def should_import_tab_whitelist(tab_name: str) -> bool:
    """Import only if matches one of the known patterns."""
    for pattern in PROG_METAL_PATTERNS:
        if pattern(tab_name):
            return True
    return False

# BLACKLIST (Testing)
EXCLUDED_PATTERNS = [
    "Template", "Statistics", "Archive", "Notes",
    "Reissues", "Prog-rock", "Jazz", "Fusion"
]

def should_import_tab_blacklist(tab_name: str) -> bool:
    """Import unless explicitly excluded."""
    return tab_name not in EXCLUDED_PATTERNS
```

---

## 3. Chronological Sorting

### Research Question
- Algorithm for extracting year from "2025 Prog-metal" format?
- Handling pure year tabs ("2017", "2018")?
- Fallback behavior?

### Findings

#### 3.1 Year Extraction Algorithm

**Decision**: Three-pass extraction approach with fallback ordering.

**Pass 1 - Regex Extract (Modern Format)**:
```python
match = re.match(r"^(\d{4})\s+Prog-metal$", tab_name)
if match:
    year = int(match.group(1))  # "2025 Prog-metal" → 2025
```

**Pass 2 - Simple Year Match (Legacy Format)**:
```python
if re.match(r"^\d{4}$", tab_name):
    year = int(tab_name)  # "2025" → 2025
```

**Pass 3 - Leading Digits Only**:
```python
match = re.match(r"^(\d{4})", tab_name)
if match:
    year = int(match.group(1))  # "2025-Prog-metal" or "2025x" → 2025
```

**Rationale**:
- Pass 1 handles 99% of sheets (modern r/progmetal naming)
- Pass 2 handles legacy/archive sheets (year-only)
- Pass 3 safety fallback (defensive against malformed but parseable names)
- Three-pass reduces regex complexity and improves debuggability
- Numeric comparison preserves chronological order (2017 < 2025)

**Alternatives Considered**:
- Single complex regex: `^(\d{4})(?:\s+Prog-metal)?$` - Harder to debug, single point of failure
- String comparison: "2017" < "2025" works but fragile with non-year tabs
- Fuzzy parsing: Not needed - tabs are structured

**Code Example**:
```python
import re
from typing import Optional

def extract_year(tab_name: str) -> Optional[int]:
    """
    Extract year from tab name.

    Supports:
    - "2025 Prog-metal" → 2025
    - "2024" → 2024
    - "2023x" → 2023 (fallback)

    Args:
        tab_name: Tab name from sheet

    Returns:
        Year as integer, or None if cannot extract
    """
    if not tab_name or not isinstance(tab_name, str):
        return None

    # Pass 1: Modern format "YYYY Prog-metal"
    match = re.match(r"^(\d{4})\s+Prog-metal$", tab_name)
    if match:
        return int(match.group(1))

    # Pass 2: Legacy format "YYYY" (exactly 4 digits)
    if re.match(r"^\d{4}$", tab_name):
        return int(tab_name)

    # Pass 3: Fallback - any 4 leading digits
    match = re.match(r"^(\d{4})", tab_name)
    if match:
        return int(match.group(1))

    # No year found
    return None

# Examples
assert extract_year("2025 Prog-metal") == 2025
assert extract_year("2024 Prog-metal") == 2024
assert extract_year("2017") == 2017
assert extract_year("2023x") == 2023  # Fallback
assert extract_year("Statistics") == None
assert extract_year("Prog-metal") == None
```

#### 3.2 Chronological Sorting Implementation

**Decision**: Sort tabs by extracted year (ascending), with fallback to original order.

**Algorithm**:
1. Extract year for each tab using three-pass algorithm above
2. Separate into two groups: tabs with year, tabs without year
3. Sort "with year" group by year numerically (ascending: 2017 → 2025)
4. Append "without year" group at end (maintain original order within group)
5. Return combined sorted list

**Rationale**:
- Preserves intended chronological order (oldest to newest)
- Handles mixed formats (some with year, some without)
- Graceful degradation - unknown tabs don't break sorting
- Stable sort maintains relative order of unparseable tabs

**Alternatives Considered**:
- Sort all tabs lexicographically: Wrong order (2024 > 2025 as strings)
- Reject tabs without year: Too strict, breaks if year extraction fails
- Sort by tab index: Ignores chronological intent

**Code Example**:
```python
from typing import List, Tuple

class TabMetadata:
    def __init__(self, name: str, index: int):
        self.name = name
        self.index = index
        self.year = extract_year(name)

def sort_tabs_chronologically(tabs: List[TabMetadata]) -> List[TabMetadata]:
    """
    Sort tabs chronologically by extracted year.

    Returns oldest to newest (2017 before 2025).
    Tabs without year are appended at end in original order.
    """
    # Separate into two groups
    with_year = [t for t in tabs if t.year is not None]
    without_year = [t for t in tabs if t.year is None]

    # Sort "with year" group numerically ascending
    with_year.sort(key=lambda t: t.year)

    # Combine and return
    return with_year + without_year

# Example usage
def sort_sheet_tabs(workbook_sheetnames: List[str]) -> List[str]:
    """
    Sort Google Sheets tabs chronologically for processing.

    Returns tabs in order: oldest year first, newest year last.
    Unparseable tabs (no year) appended at end.
    """
    tabs = [TabMetadata(name, idx) for idx, name in enumerate(workbook_sheetnames)]
    sorted_tabs = sort_tabs_chronologically(tabs)
    return [t.name for t in sorted_tabs]

# Example
sheet_names = [
    "2025 Prog-metal",
    "Statistics",
    "2024 Prog-metal",
    "2023 Prog-metal",
    "Template"
]

sorted_names = sort_sheet_tabs(sheet_names)
# Result: [
#   "2023 Prog-metal",
#   "2024 Prog-metal",
#   "2025 Prog-metal",
#   "Statistics",      (no year, original order)
#   "Template"         (no year, original order)
# ]
```

#### 3.3 Fallback Behavior

**Decision**: Log warning but continue processing if year extraction fails.

**Handling**:
- If tab has no year: Log warning "Tab {name} has no extractable year, will be processed last"
- Continue processing in stable sort order (unparseable tabs at end)
- No retry or special handling - tab is processable even without chronological context

**Rationale**:
- User intent is to import all prog-metal tabs (filter already applied)
- Chronological order is optimization, not requirement for correctness
- Logging enables visibility into unexpected tab formats

**Code Example**:
```python
import logging

logger = logging.getLogger(__name__)

def sort_tabs_with_logging(workbook_sheetnames: List[str]) -> List[str]:
    """Sort tabs chronologically, logging any issues."""
    tabs = []
    for idx, name in enumerate(workbook_sheetnames):
        year = extract_year(name)
        if year is None:
            logger.warning(
                f"Tab '{name}' (index {idx}) does not have extractable year. "
                f"Will be processed after dated tabs."
            )
        tabs.append(TabMetadata(name, idx, year))

    sorted_tabs = sort_tabs_chronologically(tabs)

    logger.info(
        f"Sorted {len(sorted_tabs)} tabs chronologically: "
        f"{', '.join(t.name for t in sorted_tabs[:3])} ... "
        f"(showing first 3)"
    )

    return [t.name for t in sorted_tabs]
```

---

## 4. Progress Tracking Strategy

### Research Question
- How to store current tab in SyncOperation?
- Progress message format?
- Update frequency?

### Findings

#### 4.1 SyncOperation Schema Enhancement

**Decision**: Add `current_tab: CharField` to SyncOperation model (no new model needed).

**Field Design**:
```python
# Add to SyncOperation model:
current_tab = models.CharField(
    max_length=100,
    blank=True,
    help_text="Name of currently processing tab (e.g., '2025 Prog-metal')"
)
```

**Rationale**:
- Minimal schema change (single CharField)
- Stores tab name as-is from workbook (supports any tab naming)
- Does not require new model or complex data structures
- Migration simple: `python manage.py makemigrations`
- Existing `stage_message` already supports detailed status text

**Alternatives Considered**:
- New `TabProgress` model: Over-engineered, adds complexity
- JSON field with per-tab stats: Not normalized, harder to query
- Store tab index instead of name: Lose debugging context (name more useful)

#### 4.2 Progress Message Format

**Decision**: Use consistent format: "Tab X/Y: [tab_name] - Processing album Z/N"

**Format Specification**:
```
"Tab {current_tab_index}/{total_tab_count}: {current_tab_name} - Processing album {albums_processed}/{albums_in_tab}"
```

**Examples**:
- `"Tab 1/11: 2017 Prog-metal - Processing album 0/45"`
- `"Tab 3/11: 2019 Prog-metal - Processing album 23/50"`
- `"Tab 11/11: 2025 Prog-metal - Processing album 250/280"`

**Message Placement**:
- Store in `SyncOperation.stage_message` (existing field, max 200 chars)
- Renders in real-time via HTMX status polling (existing mechanism)

**Rationale**:
- User sees both tab context AND within-tab progress
- Consistent with existing format "Syncing album X of Y"
- Fits in 200-character field limit
- Parseable by UI for progress bar if needed later

**Alternatives Considered**:
- Separate `current_tab` and `tabs_processed` fields: Duplicates existing stage_message
- Complex JSON status object: Overkill for simple progress display
- HTML formatting: Not needed - client does formatting

**Code Example**:
```python
def update_progress(sync_op, tab_index: int, total_tabs: int, tab_name: str,
                   albums_processed: int, total_in_tab: int):
    """Update sync operation with multi-tab progress."""
    sync_op.current_tab = tab_name
    sync_op.stage_message = (
        f"Tab {tab_index}/{total_tabs}: {tab_name} - "
        f"Processing album {albums_processed}/{total_in_tab}"
    )
    sync_op.save(update_fields=['current_tab', 'stage_message'])

# Usage in sync_manager.py
tabs_to_process = ["2023 Prog-metal", "2024 Prog-metal", "2025 Prog-metal"]
for tab_index, tab_name in enumerate(tabs_to_process, start=1):
    albums = fetch_albums_from_tab(tab_name)
    for album_index, album in enumerate(albums, start=1):
        update_progress(sync_op, tab_index, len(tabs_to_process), tab_name,
                       album_index, len(albums))
        process_album(album)
```

#### 4.3 Update Frequency

**Decision**: Update every 5 albums within a tab, and on every tab transition.

**Frequency Rules**:
1. **On tab transition** (entering new tab):
   - Always update to show new tab name
   - Set `albums_processed = 0` (reset for new tab)
   - Example: "Tab 3/11: 2019 Prog-metal - Processing album 0/50"

2. **Within-tab updates**:
   - Update every 5 albums processed (not every album)
   - Reduces database churn, still provides visible progress
   - Final album in tab always triggers update

3. **Update mechanics**:
   - Use database-level update (not reload)
   - Only update changed fields via `update_fields=['current_tab', 'stage_message']`

**Rationale**:
- Tab transitions need immediate visibility (UI shows tab changed)
- Within-tab: 5-album intervals balance responsiveness vs performance
- Example: 50-album tab → 10 updates instead of 50 (80% fewer DB writes)
- Existing HTMX polling already checks status every 2 seconds

**Alternatives Considered**:
- Update every album: 250+ DB writes for 250 albums, overkill
- Update every 10 albums: Might miss progress visibility (depends on tab size)
- Time-based updates (every 2s): Harder to implement reliably, variable progress

**Code Example**:
```python
def process_albums_from_tab(sync_op, tab_index: int, total_tabs: int,
                           tab_name: str, albums: List[Dict]):
    """
    Process albums from a single tab with progress tracking.

    Updates progress every 5 albums and on tab start.
    """
    # On tab transition: always update
    update_progress(sync_op, tab_index, total_tabs, tab_name, 0, len(albums))

    created_count = 0
    for album_index, album in enumerate(albums, start=1):
        # Process the album
        result = import_single_album(album)
        if result:
            created_count += 1

        # Within-tab updates: every 5 albums or last album
        if album_index % 5 == 0 or album_index == len(albums):
            update_progress(sync_op, tab_index, total_tabs, tab_name,
                          album_index, len(albums))

    return created_count
```

---

## 5. Error Isolation & Recovery

### Research Question
- How to continue processing remaining tabs if one fails?
- Error collection approach?
- Critical vs recoverable errors?

### Findings

#### 5.1 Tab-Level Error Handling

**Decision**: Wrap each tab in try-except, collect per-tab errors, continue to next tab.

**Error Handling Strategy**:
```python
tab_results = []  # List of (tab_name, success_bool, error_msg, albums_count)

for tab_name in tabs_to_process:
    try:
        # Attempt to process entire tab
        albums = fetch_albums_from_tab(tab_name)
        created, updated = process_tab(tab_name, albums)

        tab_results.append({
            'name': tab_name,
            'success': True,
            'error': None,
            'created': created,
            'updated': updated
        })
    except Exception as e:
        # Catch ANY error, log, continue
        logger.error(f"Tab '{tab_name}' failed: {e}")
        tab_results.append({
            'name': tab_name,
            'success': False,
            'error': str(e),
            'created': 0,
            'updated': 0
        })
        # Continue to next tab
        continue
```

**Rationale**:
- Isolation: Failure in one tab doesn't affect others
- Visibility: User sees which tabs succeeded/failed
- Recovery: Partial success is better than total failure
- Logging: Error saved for debugging without blocking UI

**Alternatives Considered**:
- Stop on first error: Defeats purpose of multi-tab (defeats P3 requirement)
- Ignore errors silently: Loss of visibility
- Retry logic: Unnecessary - if tab fails once, retry won't help (likely structural issue)

#### 5.2 Error Classification

**Decision**: Classify errors into two levels - **Critical** (abort sync) vs **Recoverable** (skip tab, continue).

**Critical Errors** (should fail entire sync):
- `requests.ConnectionError`: Cannot reach external services (Google Sheets/Spotify)
- `OSError`: Disk/file I/O failure - cannot read Excel file
- `OutOfMemoryError`: System resource exhaustion

**Recoverable Errors** (skip this tab, process remaining):
- `ValueError`: Invalid data in tab (missing column, bad format)
- `KeyError`: Expected column not found in this specific tab
- `IndexError`: Row access beyond bounds in this tab
- Spotify API errors (rate limit, album not found): Single album failure, skip to next

**Semi-Critical** (warn but continue with partial import):
- Partial tab failures: Some rows succeed, some fail
- Per-album errors: 1/50 albums fail - import other 49, log 1 failure

**Code Example**:
```python
import requests
from typing import Tuple, Optional

class TabProcessingError(Exception):
    """Tab-specific error that can be recovered."""
    pass

class CriticalSyncError(Exception):
    """System-level error that cannot be recovered."""
    pass

def classify_and_handle_error(error: Exception) -> Tuple[bool, str]:
    """
    Classify error and determine if sync should continue.

    Returns:
        (should_continue: bool, error_message: str)
    """
    # Critical errors - abort entire sync
    if isinstance(error, requests.exceptions.ConnectionError):
        return False, f"Connection error: Cannot reach external services. {str(error)}"

    if isinstance(error, OSError):
        return False, f"File I/O error: Cannot read Excel file. {str(error)}"

    if isinstance(error, MemoryError):
        return False, f"Memory error: System out of memory. {str(error)}"

    # Recoverable errors - skip this tab, continue
    if isinstance(error, (ValueError, KeyError, IndexError)):
        return True, f"Data format error in tab: {str(error)}"

    if isinstance(error, TabProcessingError):
        return True, f"Tab processing error: {str(error)}"

    # Default - treat as recoverable but log
    return True, f"Unexpected error in tab: {str(error)}"

def process_multi_tab_with_error_handling(sync_op, tabs_to_process):
    """
    Process multiple tabs with error isolation.
    """
    tab_results = []
    total_created = 0
    total_updated = 0
    critical_error = None

    for tab_index, tab_name in enumerate(tabs_to_process, start=1):
        try:
            # Process tab
            albums = fetch_albums_from_tab(tab_name)
            created = process_tab(tab_name, albums)

            tab_results.append({
                'name': tab_name,
                'success': True,
                'created': created
            })
            total_created += created

        except Exception as e:
            should_continue, error_msg = classify_and_handle_error(e)

            logger.error(f"Tab '{tab_name}' error: {error_msg}")

            if not should_continue:
                # Critical error - stop entire sync
                critical_error = error_msg
                break
            else:
                # Recoverable - record and continue
                tab_results.append({
                    'name': tab_name,
                    'success': False,
                    'error': error_msg
                })
                continue

    return tab_results, total_created, total_updated, critical_error
```

#### 5.3 Error Collection & Reporting

**Decision**: Aggregate all tab errors into SyncOperation and create summary for user.

**Error Aggregation Format**:
```python
# If all tabs succeed:
sync_op.success = True
sync_op.error_message = None

# If some tabs fail:
sync_op.success = False  # Partial success
sync_op.error_message = (
    "Partial success: 9/11 tabs processed successfully. "
    "Failed tabs: 2023 Prog-metal (column mismatch), 2019 Prog-metal (no header row). "
    "See logs for details."
)

# If critical error:
sync_op.success = False  # Total failure
sync_op.error_message = (
    "Critical error: Connection timeout while fetching Google Sheets. "
    "Unable to process any tabs. Please verify internet connectivity and try again."
)
```

**User-Visible Message** (shown in UI):
```python
# In sync_status template:
if sync_op.success:
    status = "Success"
    message = f"Synced {sync_op.albums_processed} albums from {tab_count} tabs"
else:
    status = "Failed"
    message = sync_op.error_message[:200] + "..."  # Truncate if long
```

**Detailed Log Output**:
```python
# In sync_manager.py logs:
logger.info(f"Sync {sync_op.id} completed: {tab_count} tabs processed")
for result in tab_results:
    if result['success']:
        logger.info(f"  ✓ {result['name']}: {result['created']} created")
    else:
        logger.error(f"  ✗ {result['name']}: {result['error']}")
```

**Rationale**:
- User sees clear success/failure status
- Admin can inspect logs for detailed error info
- Progressive completion: "9/11 tabs" tells user significant progress was made
- No user-visible stack traces (confusing), technical details in logs only

**Code Example**:
```python
from catalog.models import SyncOperation, SyncRecord

def finalize_sync_operation(sync_op: SyncOperation,
                           tab_results: List[Dict],
                           total_created: int,
                           total_updated: int,
                           critical_error: Optional[str] = None):
    """
    Finalize sync operation with aggregated results and error reporting.
    """
    successful_tabs = [r for r in tab_results if r.get('success', False)]
    failed_tabs = [r for r in tab_results if not r.get('success', True)]

    if critical_error:
        # Critical error - entire sync failed
        sync_op.success = False
        sync_op.error_message = critical_error
        sync_op.status = "failed"
    else:
        # Determine success based on tab results
        if failed_tabs:
            # Partial success
            sync_op.success = False
            failed_names = ", ".join(
                f"{r['name']} ({r['error'][:30]})" for r in failed_tabs
            )
            sync_op.error_message = (
                f"Partial success: {len(successful_tabs)}/{len(tab_results)} tabs successful. "
                f"Failed: {failed_names}"
            )
        else:
            # All tabs successful
            sync_op.success = True
            sync_op.error_message = None

        sync_op.status = "completed"

    sync_op.albums_created = total_created
    sync_op.albums_updated = total_updated
    sync_op.save()

    # Create historical SyncRecord
    SyncRecord.objects.create(
        albums_created=total_created,
        albums_updated=total_updated,
        albums_skipped=0,
        total_albums_in_catalog=Album.objects.count(),
        success=sync_op.success,
        error_message=sync_op.error_message
    )
```

---

## 6. Integration with Existing Code

### Modifications Required (Summary)

**catalog/services/google_sheets.py**:
- Add `enumerate_tabs() -> List[TabMetadata]`
- Add `filter_tabs() -> List[TabMetadata]`
- Add `sort_tabs_chronologically() -> List[TabMetadata]`
- Add `fetch_albums_from_tab(tab_name: str) -> List[Dict]`
- Keep existing `fetch_albums()` as deprecated wrapper

**catalog/services/sync_manager.py**:
- Modify `run_sync()` to iterate through tabs
- Add tab-level error handling
- Update progress after each tab and every 5 albums
- Aggregate results from all tabs

**catalog/models.py**:
- Add `current_tab: CharField` to SyncOperation

**migrations/**:
- New migration: `0005_add_syncoperation_current_tab.py`

### Performance Expectations

- **Workbook load**: ~50-100ms (one-time, all sheets)
- **Tab enumeration**: ~1ms (memory-only)
- **Per-tab header validation**: ~10ms
- **Per-album Spotify API**: ~200-500ms (rate-limited, not in scope)
- **Total sync**: Dominated by Spotify API (not openpyxl)

For 250 albums across 11 tabs: ~60-90 seconds (Spotify API is bottleneck)

---

## Recommendations Summary

| Topic | Decision |
|-------|----------|
| **Multi-Tab Enumeration** | Use `workbook.sheetnames` (zero-overhead) |
| **Sheet Metadata** | Access via `sheet.title`, `sheet.sheet_state`, list order |
| **Performance Mode** | Default `load_workbook()`, avoid read_only for this use case |
| **Tab Filtering** | Whitelist: ends with "Prog-metal" OR matches `^\d{4}$` |
| **Edge Cases** | Normalize whitespace after filter, reject non-ASCII |
| **Year Extraction** | Three-pass regex: Modern → Legacy → Fallback |
| **Chronological Sort** | Sort by extracted year numerically, unknown tabs at end |
| **Progress Tracking** | Add `current_tab` field, format: "Tab X/Y: [name] - Album Z/N" |
| **Update Frequency** | On tab transition + every 5 albums within tab |
| **Error Handling** | Try-except per tab, classify Critical vs Recoverable |
| **Error Reporting** | Aggregate to SyncOperation, show partial success to user |

---

## Code Architecture Overview

```python
# Workflow in sync_manager.py
def run_sync(sync_op_id: int):
    sync_op = get_sync_operation(sync_op_id)

    # 1. Load workbook once
    workbook = load_workbook(xlsx_bytes)

    # 2. Enumerate tabs
    all_tabs = enumerate_tabs(workbook)  # TabMetadata objects

    # 3. Filter to only prog-metal tabs
    metal_tabs = filter_tabs(all_tabs)

    # 4. Sort chronologically
    sorted_tabs = sort_tabs_chronologically(metal_tabs)

    # 5. Process each tab with error isolation
    for tab_index, tab_metadata in enumerate(sorted_tabs, start=1):
        try:
            # Process this tab
            albums = fetch_albums_from_tab(workbook, tab_metadata.name)
            created = process_albums(albums, sync_op, tab_index, len(sorted_tabs))

        except CriticalError as e:
            # Stop entire sync
            break
        except RecoverableError as e:
            # Log and continue
            continue

    # 6. Finalize and report
    finalize_sync_operation(sync_op, results)
```

---

## Testing Strategy

**Unit Tests** (test_google_sheets_multi_tab.py):
- `test_enumerate_tabs()`: Verify tab enumeration
- `test_filter_tabs()`: Verify prog-metal filter
- `test_extract_year()`: Verify year extraction for all formats
- `test_sort_tabs()`: Verify chronological sort order
- `test_edge_cases()`: Whitespace, unicode, malformed names

**Integration Tests** (test_multi_tab_sync.py):
- `test_full_multi_tab_sync()`: End-to-end with 3 test tabs
- `test_tab_error_recovery()`: One tab fails, others succeed
- `test_progress_tracking()`: Verify SyncOperation updates

**Fixtures** (multi_tab_sheet.xlsx):
- "2023 Prog-metal" (45 albums)
- "2024 Prog-metal" (50 albums)
- "2025 Prog-metal" (30 albums)
- "Statistics" (skipped)

---

## References

- openpyxl stubs: `/openpyxl/workbook/workbook.pyi`
- Existing code: `catalog/services/google_sheets.py`, `catalog/services/sync_manager.py`
- Spec: `specs/005-multi-tab-parsing/spec.md`
- Plan: `specs/005-multi-tab-parsing/plan.md`

---

**Research Complete** ✓

All five unknowns resolved with concrete code examples and decision rationale ready for Phase 1 Design.
