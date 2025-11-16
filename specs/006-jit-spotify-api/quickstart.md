# Quickstart: Just-in-Time Spotify API Usage

**Date**: 2025-11-07
**Feature**: Just-in-Time Spotify API Usage
**Branch**: 006-jit-spotify-api

## Overview

This guide walks you through setting up and using the just-in-time Spotify API loading feature. This feature optimizes Spotify API usage by loading cover art and metadata on-demand rather than during album import.

---

## Prerequisites

- Python 3.14 installed
- Django 5.2.8 project running (progmetal catalog app)
- Spotify API credentials (Client ID and Client Secret)
- PostgreSQL or SQLite database configured
- Google Sheets with album data

---

## Installation

### 1. Run Database Migrations

Apply the new database schema to add cache fields to the Album model:

```bash
# Local development
python manage.py migrate

# Docker
make migrate
```

**Expected Output**:
```
Operations to perform:
  Apply all migrations: catalog
Running migrations:
  Applying catalog.0006_add_spotify_cache_fields... OK
```

**Verification**:
```bash
python manage.py dbshell
```
```sql
-- Check that new fields exist
\d catalog_album  -- PostgreSQL
.schema catalog_album  -- SQLite

-- You should see:
-- spotify_cover_url VARCHAR(500) NULL
-- spotify_cover_cached_at TIMESTAMP NULL
-- spotify_metadata_json JSON NULL
-- spotify_metadata_cached_at TIMESTAMP NULL
```

---

### 2. Verify Environment Variables

Ensure your `.env` file has Spotify credentials:

```bash
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
GOOGLE_SHEETS_XLSX_URL=https://docs.google.com/spreadsheets/.../export?format=xlsx
```

**Test Spotify Credentials**:
```bash
python manage.py shell
```
```python
from catalog.services.spotify_client import SpotifyClient
import os

client = SpotifyClient(
    os.getenv('SPOTIFY_CLIENT_ID'),
    os.getenv('SPOTIFY_CLIENT_SECRET')
)
print("✓ Spotify client initialized successfully")
```

---

## Basic Usage

### Importing Albums (Optimized)

The import command now skips Spotify API calls by default, storing only Google Sheets data and Spotify URLs:

```bash
# Import with optimized mode (default)
python manage.py import_albums

# Docker
make import
```

**What Happens**:
1. ✓ Fetches album data from Google Sheets
2. ✓ Stores album name, artist, release date, Spotify URL
3. ✗ **Skips** fetching cover art from Spotify
4. ✗ **Skips** fetching detailed metadata from Spotify

**Expected Output**:
```
Importing albums from Google Sheets...
Processed 500 albums in 5.2 minutes
Spotify API calls: 0 (skipped for on-demand loading)
Albums imported: 500
Albums updated: 0
```

**Performance Comparison**:
- **Before** (eager loading): ~15 minutes for 500 albums
- **After** (just-in-time): ~5 minutes for 500 albums
- **Improvement**: ~67% faster

---

### Browsing Albums with Lazy-Loaded Cover Art

Once albums are imported, visit the catalog to see cover art load progressively:

```bash
# Start development server
python manage.py runserver

# Docker
make up
```

Visit: `http://localhost:8000/catalog/albums/`

**User Experience**:
1. Page loads instantly with album tiles showing skeleton placeholders
2. As you scroll, cover art appears for albums entering your viewport
3. Cover art loads within ~1 second of becoming visible
4. Once loaded, cover art is cached for future visits

**Developer Tools Check**:
- Open browser DevTools → Network tab
- Scroll through catalog
- You'll see requests to `/catalog/album/{id}/cover-art/` as tiles enter viewport
- First visit: Many requests (cache miss)
- Second visit: Zero requests (cache hit)

---

### Viewing Album Details

Click any album tile to view detailed metadata:

Visit: `http://localhost:8000/catalog/album/{id}/`

**User Experience**:
1. Page loads with basic info (from database)
2. Detailed metadata (track listing, genres, popularity) loads immediately
3. Metadata fetched from Spotify API on first view, cached for subsequent views

**What Gets Fetched**:
- Track listing (all tracks with durations)
- Spotify genres
- Popularity score
- Record label information
- Copyright information

---

## Advanced Usage

### Manual Cache Refresh

Use the management command to manually refresh cached Spotify data:

#### Refresh All Albums

```bash
python manage.py refresh_spotify_cache
```

**Output**:
```
Refreshing Spotify cache for all albums...
Progress: [################] 500/500
Successfully refreshed: 495 albums
Failed: 5 albums (see error log)
Total time: 12 minutes
```

#### Refresh Specific Album

```bash
python manage.py refresh_spotify_cache --album-id 123
```

#### Refresh by Artist

