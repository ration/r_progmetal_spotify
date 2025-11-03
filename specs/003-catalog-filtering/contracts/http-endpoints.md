# HTTP Endpoint Contracts: Enhanced Catalog Filtering

**Feature**: 003-catalog-filtering
**Date**: 2025-11-03
**Purpose**: Define HTTP request/response contracts for catalog browsing with pagination, search, and filters

## Endpoint Overview

All functionality uses a single endpoint with different query parameters:

- **Endpoint**: `GET /catalog/albums/`
- **Content-Type**: `text/html` (server-rendered HTML)
- **HTMX**: Supports partial page updates via `HX-Request` header

## Endpoint: GET /catalog/albums/

### Purpose

Retrieve paginated, searchable, filterable list of albums in r/progmetal catalog.

### Request

**Method**: `GET`

**URL**: `/catalog/albums/`

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `q` | string | No | - | Min 3 chars | Search query (album, artist, genre, vocal style names) |
| `genre` | string[] | No | [] | Valid genre slugs | Selected genres (OR logic within category) |
| `vocal_style` | string[] | No | [] | Valid vocal style slugs | Selected vocal styles (OR logic within category) |
| `page` | integer | No | 1 | >= 1 | Page number (1-indexed) |
| `page_size` | integer | No | 50 | One of [25, 50, 100] | Items per page |

**Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `HX-Request` | No | Set to `true` by HTMX for partial updates |
| `HX-Current-URL` | No | Current page URL (set by HTMX) |

**Example Requests**:

```http
# Default view (first page, no filters)
GET /catalog/albums/ HTTP/1.1
Host: localhost:8000
Accept: text/html
```

```http
# Search for "periphery"
GET /catalog/albums/?q=periphery HTTP/1.1
Host: localhost:8000
Accept: text/html
```

```http
# Filter by genres (djent OR progressive-metal) AND vocal style (clean)
GET /catalog/albums/?genre=djent&genre=progressive-metal&vocal_style=clean HTTP/1.1
Host: localhost:8000
Accept: text/html
```

```http
# Pagination (page 2 with 100 items per page)
GET /catalog/albums/?page=2&page_size=100 HTTP/1.1
Host: localhost:8000
Accept: text/html
```

```http
# Combined: Search + Filters + Pagination (HTMX request)
GET /catalog/albums/?q=2025&genre=djent&page=2&page_size=50 HTTP/1.1
Host: localhost:8000
Accept: text/html
HX-Request: true
HX-Target: album-tiles
```

### Response (Full Page)

**Status Code**: `200 OK`

**Headers**:

```http
Content-Type: text/html; charset=utf-8
Vary: HX-Request
```

**Body**: Full HTML page with complete structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>Album Catalog - r/progmetal</title>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
    <link href="https://cdn.tailwindcss.com/4.0.0-alpha.1" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1>Album Catalog</h1>

        <!-- Search Box -->
        <div class="search-container">
            <input type="search" name="q" value="{{ request.GET.q }}"
                   placeholder="Search albums, artists, genres..."
                   hx-get="/catalog/albums/"
                   hx-trigger="keyup changed delay:500ms, search"
                   hx-target="#album-tiles"
                   hx-push-url="true"
                   hx-include="[name='genre'], [name='vocal_style'], [name='page_size']">
        </div>

        <!-- Filters -->
        <div class="filters-container">
            <div class="filter-group">
                <h3>Genre</h3>
                <label><input type="checkbox" name="genre" value="djent" {...}> Djent</label>
                <label><input type="checkbox" name="genre" value="progressive-metal" {...}> Progressive Metal</label>
                <!-- More genres -->
            </div>
            <div class="filter-group">
                <h3>Vocal Style</h3>
                <label><input type="checkbox" name="vocal_style" value="clean" {...}> Clean</label>
                <label><input type="checkbox" name="vocal_style" value="harsh" {...}> Harsh</label>
                <!-- More vocal styles -->
            </div>
        </div>

        <!-- Album Grid -->
        <div id="album-tiles">
            <!-- 50 album tiles -->
            <div class="album-tile">...</div>
            <div class="album-tile">...</div>
            <!-- ... -->
        </div>

        <!-- Pagination Controls -->
        <div class="pagination">
            <span>Page 1 of 4 (Showing 1-50 of 175 albums)</span>
            <a href="?page=2" hx-get="?page=2" hx-target="#album-tiles" hx-push-url="true">Next</a>
        </div>

        <!-- Page Size Selector -->
        <select id="page-size-selector" name="page_size"
                hx-get="/catalog/albums/"
                hx-target="#album-tiles"
                hx-push-url="true"
                hx-include="[name='q'], [name='genre'], [name='vocal_style']">
            <option value="25">25 per page</option>
            <option value="50" selected>50 per page</option>
            <option value="100">100 per page</option>
        </select>
    </div>
