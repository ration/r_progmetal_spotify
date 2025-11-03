# Research: Enhanced Catalog Filtering and Pagination

**Feature**: 003-catalog-filtering
**Date**: 2025-11-03
**Purpose**: Research technical implementation approaches for pagination, search, and filtering in Django with HTMX

## Research Questions

Based on Technical Context, research the following areas:

1. **Django Pagination**: Best practices for Django Paginator with URL parameters
2. **Search Implementation**: Django Q objects for multi-field search with performance optimization
3. **Filter Logic**: Implementing OR within categories, AND between categories using Q objects
4. **HTMX Integration**: Partial page updates for search/filter changes
5. **URL State Management**: Persisting search/filter/pagination state in URL parameters
6. **Session Storage**: Browser-side page size preference persistence
7. **Search Debouncing**: Client-side JavaScript debouncing patterns with HTMX

---

## 1. Django Pagination with URL Parameters

### Decision
Use Django's built-in `Paginator` class with `Page` object, accessed via `?page=N` URL parameter. Integrate with existing `AlbumListView` (ListView-based).

### Rationale
- **Built-in Django support**: `Paginator` is battle-tested, handles edge cases (invalid pages, empty sets)
- **ListView integration**: Django's `ListView` has `paginate_by` attribute for automatic pagination
- **URL-based state**: `?page=N` parameters naturally support browser back/forward and bookmarking
- **Performance**: `Paginator` uses efficient `LIMIT/OFFSET` queries, counts are cached per request

### Implementation Approach
```python
# In AlbumListView
class AlbumListView(ListView):
    model = Album
    paginate_by = 50  # Default page size
    template_name = 'catalog/album_list.html'

    def get_paginate_by(self, queryset):
        """Allow dynamic page size from URL parameter."""
        return self.request.GET.get('page_size', 50)

    def get_queryset(self):
        """Apply search and filters to base queryset."""
        qs = super().get_queryset()
        # Search and filter logic added here
        return qs
```

### Alternatives Considered
- **Custom pagination**: More control but reinventing wheel, Django's Paginator handles edge cases
- **Cursor pagination**: Better performance for large datasets, but requires stable sort order (we need page numbers for UX)
- **Infinite scroll**: Eliminated per spec (out of scope)

### References
- Django Paginator docs: https://docs.djangoproject.com/en/5.2/topics/pagination/
- ListView pagination: https://docs.djangoproject.com/en/5.2/ref/class-based-views/generic-display/#listview

---

## 2. Multi-Field Search with Django Q Objects

### Decision
Use Django `Q` objects with `|` (OR) operator to search across album name, artist name, genre name, and vocal style name. Apply case-insensitive partial matching via `__icontains` lookups.

### Rationale
- **Q objects provide flexible queries**: Can combine multiple fields with OR logic
- **`__icontains` is standard**: Case-insensitive substring matching (uses `LOWER()` and `LIKE` in SQL)
- **Performance is acceptable**: With proper indexing on searched fields, `ILIKE` performs well for catalogs <10k albums
- **Simplicity**: No external dependencies (Elasticsearch, Whoosh) needed for this scale

### Implementation Approach
```python
from django.db.models import Q

def get_queryset(self):
    qs = super().get_queryset()
    search_query = self.request.GET.get('q', '').strip()

    if search_query and len(search_query) >= 3:
        qs = qs.filter(
            Q(name__icontains=search_query) |           # Album name
            Q(artist__name__icontains=search_query) |   # Artist name
            Q(genre__name__icontains=search_query) |    # Genre name
            Q(vocal_style__name__icontains=search_query) # Vocal style
        ).distinct()  # distinct() prevents duplicate results from joins

    return qs
```

### Performance Considerations
- **Indexes**: Ensure indexes exist on `album.name`, `artist.name`, `genre.name`, `vocal_style.name`
- **DISTINCT**: Required when joining across relationships to avoid duplicate albums
- **N+1 queries**: Use `select_related('artist', 'genre', 'vocal_style')` to fetch related objects in single query

### Alternatives Considered
- **Full-text search (PostgreSQL)**: Overkill for substring matching, requires GIN indexes and migration
- **Elasticsearch**: External dependency, operational complexity, unnecessary for <10k albums
- **Trigram similarity (pg_trgm)**: Better fuzzy matching but spec explicitly chose simple partial matching

### References
- Django Q objects: https://docs.djangoproject.com/en/5.2/topics/db/queries/#complex-lookups-with-q-objects
- QuerySet distinct(): https://docs.djangoproject.com/en/5.2/ref/models/querysets/#distinct

---

## 3. Filter Logic: OR Within Categories, AND Between Categories

### Decision
Use Django Q objects to implement OR logic within each filter category (genre, vocal style), then AND the category results together.