```bash
python manage.py refresh_spotify_cache --artist "Tool"
```

**Output**:
```
Found 15 albums by Tool
Refreshing Spotify cache...
Progress: [################] 15/15
Successfully refreshed: 15 albums
Failed: 0 albums
Total time: 30 seconds
```

#### Refresh by Genre

```bash
python manage.py refresh_spotify_cache --genre "djent"
```

#### Dry Run (Preview Only)

```bash
python manage.py refresh_spotify_cache --dry-run
```

**Output**:
```
[DRY RUN] Would refresh 500 albums:
- Album Name 1 (Artist 1) - Cover: needs refresh, Metadata: cached
- Album Name 2 (Artist 2) - Cover: cached, Metadata: needs refresh
...
No changes made (dry run mode)
```

---

## Monitoring & Troubleshooting

### Check Cache Status

```bash
python manage.py shell
```

```python
from catalog.models import Album
from django.utils import timezone
from datetime import timedelta

# Albums with cached cover art
cached = Album.objects.filter(spotify_cover_url__isnull=False)
print(f"Albums with cached cover art: {cached.count()}")

# Albums needing cover art
uncached = Album.objects.filter(
    spotify_url__isnull=False,
    spotify_cover_url__isnull=True
)
print(f"Albums needing cover art: {uncached.count()}")

# Cache hit rate
total = Album.objects.filter(spotify_url__isnull=False).count()
hit_rate = (cached.count() / total * 100) if total > 0 else 0
print(f"Cache hit rate: {hit_rate:.1f}%")
```

---

### View Spotify API Logs

Check logs for API errors and rate limiting:

```bash
# View Django logs
tail -f logs/django.log

# Docker logs
docker logs -f progmetal_web

# Filter for Spotify errors
docker logs progmetal_web 2>&1 | grep "spotify"
```

**Common Log Messages**:
```
INFO: Fetching cover art for album_id=123 (cache miss)
INFO: Successfully cached cover art for album_id=123
WARNING: Spotify API rate limit reached, retrying in 5 seconds
ERROR: Failed to fetch cover art for album_id=456: Album not found on Spotify
```

---

### Common Issues & Solutions

#### Issue 1: Cover Art Not Loading

**Symptom**: Album tiles show placeholder images indefinitely

**Diagnosis**:
```bash
# Check if HTMX is working
curl -H "HX-Request: true" http://localhost:8000/catalog/album/123/cover-art/

# Check Spotify credentials
python manage.py shell -c "from catalog.services.spotify_client import SpotifyClient; SpotifyClient()"
```

**Solutions**:
1. Verify Spotify credentials in `.env`
2. Check browser console for JavaScript errors
3. Ensure album has valid `spotify_url` in database
4. Check Django logs for API errors

---

#### Issue 2: Rate Limit Errors

**Symptom**: Many albums showing "loading" placeholder, logs show 429 errors

**Diagnosis**:
```bash
grep "429" logs/django.log | wc -l
```

**Solutions**:
1. Reduce concurrent requests (edit `settings.py` → `SPOTIFY_MAX_CONCURRENT`)
2. Wait for rate limit window to reset (30 seconds)
3. Pre-warm cache during off-peak hours:
   ```bash
   python manage.py refresh_spotify_cache --batch-size 50
   ```

---

#### Issue 3: Stale Cover Art

**Symptom**: Album cover art doesn't match current Spotify data

**Solution**:
```bash
# Refresh specific album
python manage.py refresh_spotify_cache --album-id 123

# Refresh all albums with stale cache (older than 90 days)
python manage.py shell
```
```python
from catalog.models import Album
from django.utils import timezone
from datetime import timedelta

stale_threshold = timezone.now() - timedelta(days=90)
stale_albums = Album.objects.filter(
    spotify_cover_cached_at__lt=stale_threshold
)
print(f"Found {stale_albums.count()} albums with stale cache")

# Refresh them
for album in stale_albums:
    # Call refresh logic here
    pass
```

---

## Performance Metrics

### Measuring Import Speed

```bash
# Benchmark import time
time python manage.py import_albums
```

**Expected Results**:
- 500 albums: ~5-7 minutes
- 1000 albums: ~10-15 minutes
- **50%+ faster than eager loading**

---

### Measuring Cache Hit Rate

After browsing the catalog, check cache efficiency:

```bash
python manage.py shell
```
```python
from catalog.models import Album

total = Album.objects.filter(spotify_url__isnull=False).count()
cached = Album.objects.filter(spotify_cover_url__isnull=False).count()

print(f"Total albums with Spotify URL: {total}")
print(f"Albums with cached cover art: {cached}")
print(f"Cache hit rate: {(cached / total * 100):.1f}%")
```

