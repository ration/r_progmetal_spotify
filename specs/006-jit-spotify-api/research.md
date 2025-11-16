# Research: Just-in-Time Spotify API Usage

**Date**: 2025-11-07
**Feature**: Just-in-Time Spotify API Usage
**Branch**: 006-jit-spotify-api

## Overview

This document captures research findings and technical decisions for implementing just-in-time Spotify API loading to optimize API usage and import performance.

## Research Questions & Findings

### 1. Cover Art Lazy Loading Strategy

**Question**: What's the best approach for loading cover art progressively as users scroll through the album catalog?

**Decision**: Use Intersection Observer API with HTMX triggers

**Rationale**:
- **Intersection Observer API** is a modern browser API specifically designed for detecting when elements enter/exit the viewport
- **HTMX** already provides `hx-trigger="intersect"` which internally uses Intersection Observer
- This approach requires minimal JavaScript and integrates naturally with Django templates
- Performance is excellent - no scroll event listeners or manual viewport calculations needed
- Browser support is universal (Chrome 51+, Firefox 55+, Safari 12.1+)

**Alternatives Considered**:
1. **Scroll event listeners + manual viewport calculation**
   - Rejected: More complex, requires throttling/debouncing, higher CPU usage
2. **Load all images with native lazy loading (`loading="lazy"`)**
   - Rejected: Still requires fetching cover art URLs during import, doesn't solve the core API usage problem
3. **Client-side JavaScript viewport detection library (e.g., LazyLoad.js)**
   - Rejected: Adds dependency, duplicates functionality already available in HTMX + browser

**Implementation Approach**:
- Album tiles render with placeholder images initially
- Each tile has `hx-get="/catalog/album/{id}/cover-art/"` with `hx-trigger="intersect once"`
- When tile enters viewport, HTMX requests cover art URL from Django endpoint
- Django view fetches from Spotify API (or cache) and returns `<img>` tag with cover URL
- HTMX swaps placeholder with actual cover art

---

### 2. Cache Storage Strategy

**Question**: Where should we store cached cover art URLs and metadata to minimize database queries and ensure persistence?

**Decision**: Use Django database models with dedicated cache fields

**Rationale**:
- **Database-backed caching** ensures persistence across server restarts
- **Simple to query** - can check cache status with standard Django ORM queries
- **Transactional integrity** - cache updates are atomic with album records
- **No additional infrastructure** - uses existing PostgreSQL/SQLite setup
- **Easy to monitor** - can use Django admin to inspect cache status

**Data Model Additions**:
- Add `spotify_cover_url` (nullable) to `Album` model
- Add `spotify_cover_cached_at` (nullable datetime) to track cache freshness
- Add `spotify_metadata_json` (nullable JSON field) for detailed metadata
- Add `spotify_metadata_cached_at` (nullable datetime)

**Alternatives Considered**:
1. **Redis/Memcached external cache**
   - Rejected: Adds infrastructure dependency, requires separate cache invalidation logic, data lost on restart
2. **Django cache framework with database backend**
   - Rejected: More abstraction than needed, harder to query cache status, designed for temporary data
3. **File-based cache (store cover images locally)**
   - Rejected: Wastes storage, requires CDN setup for production, doesn't solve metadata caching

---

### 3. Spotify URL Parsing

**Question**: How should we extract album IDs from Spotify URLs to fetch cover art?

**Decision**: Use regex parsing with validation fallback

**Rationale**:
- Spotify album URLs follow consistent format: `https://open.spotify.com/album/{album_id}`
- Album IDs are always 22 characters (Base62 encoding)
- Regex is fast and reliable for this simple pattern
- Fallback to spotipy's built-in URL parsing if regex fails

**Implementation**:
```python
SPOTIFY_ALBUM_URL_PATTERN = re.compile(r'open\.spotify\.com/album/([a-zA-Z0-9]{22})')

def extract_album_id(spotify_url: str) -> Optional[str]:
    match = SPOTIFY_ALBUM_URL_PATTERN.search(spotify_url)
    if match:
        return match.group(1)
    # Fallback: try spotipy's album() which accepts URLs
    return None
```

**Alternatives Considered**:
1. **URL parsing libraries (urllib.parse)**
   - Rejected: Overkill for simple pattern, still requires manual ID extraction from path
2. **Always use spotipy's album() method with URL**
   - Rejected: Less explicit, makes an API call even if URL is invalid

