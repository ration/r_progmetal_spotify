# Data Model: Enhanced Catalog Filtering and Pagination

**Feature**: 003-catalog-filtering
**Date**: 2025-11-03
**Purpose**: Document data structures and relationships for pagination, search, and filtering

## Overview

This feature does not introduce new database models. It enhances the existing `Album`, `Artist`, `Genre`, and `VocalStyle` models with:
- Queryset filtering based on search and filter inputs
- Pagination state management (view-level, not persisted)
- URL parameter handling for state persistence

## Existing Models (No Changes)

### Album

```python
class Album(models.Model):
    """Album entity with metadata from Spotify."""
    name = models.CharField(max_length=500)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True)
    vocal_style = models.ForeignKey(VocalStyle, on_delete=models.SET_NULL, null=True)
    release_date = models.DateField()
    spotify_url = models.URLField()
    cover_image_url = models.URLField(blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date', '-imported_at']  # Most recent first
        indexes = [
            models.Index(fields=['name']),          # For search
            models.Index(fields=['release_date']),  # For ordering
            models.Index(fields=['genre']),         # For filtering
            models.Index(fields=['vocal_style']),   # For filtering
        ]
```

**Searchable Fields**:
- `name` (album name)
- `artist.name` (via foreign key)
- `genre.name` (via foreign key)
- `vocal_style.name` (via foreign key)

**Filterable Fields**:
- `genre` (foreign key)
- `vocal_style` (foreign key)

### Artist

```python
class Artist(models.Model):
    """Artist entity."""
    name = models.CharField(max_length=500)
    country = models.CharField(max_length=100, blank=True)
    spotify_artist_id = models.CharField(max_length=50, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),  # For search
        ]
```

### Genre

```python
class Genre(models.Model):
    """Genre taxonomy."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),  # For search
            models.Index(fields=['slug']),  # For filtering (URL params use slugs)
        ]
```

### VocalStyle

```python
class VocalStyle(models.Model):
    """Vocal style taxonomy."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),  # For search
            models.Index(fields=['slug']),  # For filtering (URL params use slugs)
        ]
```

## View-Level Data Structures

These are Python objects/dictionaries used in views and templates, not persisted to database.

### PaginationState

**Purpose**: Encapsulates pagination metadata for template rendering

**Source**: Django `Page` object from `Paginator`

**Attributes**:
```python
{
    'current_page': int,      # Current page number (1-indexed)
    'total_pages': int,       # Total number of pages
    'has_previous': bool,     # Whether previous page exists
    'has_next': bool,         # Whether next page exists
    'previous_page': int|None, # Previous page number or None
    'next_page': int|None,     # Next page number or None
    'start_index': int,       # Index of first item on page (1-indexed)
    'end_index': int,         # Index of last item on page
    'total_count': int,       # Total items across all pages
    'page_range': list[int],  # List of page numbers to display
}
```

**Template Usage**:
```html
<span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
<span>Showing {{ page_obj.start_index }}-{{ page_obj.end_index }} of {{ page_obj.paginator.count }}</span>
```

### SearchQuery

**Purpose**: Represents parsed search input

**Source**: `request.GET.get('q')`

**Attributes**:
```python
{
    'query': str,              # Raw search string
    'is_valid': bool,          # True if query >= 3 characters
    'matched_fields': list[str], # ['name', 'artist__name', 'genre__name', 'vocal_style__name']
}
```

**Validation**:
- Minimum length: 3 characters
- Stripped of leading/trailing whitespace
- Empty string treated as no search

### FilterSelection

**Purpose**: Represents active filter choices

**Source**: `request.GET.getlist('genre')` and `request.GET.getlist('vocal_style')`

**Attributes**:
```python
{
    'selected_genres': list[str],      # Genre slugs e.g., ['djent', 'progressive-metal']
    'selected_vocals': list[str],      # Vocal style slugs e.g., ['clean', 'mixed']
    'has_filters': bool,               # True if any filters active
    'filter_count': int,               # Total number of active filters
}
```

**Filtering Logic**:
- **OR within category**: Albums match ANY selected genre OR ANY selected vocal style within that category
- **AND between categories**: Albums must match selected genre(s) AND selected vocal style(s)