**Target**: >80% cache hit rate after initial browsing

---

### Measuring API Usage Reduction

```bash
# Check Spotify API call logs
grep "Spotify API call" logs/django.log | wc -l
```

**Expected Results**:
- **Before**: ~500 API calls during import + 0 during browsing = 500 total
- **After**: 0 API calls during import + ~100 during browsing = 100 total
- **Reduction**: 80%

---

## Testing

### Manual Testing Checklist

1. **Import Albums**
   - [ ] Import completes successfully without Spotify API calls
   - [ ] Albums have `spotify_url` populated
   - [ ] Albums have `spotify_cover_url` = NULL

2. **Browse Catalog**
   - [ ] Album tiles show skeleton placeholders initially
   - [ ] Cover art loads as tiles enter viewport
   - [ ] Cover art appears within 1 second
   - [ ] Second page load shows cached cover art instantly

3. **View Album Details**
   - [ ] Detail page loads with basic info
   - [ ] Metadata loads immediately after page load
   - [ ] Track listing displays correctly
   - [ ] Genres and popularity show up

4. **Error Handling**
   - [ ] Albums without Spotify URL show appropriate placeholder
   - [ ] Rate limit errors show "loading" placeholder, not error
   - [ ] Invalid Spotify URLs handled gracefully

5. **Cache Refresh**
   - [ ] Refresh command updates cached data
   - [ ] Dry run mode doesn't modify database
   - [ ] Progress bar shows refresh status

---

### Automated Tests

```bash
# Run all tests
pytest

# Run just-in-time loading tests
pytest tests/integration/test_lazy_loading.py
pytest tests/contract/test_spotify_endpoints.py
pytest tests/unit/test_album_cache.py

# Docker
make test
```

**Expected Results**: All tests pass (100% pass rate)

---

## Configuration Reference

### Settings Variables

Add these to `config/settings.py`:

```python
# Spotify API Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_MAX_CONCURRENT = 10  # Max concurrent API requests
SPOTIFY_RETRY_ATTEMPTS = 3   # Max retry attempts on rate limit

# Cache Configuration
SPOTIFY_CACHE_ENABLED = True  # Enable/disable caching
SPOTIFY_CACHE_TIMEOUT = None  # Never expire (manual refresh only)
```

---

## Rollback Plan

If you need to revert to eager loading:

### 1. Revert Code Changes

```bash
git revert <commit-hash>
python manage.py migrate catalog 0005_syncoperation_current_tab
```

### 2. Re-import with Eager Loading

```bash
python manage.py import_albums --no-skip-spotify
```

This will populate all cache fields during import.

---

## Next Steps

1. **Monitor cache hit rate** for the first week after deployment
2. **Set up scheduled cache refresh** for popular albums (cron job)
3. **Optimize viewport detection** based on user behavior data
4. **Consider CDN** for serving cover art images at scale

---

## Support

- **Documentation**: `specs/006-jit-spotify-api/`
- **Issues**: Create GitHub issue with "jit-spotify-api" label
- **Logs**: Check `logs/django.log` for detailed error messages
- **Testing**: Run test suite before reporting bugs

---

## FAQ

### Q: Can I still pre-fetch cover art during import?

**A**: Yes, use the `--no-skip-spotify` flag:
```bash
python manage.py import_albums --no-skip-spotify
```
This will fetch cover art during import (slower but pre-warms cache).

---

### Q: How often should I refresh the cache?

**A**: It depends on your needs:
- **Monthly**: Good for most catalogs (album art rarely changes)
- **Weekly**: If you want the latest Spotify data (genres, popularity)
- **On-demand**: Only refresh when you notice outdated data

---

### Q: What happens if Spotify API is down?

**A**:
- Import continues successfully (doesn't depend on Spotify)
- Catalog shows placeholder images for uncached albums
- Cached albums continue to display normally
- Once Spotify recovers, new cover art will load automatically

---

### Q: Can I clear the cache?

**A**: Yes, use Django shell:
```python
from catalog.models import Album

# Clear cover art cache
Album.objects.update(
    spotify_cover_url=None,
    spotify_cover_cached_at=None
)

# Clear metadata cache
Album.objects.update(
    spotify_metadata_json=None,
    spotify_metadata_cached_at=None
)
```

---

### Q: How much database storage does caching use?

**A**: Minimal:
- Cover URL: ~200 bytes per album
- Metadata JSON: ~5KB per album
- 500 albums: ~2.6 MB total
- Negligible compared to album data itself

---

## Changelog

### Version 1.0 (2025-11-07)
- Initial release of just-in-time Spotify API loading
- Database schema updates (migration 0006)
- On-demand cover art loading via HTMX
- Manual cache refresh management command
- 80%+ reduction in Spotify API usage