</body>
</html>
```

### Response (Partial - HTMX)

**Status Code**: `200 OK`

**Headers**:

```http
Content-Type: text/html; charset=utf-8
HX-Push-Url: /catalog/albums/?q=periphery&page=1
```

**Body**: HTML fragment containing only album tiles and pagination

```html
<!-- Album tiles only (no <html>, <head>, or outer containers) -->
<div class="album-tile">
    <img src="https://..." alt="Periphery - Periphery V">
    <h3>Periphery V: Djent Is Not A Genre</h3>
    <p>Periphery</p>
    <span class="genre">Djent</span>
    <span class="vocal">Mixed</span>
</div>
<div class="album-tile">
    <img src="https://..." alt="Periphery - Periphery IV">
    <h3>Periphery IV: Hail Stan</h3>
    <p>Periphery</p>
    <span class="genre">Progressive Metal</span>
    <span class="vocal">Mixed</span>
</div>
<!-- ... more tiles ... -->

<!-- Pagination controls (updated for current state) -->
<div class="pagination" id="pagination">
    <span>Page 1 of 1 (Showing 1-8 of 8 albums)</span>
</div>
```

### Response (Empty Results)

**Status Code**: `200 OK`

**Body** (partial or full page):

```html
<div id="album-tiles">
    <div class="empty-state">
        <p>No albums found matching "xyz"</p>
        <button hx-get="/catalog/albums/" hx-target="#album-tiles" hx-push-url="true">Clear search</button>
    </div>
</div>
```

### Response (Invalid Page)

**Scenario**: User requests page 999 when only 4 pages exist

**Status Code**: `302 Found` (redirect)

**Headers**:

```http
Location: /catalog/albums/?page=4
```

**Behavior**: Redirect to last valid page, preserving other query parameters

### Response (Invalid Page Size)

**Scenario**: User requests `?page_size=999`

**Status Code**: `200 OK`

**Behavior**: Ignore invalid page size, default to 50

**Body**: Standard response with 50 items per page

### Error Responses

**400 Bad Request**: Malformed query parameters (rare, Django handles most gracefully)

```http
HTTP/1.1 400 Bad Request
Content-Type: text/html

<h1>Bad Request</h1>
<p>Invalid query parameters</p>
```

**500 Internal Server Error**: Database connection failure or unhandled exception

```http
HTTP/1.1 500 Internal Server Error
Content-Type: text/html

<h1>Server Error</h1>
<p>Something went wrong. Please try again later.</p>
```

## Context Data Contract

Data passed to templates from Django view.

### Full Page Context

```python
{
    # Pagination
    'page_obj': Page,          # Django Page object
    'paginator': Paginator,    # Django Paginator object
    'is_paginated': bool,      # True if more than one page

    # Search state
    'search_query': str,       # Current search query or empty string
    'has_search': bool,        # True if search query present

    # Filter state
    'selected_genres': list[str],      # Genre slugs ['djent', 'progressive-metal']
    'selected_vocals': list[str],      # Vocal style slugs ['clean']
    'has_filters': bool,               # True if any filters active
    'filter_count': int,               # Total active filters

    # Available filter options
    'all_genres': QuerySet[Genre],     # All genres with album counts
    'all_vocals': QuerySet[VocalStyle], # All vocal styles with album counts

    # Page size
    'page_size': int,          # Current page size (25, 50, or 100)
    'page_size_options': list[int],  # [25, 50, 100]

    # Results
    'object_list': QuerySet[Album],  # Current page of albums (with select_related)
    'album_count': int,              # Total albums matching filters

    # HTMX
    'is_htmx': bool,           # True if HX-Request header present
}
```

### Partial Page Context (HTMX)

Same as full page, but view returns different template (`album_tiles_partial.html` instead of `album_list.html`)

## HTMX Behavior Contracts

### Search Input Debouncing

**Trigger**: User types in search box

**Behavior**:
1. Wait 500ms after last keystroke
2. If input length >= 3: Send `GET /catalog/albums/?q=<query>&...` with HX-Request header
3. If input length < 3: No request sent (client-side validation)
4. On response: Replace `#album-tiles` div with response HTML
5. Update browser URL via `HX-Push-Url` header