Example:
- Filters: `genre=djent`, `genre=progressive-metal`, `vocal_style=clean`
- Result: Albums where `(genre='djent' OR genre='progressive-metal') AND vocal_style='clean'`

### PageSizePreference

**Purpose**: User's page size preference

**Source**: `request.GET.get('page_size')` or `sessionStorage.getItem('catalog_page_size')`

**Attributes**:
```python
{
    'page_size': int,          # 25, 50, or 100
    'is_default': bool,        # True if using default (50)
    'valid_options': list[int], # [25, 50, 100]
}
```

**Validation**:
- Must be one of [25, 50, 100]
- Defaults to 50 if invalid or missing
- Stored in browser `sessionStorage` (not persisted server-side)

## URL Parameter Schema

All catalog state is encoded in URL query parameters for bookmarkability.

### Parameter Spec

| Parameter | Type | Values | Example | Description |
|-----------|------|--------|---------|-------------|
| `q` | string | Any text | `?q=periphery` | Search query (min 3 chars) |
| `genre` | string[] | Genre slugs | `?genre=djent&genre=progressive-metal` | Selected genres (OR logic) |
| `vocal_style` | string[] | Vocal slugs | `?vocal_style=clean` | Selected vocal styles (OR logic) |
| `page` | int | 1-N | `?page=2` | Current page number |
| `page_size` | int | 25, 50, 100 | `?page_size=100` | Items per page |

### Example URLs

**Pagination only**:
```
/catalog/albums/?page=2
```

**Search only**:
```
/catalog/albums/?q=periphery
```

**Filters only**:
```
/catalog/albums/?genre=djent&genre=progressive-metal&vocal_style=clean
```

**Combined state**:
```
/catalog/albums/?q=2025&genre=djent&page=2&page_size=100
```

### URL Parameter Handling

**Multi-value parameters**: Django's `request.GET.getlist('genre')` returns list for repeated parameters

**Encoding**: Use `urlencode()` for proper encoding of special characters

**Preservation**: Custom template tag `{% url_replace request page=2 %}` preserves existing parameters when generating new URLs

## Queryset Filtering

### Base Queryset

```python
# Start with all albums, ordered by most recent
Album.objects.all().select_related('artist', 'genre', 'vocal_style').order_by('-release_date', '-imported_at')
```

### Search Filtering

```python
if search_query and len(search_query) >= 3:
    queryset = queryset.filter(
        Q(name__icontains=search_query) |
        Q(artist__name__icontains=search_query) |
        Q(genre__name__icontains=search_query) |
        Q(vocal_style__name__icontains=search_query)
    ).distinct()
```

**SQL Generated** (PostgreSQL):
```sql
SELECT DISTINCT album.* FROM album
LEFT JOIN artist ON album.artist_id = artist.id
LEFT JOIN genre ON album.genre_id = genre.id
LEFT JOIN vocal_style ON album.vocal_style_id = vocal_style.id
WHERE (
    LOWER(album.name) LIKE LOWER('%periphery%') OR
    LOWER(artist.name) LIKE LOWER('%periphery%') OR
    LOWER(genre.name) LIKE LOWER('%periphery%') OR
    LOWER(vocal_style.name) LIKE LOWER('%periphery%')
)
ORDER BY album.release_date DESC, album.imported_at DESC;
```

### Genre Filtering

```python
if selected_genres:
    queryset = queryset.filter(genre__slug__in=selected_genres)
```

**SQL Generated**:
```sql
WHERE genre.slug IN ('djent', 'progressive-metal')
```

### Vocal Style Filtering

```python
if selected_vocals:
    queryset = queryset.filter(vocal_style__slug__in=selected_vocals)
```

**SQL Generated**:
```sql
WHERE vocal_style.slug IN ('clean', 'mixed')
```

### Combined Filtering