---

### 4. Error Handling & Placeholder Images

**Question**: How should we handle Spotify API failures, rate limits, and missing data gracefully?

**Decision**: Multi-tier fallback strategy with distinct placeholder images

**Rationale**:
- Different failure modes require different user feedback
- Placeholder images provide visual continuity while indicating status
- Graceful degradation ensures catalog remains browsable even during API outages

**Fallback Hierarchy**:
1. **Cached cover art exists** → Return cached URL (fastest path)
2. **Spotify API call succeeds** → Return cover URL, cache it
3. **Spotify API rate limited** → Return "loading" placeholder, log error, retry later
4. **Spotify API error (404, 500)** → Return "unavailable" placeholder, log error
5. **No Spotify URL in database** → Return "no-spotify" placeholder

**Placeholder Image Strategy**:
- Use DaisyUI skeleton loading for "loading" state
- Use generic album icon for "unavailable" state
- Use different icon for "no-spotify" state (albums without Spotify URLs)

**Alternatives Considered**:
1. **Single generic placeholder for all failures**
   - Rejected: Doesn't communicate error type to users, harder to debug
2. **Retry API calls immediately on failure**
   - Rejected: Can make rate limiting worse, wastes API quota
3. **Show error messages instead of placeholders**
   - Rejected: Breaks visual grid layout, creates jarring user experience

---

### 5. Import Optimization

**Question**: How do we modify the existing import command to skip Spotify API calls while preserving all other functionality?

**Decision**: Add a `--skip-spotify` flag (default: True) and store only Spotify URLs during import

**Rationale**:
- Backward compatibility: Keep existing behavior available via flag
- Clear intent: Flag name explicitly indicates what's skipped
- Minimal changes: Wrap Spotify API calls in conditional checks
- Testing: Can test both modes (with/without Spotify)

**Implementation Changes**:
1. Parse `--skip-spotify` flag in `import_albums.py` command
2. Store `spotify_url` from Google Sheets without fetching metadata
3. Set `spotify_cover_url=None` and `spotify_metadata_json=None` during import
4. Log message indicating Spotify API calls were skipped
5. Update command help text to explain on-demand loading

**Alternatives Considered**:
1. **Remove Spotify API calls entirely from import**
   - Rejected: Removes flexibility to pre-populate cache if needed (e.g., for testing)
2. **Create separate import command (import_albums_fast)**
   - Rejected: Creates maintenance burden, duplicates logic
3. **Auto-detect Spotify API availability and skip if unavailable**
   - Rejected: Implicit behavior is harder to understand, can hide configuration issues

---

### 6. Cache Refresh Command

**Question**: How should administrators manually refresh cached Spotify data when needed?

**Decision**: Create `refresh_spotify_cache` management command with filtering options

**Rationale**:
- Follows Django convention for administrative tasks
- Provides granular control via command-line arguments
- Can be run manually or scheduled via cron/Celery
- Easy to test and document

**Command Interface**:
```bash
python manage.py refresh_spotify_cache             # Refresh all albums
python manage.py refresh_spotify_cache --album-id 123  # Refresh specific album
python manage.py refresh_spotify_cache --artist "Tool"  # Refresh albums by artist
python manage.py refresh_spotify_cache --genre "djent"  # Refresh albums in genre
```

**Features**:
- Progress bar showing refresh status
- Rate limit handling with exponential backoff
- Dry-run mode to preview what would be refreshed
- Logging of API failures for debugging

**Alternatives Considered**:
1. **Django admin action for cache refresh**
   - Rejected: Less flexible for bulk operations, harder to automate
2. **API endpoint for cache refresh**
   - Rejected: Requires authentication/authorization, can be triggered accidentally, less secure
3. **Automatic cache expiration (time-based)**
   - Rejected: Spec explicitly chose manual refresh strategy (Question 1 in specification)

---

### 7. Concurrency & Race Conditions

**Question**: How do we handle multiple users requesting cover art for the same album simultaneously?

**Decision**: Use database-level locking with select_for_update() for cache writes

**Rationale**:
- **select_for_update()** provides row-level locks in PostgreSQL
- Prevents duplicate API calls when multiple users view the same album
- Automatically released when transaction commits
- Works seamlessly with Django ORM