### Rationale
- **Q objects support complex logic**: Can build dynamic queries based on selected filters
- **AND between categories is intersection**: Filters from different categories narrow results (genre AND vocal_style)
- **OR within category is union**: Multiple genres/vocal styles within same category broaden results
- **Efficient SQL generation**: Django ORM translates to optimal `WHERE` clauses

### Implementation Approach
```python
def get_queryset(self):
    qs = super().get_queryset()

    # Get selected genres and vocal styles from URL parameters
    selected_genres = self.request.GET.getlist('genre')  # e.g., ?genre=djent&genre=progressive
    selected_vocals = self.request.GET.getlist('vocal_style')

    # OR logic within genre category
    if selected_genres:
        genre_q = Q(genre__slug__in=selected_genres)
        qs = qs.filter(genre_q)

    # OR logic within vocal style category
    if selected_vocals:
        vocal_q = Q(vocal_style__slug__in=selected_vocals)
        qs = qs.filter(vocal_q)  # AND with previous filters

    return qs
```

### SQL Generated
```sql
-- Example: genres=["djent", "progressive"] AND vocals=["clean"]
SELECT * FROM album
WHERE genre_id IN (SELECT id FROM genre WHERE slug IN ('djent', 'progressive'))
  AND vocal_style_id IN (SELECT id FROM vocal_style WHERE slug = 'clean');
```

### Alternatives Considered
- **Multiple filter parameters**: Less intuitive, harder to implement OR within category
- **JSON-based filter spec**: Overcomplicated for this use case
- **Server-side state (session)**: Breaks bookmarking requirement

### References
- Q object combinations: https://docs.djangoproject.com/en/5.2/topics/db/queries/#complex-lookups-with-q-objects
- getlist() for multi-value parameters: https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.QueryDict.getlist

---

## 4. HTMX Integration for Partial Updates

### Decision
Use `hx-get`, `hx-trigger`, and `hx-target` attributes to replace album grid on search/filter/pagination changes without full page reload. Return HTML fragments from Django view when `HX-Request` header present.

### Rationale
- **HTMX already integrated**: Project uses django-htmx, consistent with existing architecture
- **No JavaScript framework needed**: HTMX handles DOM swapping declaratively
- **Server-rendered HTML**: Django templates generate HTML, no JSON API needed
- **Progressive enhancement**: Falls back to full page reload if JavaScript disabled

### Implementation Approach
```html
<!-- Search box with debouncing -->
<input type="search" name="q"
       hx-get="/catalog/albums/"
       hx-trigger="keyup changed delay:500ms, search"
       hx-target="#album-tiles"
       hx-push-url="true"
       hx-indicator="#loading-spinner">

<!-- Checkbox filters -->
<input type="checkbox" name="genre" value="djent"
       hx-get="/catalog/albums/"
       hx-trigger="change"
       hx-target="#album-tiles"
       hx-push-url="true"
       hx-include="[name='genre'], [name='vocal_style'], [name='q']">

<!-- Pagination links -->
<a href="?page=2"
   hx-get="?page=2"
   hx-target="#album-tiles"
   hx-push-url="true">Next</a>
```

```python
# View: Return partial template for HTMX requests
def get_template_names(self):
    if self.request.htmx:
        return ['catalog/components/album_tiles_partial.html']
    return ['catalog/album_list.html']
```

### Alternatives Considered
- **Full page reloads**: Simpler but violates performance requirements (<500ms updates)
- **React/Vue SPA**: Massive complexity increase, requires API, state management, build process
- **Alpine.js**: Lighter than React but still requires client-side state management

### References
- HTMX documentation: https://htmx.org/docs/
- django-htmx library: https://django-htmx.readthedocs.io/
- HTMX examples: https://htmx.org/examples/

---

## 5. URL State Management

### Decision
Use URL query parameters for all state: `?q=search&genre=djent&genre=progressive&vocal_style=clean&page=2&page_size=50`. HTMX's `hx-push-url="true"` updates browser history.

### Rationale
- **Bookmarkable**: Users can save and share exact filter/search/page state
- **Browser back/forward works**: URL history navigation restores state automatically
- **No server-side session needed**: Stateless, scales horizontally
- **SEO-friendly**: Search engines can crawl different filter combinations

### Implementation Approach
- **Form serialization**: HTMX automatically serializes form inputs to URL parameters
- **`hx-include` attribute**: Ensures all filters included in HTMX requests (e.g., include search box value with checkbox change)
- **Django QueryDict**: `request.GET.getlist('genre')` handles multiple values for same parameter
- **Template tags**: Custom template tag to preserve existing URL parameters when generating links

```python
# Custom template tag for URL parameter manipulation
@register.simple_tag
def url_replace(request, **kwargs):
    """Update URL parameters while preserving others."""
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return params.urlencode()

# Template usage
<a href="?{% url_replace request page=2 %}">Page 2</a>
```

