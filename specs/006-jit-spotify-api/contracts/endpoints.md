# API Contracts: Just-in-Time Spotify API Endpoints

**Date**: 2025-11-07
**Feature**: Just-in-Time Spotify API Usage
**Branch**: 006-jit-spotify-api

## Overview

This document defines the HTTP API contracts for on-demand Spotify cover art and metadata loading. All endpoints follow REST conventions and return HTML fragments for HTMX integration or JSON for programmatic access.

---

## Endpoints

### 1. Get Album Cover Art (Lazy Load)

**Purpose**: Fetch album cover art on-demand when album tile enters viewport.

**Endpoint**: `GET /catalog/album/<int:album_id>/cover-art/`

**Request**:

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `album_id` | Integer | URL path | Yes | Album primary key |
| `format` | String | Query | No | Response format: "html" (default) or "json" |

**Request Headers**:
```
HX-Request: true              # Indicates HTMX request
HX-Target: album-cover-{id}   # Target element for swap
HX-Trigger: album-tile-{id}   # Element that triggered request
```

**Response (HTML format)**:

Status: `200 OK`

Headers:
```
Content-Type: text/html; charset=utf-8
HX-Trigger: cover-art-loaded  # Notify other components
```

Body (cached):
```html
<img
    src="https://i.scdn.co/image/ab67616d0000b273..."
    alt="Album Name by Artist Name"
    class="w-full h-auto rounded-lg shadow-md"
    loading="eager"
/>
```

Body (fetched from API):
```html
<img
    src="https://i.scdn.co/image/ab67616d0000b273..."
    alt="Album Name by Artist Name"
    class="w-full h-auto rounded-lg shadow-md fade-in"
    loading="eager"
/>
```

Body (placeholder - API error):
```html
<div class="w-full aspect-square bg-base-200 rounded-lg flex items-center justify-center">
    <svg class="w-16 h-16 text-base-content opacity-30" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
</div>
```

**Response (JSON format)**:

Status: `200 OK`

Headers:
```
Content-Type: application/json
```

Body (success):
```json
{
    "album_id": 123,
    "cover_url": "https://i.scdn.co/image/ab67616d0000b273...",
    "cached": true,
    "cached_at": "2025-11-07T14:30:00Z"
}
```

Body (error):
```json
{
    "album_id": 123,
    "cover_url": null,
    "error": "Spotify API rate limit exceeded",
    "cached": false
}
```

**Error Responses**:

| Status Code | Reason | Response Body |
|-------------|--------|---------------|
| 404 Not Found | Album doesn't exist | `<div class="alert alert-error">Album not found</div>` |
| 429 Too Many Requests | Rate limit exceeded | `<div class="alert alert-warning">Loading...</div>` (retry after delay) |
| 500 Internal Server Error | Unexpected error | `<div class="alert alert-error">Failed to load cover art</div>` |

---

### 2. Get Album Metadata (Detail Page)

**Purpose**: Fetch detailed Spotify metadata when user views album detail page.

**Endpoint**: `GET /catalog/album/<int:album_id>/metadata/`

**Request**:

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `album_id` | Integer | URL path | Yes | Album primary key |
| `format` | String | Query | No | Response format: "html" (default) or "json" |

**Request Headers**:
```
HX-Request: true                    # Indicates HTMX request
HX-Target: album-metadata-{id}      # Target element for swap
HX-Trigger: album-detail-page       # Element that triggered request
```

**Response (HTML format)**:

Status: `200 OK`

Headers:
```
Content-Type: text/html; charset=utf-8
```

Body:
```html
<div class="metadata-container space-y-4">
    <div class="stat">
        <div class="stat-title">Popularity</div>
        <div class="stat-value text-primary">85/100</div>
    </div>

    <div class="tracks">
        <h3 class="text-lg font-bold mb-2">Track Listing</h3>
        <ol class="list-decimal list-inside space-y-1">
            <li>Track Name 1 <span class="text-sm text-base-content/70">(5:45)</span></li>
            <li>Track Name 2 <span class="text-sm text-base-content/70">(6:20)</span></li>
            <!-- ... more tracks ... -->
        </ol>
    </div>

    <div class="genres">
        <h3 class="text-lg font-bold mb-2">Spotify Genres</h3>
        <div class="flex flex-wrap gap-2">
            <span class="badge badge-primary">progressive metal</span>
            <span class="badge badge-primary">djent</span>
        </div>
    </div>

    <div class="label">
        <p class="text-sm text-base-content/70">Label: Record Label Name</p>
    </div>
</div>
```