**Implementation**:
```python
from django.db import transaction

@transaction.atomic
def fetch_and_cache_cover_art(album_id: int) -> str:
    album = Album.objects.select_for_update().get(id=album_id)

    # Check cache again (might have been populated by another request)
    if album.spotify_cover_url:
        return album.spotify_cover_url

    # Fetch from Spotify API
    cover_url = spotify_client.get_album_cover(album.spotify_url)

    # Update cache
    album.spotify_cover_url = cover_url
    album.spotify_cover_cached_at = timezone.now()
    album.save()

    return cover_url
```

**Alternatives Considered**:
1. **No locking - accept duplicate API calls**
   - Rejected: Wastes API quota, can hit rate limits faster
2. **Application-level locking (threading.Lock)**
   - Rejected: Doesn't work across multiple processes/servers
3. **Redis distributed locks**
   - Rejected: Adds infrastructure dependency, overkill for this use case

---

### 8. Performance Testing Strategy

**Question**: How do we validate that the just-in-time approach actually improves performance as claimed?

**Decision**: Benchmark import time and API call counts before/after implementation

**Metrics to Track**:
1. **Import time**: Measure `import_albums` command execution time
2. **API call count**: Log total Spotify API calls during import
3. **Time to first cover art**: Measure page load to first cover visible
4. **Cache hit rate**: Track % of cover art requests served from cache

**Baseline (Current Eager Loading)**:
- Import 500 albums: ~15 minutes (with rate limiting)
- API calls during import: 500+ (one per album)
- All cover art visible immediately on page load

**Target (Just-in-Time Loading)**:
- Import 500 albums: <7 minutes (50%+ faster)
- API calls during import: 0
- Cover art loads progressively within 1 second of viewport visibility
- Cache hit rate: >80% after initial browsing

**Testing Approach**:
1. Create baseline measurements with current implementation
2. Implement just-in-time loading
3. Run same tests and compare metrics
4. Document in success criteria validation

**Alternatives Considered**:
1. **Load testing with concurrent users**
   - Deferred: Useful but not required for MVP validation
2. **Lighthouse/WebPageTest performance scores**
   - Deferred: Useful but page load time metrics sufficient for initial validation

---

## Technology Stack Summary

### Backend
- **Django 5.2.8**: Web framework
- **spotipy**: Spotify Web API client
- **psycopg**: PostgreSQL adapter
- **Python 3.14**: Language runtime

### Frontend
- **HTMX**: Progressive enhancement for lazy loading
- **Tailwind CSS v4**: Utility-first CSS framework
- **DaisyUI v5**: UI component library (placeholder states)

### Testing
- **pytest**: Test framework
- **pytest-django**: Django integration for pytest
- **Django test client**: Integration testing
- **factory_boy**: Test fixture generation (if needed)

### Infrastructure
- **PostgreSQL**: Production database
- **SQLite**: Development/test database
- **Docker**: Containerization (optional for development)

---

## Key Implementation Risks

### Risk 1: Spotify API Rate Limits During Initial Page Load

**Risk**: When users first browse the catalog, all visible albums will request cover art simultaneously, potentially hitting rate limits.

**Mitigation**:
- Implement request throttling on the backend (max 10 concurrent requests)
- Queue cover art requests and process them with controlled concurrency
- Use exponential backoff for rate limit errors
- Cache aggressively to reduce repeated requests

### Risk 2: Poor User Experience with Slow Cover Art Loading

**Risk**: Users may see a grid of placeholders for several seconds while cover art loads.

**Mitigation**:
- Use visually appealing skeleton loading placeholders
- Ensure placeholder → image transition is smooth (fade-in animation)
- Load cover art for above-the-fold albums eagerly (first 20 albums)
- Consider prefetching cover art for next page of results

### Risk 3: Database Performance with Many Cache Queries

**Risk**: Checking cache status for every album view could create database bottleneck.

**Mitigation**:
- Use `select_related()` to fetch albums with cover URLs in single query
- Add database indexes on `spotify_cover_cached_at` and `spotify_cover_url`
- Consider queryset caching for catalog list view
- Monitor query counts in development with Django Debug Toolbar

---

## Next Steps

1. **Phase 1**: Design data model changes and API contracts
2. Implement database migrations for cache fields
3. Modify import command to skip Spotify API calls
4. Implement cover art on-demand endpoint
5. Update album catalog template for lazy loading
6. Add cache refresh management command
7. Write tests for all new functionality
8. Benchmark performance against baseline metrics