### Alternatives Considered
- **Session storage**: Not bookmarkable, breaks browser back/forward
- **POST requests**: Not bookmarkable, requires JavaScript to restore state
- **Client-side routing (pushState only)**: Requires duplicating filter logic in JavaScript

### References
- QueryDict API: https://docs.djangoproject.com/en/5.2/ref/request-response/#querydict-objects
- HTMX push-url: https://htmx.org/attributes/hx-push-url/

---

## 6. Page Size Preference Persistence

### Decision
Use browser `sessionStorage` to persist page size preference within browsing session, override with URL parameter if present.

### Rationale
- **Session-scoped persistence**: User preference remembered until browser tab closed
- **URL takes precedence**: `?page_size=100` overrides stored preference (explicit intent)
- **No server-side state**: Simpler than cookies or database storage
- **Lightweight JavaScript**: ~10 lines to read/write sessionStorage

### Implementation Approach
```javascript
// Save page size to sessionStorage on change
document.getElementById('page-size-selector').addEventListener('change', (e) => {
    sessionStorage.setItem('catalog_page_size', e.target.value);
    // HTMX triggers request automatically via hx-get
});

// Restore page size on page load (if not in URL)
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    if (!urlParams.has('page_size')) {
        const savedSize = sessionStorage.getItem('catalog_page_size');
        if (savedSize) {
            document.getElementById('page-size-selector').value = savedSize;
        }
    }
});
```

### Alternatives Considered
- **Cookies**: More persistent than needed, requires server-side read/write
- **localStorage**: Too persistent (survives browser restart, could confuse users)
- **Database user preference**: Requires authentication, overkill for unauthenticated catalog browsing

### References
- Web Storage API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API
- sessionStorage: https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage

---

## 7. Search Debouncing with HTMX

### Decision
Use HTMX's built-in `delay` modifier on `hx-trigger` to debounce search input: `hx-trigger="keyup changed delay:500ms"`.

### Rationale
- **No custom JavaScript**: HTMX handles debouncing declaratively
- **500ms delay matches spec**: Executes 500ms after user stops typing
- **`changed` modifier**: Only triggers if input value actually changed (prevents redundant requests)
- **`search` event**: Also triggers on clear button (X) click

### Implementation Approach
```html
<input type="search"
       name="q"
       placeholder="Search albums, artists, genres..."
       minlength="3"
       hx-get="/catalog/albums/"
       hx-trigger="keyup changed delay:500ms, search"
       hx-target="#album-tiles"
       hx-push-url="true">
```

### Client-Side Validation
```javascript
// Prevent search requests for queries < 3 characters
document.addEventListener('htmx:configRequest', (e) => {
    const searchInput = e.detail.parameters.q;
    if (searchInput && searchInput.length < 3) {
        e.preventDefault();  // Block request
    }
});
```

### Alternatives Considered
- **Custom JavaScript debounce**: Reinventing wheel, HTMX provides this
- **Server-side only validation**: Wastes requests, HTMX makes client-side trivial
- **Lodash debounce**: External dependency, HTMX built-in is sufficient

### References
- HTMX trigger modifiers: https://htmx.org/attributes/hx-trigger/#trigger-modifiers
- HTMX events: https://htmx.org/events/

---

## Summary of Decisions

| Area | Technology Choice | Key Rationale |
|------|------------------|---------------|
| Pagination | Django Paginator | Built-in, handles edge cases, URL-based state |
| Search | Q objects + `__icontains` | Simple, performant for <10k albums, no external deps |
| Filters | Q objects with IN queries | Efficient OR within category, AND between categories |
| HTMX Integration | hx-get + hx-target | Partial updates, no full page reload, declarative |
| URL State | Query parameters | Bookmarkable, browser back/forward, stateless |
| Page Size Storage | sessionStorage | Session-scoped, no server state, lightweight |
| Search Debouncing | HTMX delay modifier | Declarative, no custom JavaScript needed |

## Performance Optimizations

1. **Database Indexes**: Ensure indexes on `album.name`, `artist.name`, `genre.name`, `vocal_style.name`, `genre.slug`, `vocal_style.slug`
2. **Select Related**: Use `.select_related('artist', 'genre', 'vocal_style')` to avoid N+1 queries
3. **Distinct Queries**: Apply `.distinct()` when searching across relationships
4. **Pagination Count Caching**: Django Paginator caches count for request duration
5. **HTMX Request Caching**: Browser caches GET requests, reduces server load for back/forward navigation

## Open Questions / Future Enhancements (Out of Scope)

- Advanced search operators (quoted phrases, boolean AND/OR/NOT)
- Search result highlighting
- Relevance-based ranking
- Autocomplete / typeahead suggestions
- Saved search/filter presets
- Export filtered results

---

**Research Complete**: All technical approaches validated, ready for Phase 1 (data model & contracts)
