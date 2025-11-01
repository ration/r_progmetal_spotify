# HTMX Endpoints: Album Catalog

**Feature**: Album Catalog Visualization
**Date**: 2025-11-01
**Purpose**: Define HTTP endpoints for HTMX interactions

## Overview

This document specifies the HTTP endpoints used by HTMX for partial page updates. All endpoints return HTML (full pages or fragments) rather than JSON. The server detects HTMX requests via the `HX-Request: true` header and returns appropriate responses.

---

## Endpoint: Album List

### GET /catalog/albums/

**Purpose**: Display album catalog with optional filters

**Request Types**:
1. **Full Page Load** (no `HX-Request` header)
   - Initial visit to catalog
   - Returns complete HTML page with layout, filters, and album tiles

2. **HTMX Fragment** (`HX-Request: true` header)
   - Filter change via HTMX
   - Returns only the album tiles HTML (for swap into `#album-tiles` container)

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| genre | String | No | Genre slug for filtering | `?genre=progressive-metal` |
| vocal | String | No | Vocal style slug for filtering | `?vocal=instrumental` |
| page | Integer | No | Page number for pagination (future) | `?page=2` |

**Example Requests**:

```http
GET /catalog/albums/ HTTP/1.1
Host: localhost:8000

# Response: Full HTML page (base.html + catalog layout + tiles)
```

```http
GET /catalog/albums/?genre=djent HTTP/1.1
Host: localhost:8000
HX-Request: true
HX-Target: #album-tiles
HX-Current-URL: /catalog/albums/

# Response: HTML fragment (just the tiles)
```

**Response (Full Page)**:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Album Catalog</title>
    <!-- Tailwind CSS, HTMX scripts -->
</head>
<body>
    <main class="container mx-auto p-4">
        <h1>Progressive Metal Releases</h1>

        <!-- Filters -->
        <div class="filters flex gap-4 mb-6">
            <select
                hx-get="/catalog/albums/"
                hx-target="#album-tiles"
                hx-push-url="true"
                name="genre"
                class="select select-bordered"
            >
                <option value="">All Genres</option>
                <option value="progressive-metal">Progressive Metal</option>
                <option value="djent">Djent</option>
                <!-- ... -->
            </select>

            <select
                hx-get="/catalog/albums/"
                hx-target="#album-tiles"
                hx-push-url="true"
                name="vocal"
                class="select select-bordered"
            >
                <option value="">All Vocal Styles</option>
                <option value="clean-vocals">Clean Vocals</option>
                <option value="harsh-vocals">Harsh Vocals</option>
                <!-- ... -->
            </select>
        </div>

        <!-- Album Tiles Container -->
        <div id="album-tiles" class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
            <!-- Album tiles rendered here -->
            {% include 'catalog/album_list_tiles.html' %}
        </div>
    </main>
</body>
</html>
```

**Response (HTMX Fragment)**:

```html
<!-- Only the tiles, no layout -->
<div class="card bg-base-100 shadow-xl cursor-pointer"
     hx-get="/catalog/albums/1/" hx-target="body" hx-push-url="true">
    <figure>
        <img src="https://i.scdn.co/image/..." alt="Fauna by Haken" class="w-full aspect-square object-cover">
    </figure>
    <div class="card-body">
        <h2 class="card-title text-lg">Fauna</h2>
        <p class="text-sm text-gray-600">Haken</p>
        <div class="flex justify-between text-xs text-gray-500">
            <span>Progressive Metal</span>
            <span>2023</span>
        </div>
    </div>
</div>
<!-- More tiles... -->
```

**Status Codes**:
- `200 OK`: Success (tiles rendered)
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Database or template error

**Headers**:
- `HX-Push-Url: /catalog/albums/?genre=djent` (update browser URL)
- `Vary: HX-Request` (cache control for HTMX vs full page)

**View Implementation Notes**:
- Check `request.headers.get('HX-Request')` to determine response type
- If HTMX: Return `catalog/album_list_tiles.html` template
- If full page: Return `catalog/album_list.html` template (which includes tiles)
- Use `Album.objects.select_related('artist', 'genre', 'vocal_style')` for efficiency
- Apply filters via `Q` objects if query params present
- Order by `release_date DESC, imported_at DESC`

---

## Endpoint: Album Detail

### GET /catalog/albums/<id>/

**Purpose**: Display detailed view of a single album

**Request Types**:
1. **Full Page Load** (no `HX-Request` header)
   - Direct link navigation
   - Returns complete HTML page with album details

2. **HTMX Navigation** (`HX-Request: true` header)
   - Click on album tile
   - Returns full page HTML (swaps entire `<body>`)

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | Integer | Yes | Album database primary key |

**Example Request**:

```http
GET /catalog/albums/1/ HTTP/1.1
Host: localhost:8000
HX-Request: true
HX-Target: body
HX-Current-URL: /catalog/albums/
```

**Response**:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Fauna by Haken - Album Details</title>
</head>
<body>
    <main class="container mx-auto p-4">
        <!-- Back button -->
        <a href="/catalog/albums/" class="btn btn-ghost mb-4">
            ← Back to Catalog
        </a>

        <div class="flex flex-col md:flex-row gap-8">
            <!-- Album Cover -->
            <div class="w-full md:w-1/3">
                <img src="https://i.scdn.co/image/..." alt="Fauna" class="w-full rounded-lg shadow-lg">
            </div>

            <!-- Album Details -->
            <div class="w-full md:w-2/3">
                <h1 class="text-4xl font-bold mb-2">Fauna</h1>
                <p class="text-2xl text-gray-600 mb-4">Haken</p>

                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div>
                        <span class="text-sm text-gray-500">Release Date</span>
                        <p class="text-lg">February 3, 2023</p>
                    </div>
                    <div>
                        <span class="text-sm text-gray-500">Genre</span>
                        <p class="text-lg">Progressive Metal</p>
                    </div>
                    <div>
                        <span class="text-sm text-gray-500">Country</span>
                        <p class="text-lg">United Kingdom</p>
                    </div>
                    <div>
                        <span class="text-sm text-gray-500">Vocal Style</span>
                        <p class="text-lg">Clean Vocals</p>
                    </div>
                </div>

                <!-- External Link -->
                <a href="https://open.spotify.com/album/..." target="_blank"
                   class="btn btn-primary">
                    Open in Spotify →
                </a>
            </div>
        </div>
    </main>
</body>
</html>
```