**Edge Case**: User clears search box (clicks X)
- Trigger: `search` event
- Behavior: Immediate request to `/catalog/albums/` (no query parameter)

### Checkbox Filter Changes

**Trigger**: User checks/unchecks genre or vocal style checkbox

**Behavior**:
1. Immediately send `GET /catalog/albums/?genre=X&genre=Y&vocal_style=Z&...`
2. Include current search query and page size via `hx-include` attribute
3. Reset page to 1 (filters change result count)
4. On response: Replace `#album-tiles` div
5. Update URL

### Pagination Link Clicks

**Trigger**: User clicks "Next", "Previous", or page number

**Behavior**:
1. Send `GET /catalog/albums/?page=N&...` preserving all other parameters
2. On response: Replace `#album-tiles` div
3. Scroll to top of album grid (via HTMX `hx-swap="innerHTML settle:scroll:top"`)

### Page Size Selection

**Trigger**: User selects different page size from dropdown

**Behavior**:
1. Save selected size to `sessionStorage.setItem('catalog_page_size', value)`
2. Send `GET /catalog/albums/?page_size=N&...` preserving other parameters
3. Reset page to 1 (page size change affects pagination)
4. On response: Replace `#album-tiles` div

## URL State Contract

**Invariant**: All catalog state must be encodable in URL for bookmarking

### URL Parameter Precedence

1. **Explicit URL parameter** > sessionStorage (e.g., `?page_size=100` overrides saved preference)
2. **Multiple values**: Use repeated parameters (`?genre=X&genre=Y`)
3. **Encoding**: Use standard URL encoding for special characters

### URL Parameter Preservation

When generating links (e.g., pagination), preserve all existing parameters except the one being changed.

**Example**: Current URL is `?q=periphery&genre=djent&page=1`

- Clicking "Next" generates: `?q=periphery&genre=djent&page=2`
- Checking "progressive-metal" genre generates: `?q=periphery&genre=djent&genre=progressive-metal&page=1`

**Implementation**: Custom template tag `{% url_replace request page=2 %}`

## Performance Contracts

### Response Time Targets

| Scenario | Target | Measurement |
|----------|--------|-------------|
| Initial page load (no filters) | < 2s | Server TTFB + rendering |
| Search update (HTMX) | < 500ms | From keystroke to DOM update |
| Filter change (HTMX) | < 500ms | From checkbox click to DOM update |
| Pagination (HTMX) | < 1s | From link click to DOM update |

### Database Query Constraints

- **Max queries per request**: 3 (base query + count + prefetch options)
- **Use of select_related()**: Required to avoid N+1 queries
- **Use of distinct()**: Required when searching across joins

### Caching Strategy

- **No server-side caching initially**: Django's QuerySet evaluation is fast enough
- **Future optimization**: Add Redis caching if response times exceed targets

## Security Contracts

### Input Validation

- **SQL Injection**: Protected by Django ORM (parameterized queries)
- **XSS**: Protected by Django template auto-escaping
- **CSRF**: Not applicable (GET requests don't modify state)

### Parameter Validation

- `page`: Validated by Django Paginator (invalid values handled gracefully)
- `page_size`: Validated against allowed values [25, 50, 100], defaults to 50
- `q`: No validation needed (search term can be any string)
- `genre`, `vocal_style`: Validated against existing slugs in database

### Rate Limiting

**Not implemented initially** (public read-only catalog, low abuse risk)

**Future consideration**: Implement rate limiting if abuse detected:
- 100 requests per minute per IP
- Use `django-ratelimit` library

## Accessibility Contracts

### Keyboard Navigation

- Search box focusable via Tab key
- Checkboxes focusable and toggleable via Space
- Pagination links focusable via Tab, activatable via Enter

### Screen Reader Support

- Search box labeled with `aria-label="Search albums"`
- Checkboxes grouped with `<fieldset>` and `<legend>`
- Pagination announced as "Page X of Y"
- HTMX updates announced via `aria-live="polite"` region

### Progressive Enhancement

- All functionality works without JavaScript (falls back to full page reloads)
- HTMX attributes degrade gracefully (standard `href` links still work)

---

**Contracts Complete**: HTTP endpoints, HTMX behavior, URL state, performance, security, and accessibility requirements defined