**Response (JSON format)**:

Status: `200 OK`

Headers:
```
Content-Type: application/json
```

Body:
```json
{
    "album_id": 123,
    "metadata": {
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
        "external_urls": {
            "spotify": "https://open.spotify.com/album/abc123..."
        }
    },
    "cached": true,
    "cached_at": "2025-11-07T14:30:00Z"
}
```

**Error Responses**:

| Status Code | Reason | Response Body |
|-------------|--------|---------------|
| 404 Not Found | Album doesn't exist | `<div class="alert alert-error">Album not found</div>` |
| 503 Service Unavailable | Spotify API unavailable | `<div class="alert alert-warning">Metadata temporarily unavailable</div>` |
| 500 Internal Server Error | Unexpected error | `<div class="alert alert-error">Failed to load metadata</div>` |

---

### 3. Refresh Album Cache (Admin)

**Purpose**: Manually refresh cached Spotify data for specific albums.

**Endpoint**: `POST /catalog/admin/refresh-cache/`

**Authentication**: Requires Django admin or staff user authentication.

**Request**:

Headers:
```
Content-Type: application/json
X-CSRFToken: {csrf_token}
Authorization: Session {session_id}
```

Body:
```json
{
    "album_ids": [123, 456, 789],
    "refresh_cover": true,
    "refresh_metadata": true,
    "dry_run": false
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `album_ids` | Array[Integer] | No | Specific album IDs to refresh (empty = all albums) |
| `refresh_cover` | Boolean | No | Refresh cover art (default: true) |
| `refresh_metadata` | Boolean | No | Refresh metadata (default: true) |
| `dry_run` | Boolean | No | Preview without making changes (default: false) |

**Response**:

Status: `200 OK`

Body:
```json
{
    "status": "success",
    "refreshed_count": 3,
    "failed_count": 0,
    "results": [
        {
            "album_id": 123,
            "album_name": "Album Name",
            "cover_refreshed": true,
            "metadata_refreshed": true,
            "error": null
        },
        {
            "album_id": 456,
            "album_name": "Another Album",
            "cover_refreshed": true,
            "metadata_refreshed": false,
            "error": "Spotify API rate limit exceeded"
        }
    ],
    "dry_run": false
}
```

**Error Responses**:

| Status Code | Reason | Response Body |
|-------------|--------|---------------|
| 401 Unauthorized | Not authenticated | `{"error": "Authentication required"}` |
| 403 Forbidden | Not staff user | `{"error": "Admin access required"}` |
| 400 Bad Request | Invalid input | `{"error": "Invalid album_ids format"}` |
| 500 Internal Server Error | Unexpected error | `{"error": "Cache refresh failed"}` |

---

## HTMX Integration Patterns

### Lazy Load Cover Art Pattern

**Template (album_tile.html)**:
```html
<div class="album-tile card bg-base-100 shadow-xl">
    <figure
        id="album-cover-{{ album.id }}"
        hx-get="/catalog/album/{{ album.id }}/cover-art/"
        hx-trigger="intersect once"
        hx-swap="innerHTML"
    >
        <!-- Skeleton loading placeholder -->
        <div class="w-full aspect-square bg-base-200 animate-pulse"></div>
    </figure>

    <div class="card-body">
        <h2 class="card-title">{{ album.name }}</h2>
        <p>{{ album.artist.name }}</p>
    </div>
</div>
```

**Behavior**:
1. Album tile renders with skeleton placeholder
2. When tile enters viewport, HTMX triggers GET request
3. Server checks cache, fetches from Spotify if needed
4. Server returns `<img>` tag with cover URL
5. HTMX replaces placeholder with actual image

---

### Load Metadata on Detail Page Pattern

**Template (album_detail.html)**:
```html
<div class="album-detail-page">
    <div class="album-header">
        <img src="{{ album.spotify_cover_url|default:'/static/placeholder.jpg' }}"
             alt="{{ album.name }}" />
        <h1>{{ album.name }}</h1>
        <p>{{ album.artist.name }}</p>
    </div>

    <div
        id="album-metadata-{{ album.id }}"
        hx-get="/catalog/album/{{ album.id }}/metadata/"
        hx-trigger="load"
        hx-swap="innerHTML"
    >
        <!-- Loading spinner -->
        <div class="loading loading-spinner loading-lg"></div>
    </div>