**Search AND Genre AND Vocal**:
```python
queryset = Album.objects.all().select_related('artist', 'genre', 'vocal_style')

if search_query and len(search_query) >= 3:
    queryset = queryset.filter(
        Q(name__icontains=search_query) |
        Q(artist__name__icontains=search_query) |
        Q(genre__name__icontains=search_query) |
        Q(vocal_style__name__icontains=search_query)
    ).distinct()

if selected_genres:
    queryset = queryset.filter(genre__slug__in=selected_genres)

if selected_vocals:
    queryset = queryset.filter(vocal_style__slug__in=selected_vocals)

queryset = queryset.order_by('-release_date', '-imported_at')
```

**SQL Generated** (example: search="2025", genres=["djent"], vocals=["clean"]):
```sql
SELECT DISTINCT album.* FROM album
LEFT JOIN artist ON album.artist_id = artist.id
LEFT JOIN genre ON album.genre_id = genre.id
LEFT JOIN vocal_style ON album.vocal_style_id = vocal_style.id
WHERE (
    LOWER(album.name) LIKE LOWER('%2025%') OR
    LOWER(artist.name) LIKE LOWER('%2025%') OR
    LOWER(genre.name) LIKE LOWER('%2025%') OR
    LOWER(vocal_style.name) LIKE LOWER('%2025%')
)
AND genre.slug IN ('djent')
AND vocal_style.slug IN ('clean')
ORDER BY album.release_date DESC, album.imported_at DESC;
```

## Performance Considerations

### Database Indexes

**Existing indexes (verify in migrations)**:
- `album.name` (for search)
- `album.release_date` (for ordering)
- `album.genre_id` (foreign key, for filtering)
- `album.vocal_style_id` (foreign key, for filtering)
- `artist.name` (for search)
- `genre.name` (for search)
- `genre.slug` (for filtering)
- `vocal_style.name` (for search)
- `vocal_style.slug` (for filtering)

### Query Optimization

**select_related()**: Fetch related Artist, Genre, VocalStyle in single query (avoid N+1)

**distinct()**: Required when searching across joins to prevent duplicate albums

**Count caching**: Django Paginator caches count for request duration

### Scalability

**Current scale**: <1000 albums, 20 genres, 10 vocal styles
**Expected performance**: <200ms query time with proper indexes
**Bottlenecks**: `ILIKE` queries on large text fields (album/artist names)

**Future optimization** (if needed):
- Full-text search (PostgreSQL `to_tsvector`, GIN indexes)
- Materialized views for common filter combinations
- Redis caching for popular queries

## Edge Cases

### Empty Result Sets

**Search with no matches**:
```python
queryset = Album.objects.filter(search_conditions)  # Returns empty QuerySet
# Template displays: "No albums found matching 'xyz'"
```

**Filters with no matches**:
```python
queryset = Album.objects.filter(genre__slug__in=['nonexistent'])  # Returns empty QuerySet
# Template displays: "No albums found matching your filters"
```

### Invalid Page Numbers

**Handled by Django Paginator**:
```python
try:
    page = paginator.page(page_number)
except PageNotAnInteger:
    page = paginator.page(1)  # Default to first page
except EmptyPage:
    page = paginator.page(paginator.num_pages)  # Default to last page
```

### Page Number Out of Range After Filtering

**Example**: User on page 5, applies filter that returns only 30 results (1 page)
**Handling**: Redirect to last valid page (page 1 in this case)

### Special Characters in Search

**Input**: `"C++ programming"`
**Handling**: Django ORM escapes special characters automatically, safe for SQL injection

### URL Parameter Injection

**Protection**: Django's `QueryDict` handles parameter parsing safely
**Validation**: Page size validated against allowed values [25, 50, 100]

## Testing Data Requirements

### Minimal Test Data

- **Albums**: 175+ albums (to test pagination across 4 pages with 50 items/page)
- **Genres**: At least 3 different genres (to test OR logic within category)
- **Vocal Styles**: At least 2 different vocal styles (to test AND logic between categories)
- **Artists**: At least 10 artists with varying names (to test search across artists)

### Edge Case Test Data

- Album with name matching genre name (e.g., album "Djent" in genre "Progressive Metal")
- Artist with name containing search term (e.g., "Periphery")
- Albums with same name, different artists (test distinct())
- Albums with null genre or vocal_style (test filtering behavior)

---

**Data Model Complete**: No database schema changes required, all state managed via querysets and URL parameters
