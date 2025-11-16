# Data Model: Just-in-Time Spotify API Usage

**Date**: 2025-11-07
**Feature**: Just-in-Time Spotify API Usage
**Branch**: 006-jit-spotify-api

## Overview

This document defines the data model changes required to support just-in-time loading of Spotify cover art and metadata. The model extends the existing `Album` model with cache fields to store fetched data.

## Entity Definitions

### Album (Modified)

Represents a music album with on-demand cached Spotify data.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | Primary key, auto-increment | Existing: Unique album identifier |
| `name` | String(500) | Not null | Existing: Album title |
| `release_date` | Date | Not null | Existing: Album release date |
| `spotify_url` | String(200) | Nullable, indexed | Existing: Spotify album URL from Google Sheets |
| `artist` | ForeignKey | Not null | Existing: Reference to Artist model |
| `genres` | ManyToMany | | Existing: Album genres |
| `vocal_style` | ForeignKey | Nullable | Existing: Vocal style category |
| `spotify_cover_url` | String(500) | **NEW: Nullable, indexed** | Cached Spotify cover art URL |
| `spotify_cover_cached_at` | DateTime | **NEW: Nullable** | Timestamp when cover art was cached |
| `spotify_metadata_json` | JSON | **NEW: Nullable** | Cached detailed Spotify metadata (genres, tracks, popularity) |
| `spotify_metadata_cached_at` | DateTime | **NEW: Nullable** | Timestamp when metadata was cached |

**Validation Rules**:
- `spotify_cover_url` must be a valid HTTP(S) URL if not null
- `spotify_cover_cached_at` must be set when `spotify_cover_url` is set
- `spotify_metadata_cached_at` must be set when `spotify_metadata_json` is set
- `spotify_url` format must match `https://open.spotify.com/album/{22-char-id}`

**Relationships**:
- Belongs to one `Artist` (existing many-to-one)
- Has many `Genre` (existing many-to-many)
- Has one `VocalStyle` (existing many-to-one, nullable)

**State Transitions**:
1. **Initial State**: Album imported from Google Sheets
   - `spotify_url` populated from sheet (if available)
   - `spotify_cover_url` = NULL
   - `spotify_metadata_json` = NULL

2. **Cover Cached State**: User views album in catalog
   - Cover art fetched from Spotify API
   - `spotify_cover_url` = URL from Spotify
   - `spotify_cover_cached_at` = current timestamp

3. **Metadata Cached State**: User views album detail page
   - Detailed metadata fetched from Spotify API
   - `spotify_metadata_json` = full album data
   - `spotify_metadata_cached_at` = current timestamp

4. **Cache Refreshed State**: Administrator runs refresh command
   - `spotify_cover_url` and/or `spotify_metadata_json` re-fetched
   - `spotify_cover_cached_at` and/or `spotify_metadata_cached_at` updated

**Indexes**:
- `spotify_url` (existing or new, for lookup by URL)
- `spotify_cover_url` (new, for checking cache status)
- `spotify_cover_cached_at` (new, for cache freshness queries)

---

### Artist (Unchanged)

No changes required to the Artist model.

---

### Genre (Unchanged)

No changes required to the Genre model.

---

### VocalStyle (Unchanged)

No changes required to the VocalStyle model.

---

## Database Migration Plan

### Migration 1: Add Cache Fields

**Migration Name**: `0006_add_spotify_cache_fields.py`

**Operations**:
1. Add `spotify_cover_url` field (nullable VARCHAR(500))
2. Add `spotify_cover_cached_at` field (nullable TIMESTAMP)
3. Add `spotify_metadata_json` field (nullable JSONB for PostgreSQL, TEXT for SQLite)
4. Add `spotify_metadata_cached_at` field (nullable TIMESTAMP)
5. Create index on `spotify_cover_url`
6. Create index on `spotify_cover_cached_at`

**Rollback Strategy**:
- Drop indexes
- Drop fields (safe as they are nullable and newly added)

**Data Migration**:
- None required (fields start as NULL)

---

## Cache Data Structure

### Spotify Metadata JSON Schema

The `spotify_metadata_json` field stores a JSON object with the following structure:

```json
{
  "name": "Album Name",
  "artist": "Artist Name",
  "release_date": "2025-01-15",
  "total_tracks": 12,
  "popularity": 85,
  "genres": ["progressive metal", "djent"],
  "tracks": [
    {
      "track_number": 1,
      "name": "Track Name",
      "duration_ms": 345000,
      "explicit": false
    }
  ],
  "label": "Record Label Name",
  "copyrights": [
    {
      "text": "© 2025 Record Label",
      "type": "C"
    }
  ],
  "external_urls": {
    "spotify": "https://open.spotify.com/album/abc123..."
  }
}
```

**Field Descriptions**:
- `name`: Album title from Spotify (may differ from Google Sheets)
- `artist`: Primary artist name from Spotify
- `release_date`: ISO 8601 date string
- `total_tracks`: Number of tracks on album
- `popularity`: Spotify popularity score (0-100)
- `genres`: Array of genre strings from Spotify
- `tracks`: Array of track objects with details
- `label`: Record label name
- `copyrights`: Copyright information
- `external_urls`: Links to Spotify