</div>
```

**Behavior**:
1. Detail page loads with basic info (from database)
2. HTMX immediately triggers metadata request on page load
3. Server checks cache, fetches from Spotify if needed
4. Server returns HTML with track listing, genres, etc.
5. HTMX replaces loading spinner with metadata

---

## Caching Behavior

### Cache Hit Flow

```
Client Request → Django View
                      ↓
                Check Album.spotify_cover_url
                      ↓
                [URL exists?]
                      ↓ Yes
                Return cached URL
                      ↓
                Response (cache hit)
```

**Performance**: <10ms (database query only)

---

### Cache Miss Flow

```
Client Request → Django View
                      ↓
                Check Album.spotify_cover_url
                      ↓
                [URL exists?]
                      ↓ No
                Acquire database lock (select_for_update)
                      ↓
                Fetch from Spotify API
                      ↓
                [API success?]
                      ↓ Yes
                Update Album.spotify_cover_url
                      ↓
                Release lock
                      ↓
                Response (cache miss, now cached)
```

**Performance**: ~500ms (includes Spotify API call)

---

### Cache Refresh Flow

```
Admin Request → Django View
                      ↓
                Verify authentication
                      ↓
                Iterate over album_ids
                      ↓
                For each album:
                    ↓
                    Fetch from Spotify API
                    ↓
                    Update cache fields
                    ↓
                    Handle rate limits (backoff)
                      ↓
                Return refresh summary
```

**Performance**: ~1-2 seconds per album (rate limited)

---

## Rate Limiting Strategy

### Spotify API Rate Limits

- **Limit**: ~180 requests per 30 seconds per client
- **Strategy**: Exponential backoff on 429 responses
- **Concurrency**: Max 10 concurrent requests to Spotify

### Implementation

```python
import time
from functools import wraps

def rate_limited_spotify_call(max_retries=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except SpotifyException as e:
                    if e.http_status == 429:
                        retry_after = int(e.headers.get('Retry-After', 1))
                        time.sleep(retry_after * (2 ** attempt))
                    else:
                        raise
            raise Exception("Max retries exceeded")
        return wrapper
    return decorator
```

---

## Security Considerations

### Authentication

- Cover art endpoint: **Public** (no authentication required)
- Metadata endpoint: **Public** (no authentication required)
- Cache refresh endpoint: **Staff only** (Django admin authentication)

### CSRF Protection

- GET requests: No CSRF token required
- POST requests (cache refresh): CSRF token required

### Input Validation

- `album_id`: Must be positive integer
- `format`: Must be "html" or "json"
- `album_ids`: Must be array of positive integers

### Output Encoding

- HTML responses: Django template auto-escaping enabled
- JSON responses: Django JsonResponse handles serialization safely

---

## Testing Contracts

### Contract Test Examples

**Test: Cover art returns valid HTML**
```python
def test_cover_art_returns_valid_html():
    response = client.get(f'/catalog/album/{album_id}/cover-art/')
    assert response.status_code == 200
    assert '<img' in response.content.decode()
    assert 'src=' in response.content.decode()
```

**Test: Cover art JSON response has required fields**
```python
def test_cover_art_json_has_required_fields():
    response = client.get(f'/catalog/album/{album_id}/cover-art/?format=json')
    data = response.json()
    assert 'album_id' in data
    assert 'cover_url' in data
    assert 'cached' in data
```

**Test: Metadata endpoint handles missing Spotify URL**
```python
def test_metadata_handles_missing_spotify_url():
    album.spotify_url = None
    album.save()
    response = client.get(f'/catalog/album/{album.id}/metadata/')
    assert response.status_code == 200
    assert 'unavailable' in response.content.decode().lower()
```

**Test: Cache refresh requires authentication**
```python
def test_cache_refresh_requires_auth():
    response = client.post('/catalog/admin/refresh-cache/', {})
    assert response.status_code == 401
```

---

## Performance Benchmarks

### Expected Response Times

| Endpoint | Cache Hit | Cache Miss | Notes |
|----------|-----------|------------|-------|
| Cover Art (HTML) | <50ms | ~500ms | Cache miss includes Spotify API call |
| Cover Art (JSON) | <30ms | ~500ms | JSON is faster to serialize |
| Metadata (HTML) | <100ms | ~1000ms | More data to fetch/render |
| Metadata (JSON) | <50ms | ~1000ms | Full track listing included |
| Cache Refresh | N/A | ~1-2s/album | Rate limited by Spotify |

### Optimization Targets

- **P95 response time** for cached requests: <100ms
- **Concurrent requests**: Support 50+ simultaneous cover art requests
- **Cache hit rate**: >80% after initial browsing session