**Status Codes**:
- `200 OK`: Album found and rendered
- `404 Not Found`: Album ID does not exist
- `500 Internal Server Error`: Database or template error

**Headers**:
- `HX-Push-Url: /catalog/albums/1/` (update browser URL)

**View Implementation Notes**:
- Use `get_object_or_404(Album, id=id)`
- `select_related('artist', 'genre', 'vocal_style')` for efficiency
- Handle missing fields gracefully (e.g., "Country: Unknown" if null)
- Use `album.get_cover_art_or_placeholder()` for image src

---

## Endpoint: Filter Clear

### GET /catalog/albums/ (no query params)

**Purpose**: Clear all filters and return to unfiltered catalog

**Trigger**: User clicks "Clear Filters" button or removes filter selection

**Example Request**:

```http
GET /catalog/albums/ HTTP/1.1
Host: localhost:8000
HX-Request: true
HX-Target: #album-tiles
```

**Response**: Same as filtered request, but returns all albums (no filter applied)

**HTMX Attribute**:
```html
<button hx-get="/catalog/albums/" hx-target="#album-tiles" hx-push-url="true">
    Clear Filters
</button>
```

---

## HTMX Configuration

### Global HTMX Attributes

**In base.html**:
```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script>
    // Configure HTMX timeout (default 0 = no timeout)
    htmx.config.timeout = 5000; // 5 second timeout for requests

    // Enable history navigation
    htmx.config.historyCacheSize = 10;

    // Show loading indicator
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        document.body.style.cursor = 'wait';
    });
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        document.body.style.cursor = 'default';
    });
</script>
```

### HTMX Headers (Django Middleware)

**Django View Helper** (check if HTMX request):
```python
def is_htmx_request(request):
    return request.headers.get('HX-Request') == 'true'
```

**Response Headers**:
- `HX-Push-Url`: Update browser URL (for bookmarkability)
- `HX-Trigger`: Trigger client-side events (future: notifications)
- `Vary: HX-Request`: Ensure CDN/proxy cache separation

---

## Error Handling

### 404 Not Found

**Trigger**: Album ID doesn't exist

**Response (HTMX)**:
```html
<div class="alert alert-error">
    <span>Album not found. It may have been removed.</span>
    <a href="/catalog/albums/" class="btn btn-sm">Back to Catalog</a>
</div>
```

**Status Code**: `404 Not Found`

### 500 Internal Server Error

**Trigger**: Database connection failure, template error

**Response (HTMX)**:
```html
<div class="alert alert-error">
    <span>Something went wrong. Please try again later.</span>
    <button hx-get="/catalog/albums/" hx-target="#album-tiles">
        Retry
    </button>
</div>
```

**Status Code**: `500 Internal Server Error`

**Logging**: All 500 errors logged with traceback (Observability principle)

---

## Testing Contracts

### Integration Test Example

**Test HTMX Fragment Response**:
```python
def test_album_list_htmx_fragment(client, test_album):
    response = client.get('/catalog/albums/', HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'album-tiles' not in response.content.decode()  # No full page layout
    assert test_album.name in response.content.decode()
    assert 'HX-Push-Url' in response.headers
```

**Test Full Page Response**:
```python
def test_album_list_full_page(client, test_album):
    response = client.get('/catalog/albums/')

    assert response.status_code == 200
    assert '<html>' in response.content.decode()
    assert test_album.name in response.content.decode()
```

**Test Filter Application**:
```python
def test_album_list_filter_by_genre(client, prog_metal_album, djent_album):
    response = client.get('/catalog/albums/?genre=djent', HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert djent_album.name in response.content.decode()
    assert prog_metal_album.name not in response.content.decode()
```

---

## Performance Considerations

### Response Times

**Target**: < 1 second for filter responses (Success Criterion SC-004)

**Optimizations**:
- Database indexes on filter fields (genre_id, vocal_style_id)
- `select_related()` to avoid N+1 queries
- Template fragment caching (future optimization)
- CDN for static assets (CSS, JS, placeholder image)

### Caching Strategy

**Browser Caching**:
- Static assets: 1 year (`Cache-Control: max-age=31536000`)
- HTML pages: No cache (`Cache-Control: no-cache, must-revalidate`)

**Template Fragment Caching** (future):
```python
{% load cache %}
{% cache 300 album_tiles genre vocal %}
    <!-- Tiles rendered here -->
{% endcache %}
```

---

## Summary

**Total Endpoints**: 2
- GET /catalog/albums/ (list + filter)
- GET /catalog/albums/<id>/ (detail)

**HTMX Features Used**:
- `hx-get`: Trigger GET requests
- `hx-target`: Specify swap target
- `hx-push-url`: Update browser URL
- `hx-swap`: Replace innerHTML (default)

**Response Types**:
- Full page HTML (initial load, direct navigation)
- HTML fragments (HTMX filter updates)

**Headers**:
- Request: `HX-Request: true` (indicates HTMX call)
- Response: `HX-Push-Url` (browser URL update), `Vary: HX-Request` (caching)

All endpoints follow REST conventions and return semantic HTML for progressive enhancement.