**Usage**:
- Displayed on album detail page
- Used for enhanced search/filtering (future feature)
- Provides track listing for users

---

## Query Patterns

### Check if Cover Art is Cached

```python
album = Album.objects.filter(id=album_id).values('spotify_cover_url').first()
if album and album['spotify_cover_url']:
    # Cover art is cached
    return album['spotify_cover_url']
else:
    # Need to fetch from Spotify API
    return fetch_and_cache_cover_art(album_id)
```

### Get Albums Needing Cache Refresh

```python
from django.utils import timezone
from datetime import timedelta

# Albums with no cached cover art
albums_no_cache = Album.objects.filter(
    spotify_url__isnull=False,
    spotify_cover_url__isnull=True
)

# Albums with stale cache (older than 30 days)
stale_threshold = timezone.now() - timedelta(days=30)
albums_stale_cache = Album.objects.filter(
    spotify_cover_cached_at__lt=stale_threshold
)
```

### Fetch Albums with Cached Cover Art for Catalog

```python
albums = Album.objects.select_related('artist', 'vocal_style').prefetch_related('genres').all()

# Check cache in template/view
for album in albums:
    if album.spotify_cover_url:
        # Use cached URL
        cover_url = album.spotify_cover_url
    else:
        # Return placeholder, trigger lazy load
        cover_url = '/static/placeholder.jpg'
```

### Update Cache After Fetching

```python
from django.db import transaction
from django.utils import timezone

@transaction.atomic
def cache_cover_art(album_id: int, cover_url: str) -> None:
    album = Album.objects.select_for_update().get(id=album_id)

    # Check if another request already cached it
    if album.spotify_cover_url:
        return

    album.spotify_cover_url = cover_url
    album.spotify_cover_cached_at = timezone.now()
    album.save(update_fields=['spotify_cover_url', 'spotify_cover_cached_at'])
```

---

## Model Validation

### Album Model Validation

Add custom validation method to `Album` model:

```python
from django.core.exceptions import ValidationError
import re

def clean(self):
    super().clean()

    # Validate spotify_url format
    if self.spotify_url:
        pattern = r'open\.spotify\.com/album/[a-zA-Z0-9]{22}'
        if not re.search(pattern, self.spotify_url):
            raise ValidationError({
                'spotify_url': 'Invalid Spotify album URL format'
            })

    # Ensure cache timestamps are set when cache fields are populated
    if self.spotify_cover_url and not self.spotify_cover_cached_at:
        raise ValidationError({
            'spotify_cover_cached_at': 'Must be set when cover URL is cached'
        })

    if self.spotify_metadata_json and not self.spotify_metadata_cached_at:
        raise ValidationError({
            'spotify_metadata_cached_at': 'Must be set when metadata is cached'
        })
```

---

## Testing Considerations

### Unit Tests

1. **Test cache field validation**
   - Cover URL without timestamp raises error
   - Metadata JSON without timestamp raises error
   - Invalid Spotify URL format raises error

2. **Test state transitions**
   - Album moves from uncached → cover cached → metadata cached
   - Cache timestamps are set correctly
   - Multiple refreshes update timestamps

### Integration Tests

1. **Test concurrent cache updates**
   - Multiple requests for same album don't duplicate API calls
   - select_for_update() prevents race conditions

2. **Test query performance**
   - Indexes improve query speed for cache checks
   - select_related() reduces query count for catalog view

### Contract Tests

1. **Test metadata JSON schema**
   - Fetched metadata matches expected structure
   - Required fields are present
   - Data types are correct

---

## Migration Script Example

```python
# Generated by Django 5.2.8 on 2025-11-07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_syncoperation_current_tab'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='spotify_cover_url',
            field=models.URLField(max_length=500, blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name='album',
            name='spotify_cover_cached_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='album',
            name='spotify_metadata_json',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='album',
            name='spotify_metadata_cached_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='album',
            index=models.Index(fields=['spotify_cover_cached_at'], name='catalog_alb_spotify_cover_idx'),
        ),
    ]
```

---

## Performance Considerations

### Database Size Impact

**Estimation**:
- 500 albums in catalog
- Average cover URL length: 200 characters = 200 bytes
- Average metadata JSON size: 5KB
- Total additional storage: (200 bytes + 5KB) × 500 ≈ 2.6 MB

**Impact**: Negligible - database size increase is minimal.

### Query Performance

**Indexes**:
- `spotify_cover_url` index: Speeds up cache status checks
- `spotify_cover_cached_at` index: Speeds up stale cache queries

**Expected Performance**:
- Cache check query: <5ms (indexed lookup)
- Catalog list query: <50ms (with select_related/prefetch_related)
- Cache update: <10ms (single row update with index)

---

## Future Enhancements

### Potential Additions (Not in Current Scope)

1. **Cache Statistics Model**
   - Track cache hit/miss rates
   - Monitor API usage patterns
   - Identify frequently accessed albums

2. **Batch Cache Preloading**
   - Pre-fetch cover art for top N albums
   - Background job to warm cache
   - Reduce cold-start latency

3. **Cache Versioning**
   - Track when Spotify data changes
   - Automatically invalidate stale caches
   - Compare cached vs. live data

4. **Error Tracking**
   - Log failed API requests per album
   - Retry failed fetches automatically
   - Alert on persistent failures
