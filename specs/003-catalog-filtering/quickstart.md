# Quickstart Guide: Enhanced Catalog Filtering

**Feature**: 003-catalog-filtering
**Date**: 2025-11-03
**Purpose**: Step-by-step guide for developers implementing pagination, search, and filtering

## Prerequisites

- Existing Django 5.2.8 project with `catalog` app
- Album, Artist, Genre, VocalStyle models already exist
- HTMX already integrated (`django-htmx` installed)
- PostgreSQL or SQLite database with test data (175+ albums recommended)

## Implementation Order

Follow this order to deliver user stories incrementally:

1. **P1: Pagination** (baseline functionality)
2. **P2: Search** (highest value feature)
3. **P3: Checkbox Filters** (discovery/browsing)
4. **P4: Page Size Configuration** (personalization)

---

## Phase 1: Pagination (P1)

### Step 1.1: Modify AlbumListView

**File**: `catalog/views.py`

```python
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from catalog.models import Album

class AlbumListView(ListView):
    model = Album
    template_name = 'catalog/album_list.html'
    context_object_name = 'albums'
    paginate_by = 50  # Default page size

    def get_queryset(self):
        """Base queryset with optimized joins."""
        return Album.objects.select_related(
            'artist', 'genre', 'vocal_style'
        ).order_by('-release_date', '-imported_at')

    def get_paginate_by(self, queryset):
        """Allow dynamic page size from URL parameter."""
        page_size = self.request.GET.get('page_size', 50)
        try:
            page_size = int(page_size)
            if page_size not in [25, 50, 100]:
                return 50  # Default if invalid
            return page_size
        except (ValueError, TypeError):
            return 50
```

### Step 1.2: Create Pagination Component

**File**: `catalog/templates/catalog/components/pagination.html`

```html
{% if is_paginated %}
<div class="pagination flex items-center justify-between py-4">
    <!-- Page info -->
    <div class="text-sm text-base-content/60">
        Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
        (Showing {{ page_obj.start_index }}-{{ page_obj.end_index }} of {{ page_obj.paginator.count }} albums)
    </div>

    <!-- Navigation -->
    <div class="flex gap-2">
        {% if page_obj.has_previous %}
            <a href="?{% url_replace request page=page_obj.previous_page_number %}"
               hx-get="?{% url_replace request page=page_obj.previous_page_number %}"
               hx-target="#album-tiles"
               hx-push-url="true"
               class="btn btn-sm btn-outline">
                Previous
            </a>
        {% endif %}

        <!-- Page numbers (show first, last, and pages around current) -->
        {% for num in page_obj.paginator.page_range %}
            {% if num == page_obj.number %}
                <span class="btn btn-sm btn-active">{{ num }}</span>
            {% elif num == 1 or num == page_obj.paginator.num_pages or num >= page_obj.number|add:"-2" and num <= page_obj.number|add:"2" %}
                <a href="?{% url_replace request page=num %}"
                   hx-get="?{% url_replace request page=num %}"
                   hx-target="#album-tiles"
                   hx-push-url="true"
                   class="btn btn-sm btn-outline">
                    {{ num }}
                </a>
            {% elif num == 2 and page_obj.number > 4 %}
                <span class="btn btn-sm btn-disabled">...</span>
            {% elif num == page_obj.paginator.num_pages|add:"-1" and page_obj.number < page_obj.paginator.num_pages|add:"-3" %}
                <span class="btn btn-sm btn-disabled">...</span>
            {% endif %}
        {% endfor %}

        {% if page_obj.has_next %}
            <a href="?{% url_replace request page=page_obj.next_page_number %}"
               hx-get="?{% url_replace request page=page_obj.next_page_number %}"
               hx-target="#album-tiles"
               hx-push-url="true"
               class="btn btn-sm btn-outline">
                Next
            </a>
        {% endif %}
    </div>
</div>
{% endif %}
```

### Step 1.3: Create URL Parameter Template Tag

**File**: `catalog/templatetags/catalog_extras.py`

```python
from django import template
from django.http import QueryDict

register = template.Library()

@register.simple_tag
def url_replace(request, **kwargs):
    """
    Update URL parameters while preserving existing ones.
    Usage: {% url_replace request page=2 %}
    """
    query = request.GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
```

### Step 1.4: Update Main Template

**File**: `catalog/templates/catalog/album_list.html`

```html
{% load catalog_extras %}

<!DOCTYPE html>
<html>
<head>
    <title>Album Catalog</title>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
    <link href="https://cdn.tailwindcss.com/4.0.0-alpha.1" rel="stylesheet">
</head>
<body>
    <div class="container mx-auto px-4">
        <h1 class="text-3xl font-bold my-6">Album Catalog</h1>

        <!-- Album grid -->
        <div id="album-tiles" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {% for album in page_obj %}
                {% include "catalog/components/album_tile.html" %}
            {% endfor %}
        </div>

        <!-- Pagination -->
        {% include "catalog/components/pagination.html" %}
    </div>
</body>
</html>
```

### Step 1.5: Test Pagination

```bash
# Run development server
python manage.py runserver

# Test in browser:
# - http://localhost:8000/catalog/albums/ (page 1)
# - http://localhost:8000/catalog/albums/?page=2 (page 2)
# - http://localhost:8000/catalog/albums/?page=999 (should default to last page)

# Run tests
pytest tests/test_pagination.py -v
```

---

## Phase 2: Search (P2)

### Step 2.1: Add Search Form

**File**: `catalog/forms.py` (create if doesn't exist)

```python
from django import forms

class SearchForm(forms.Form):
    """Form for search input."""
    q = forms.CharField(
        required=False,
        min_length=3,
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search albums, artists, genres...',
            'class': 'input input-bordered w-full',
        })
    )

    def clean_q(self):
        """Validate and clean search query."""
        query = self.cleaned_data.get('q', '').strip()
        if query and len(query) < 3:
            return ''  # Ignore short queries
        return query
```

### Step 2.2: Create Search Box Component

**File**: `catalog/templates/catalog/components/search_box.html`

```html
<div class="search-box mb-6">
    <input type="search"
           name="q"
           value="{{ search_query }}"
           placeholder="Search albums, artists, genres..."
           class="input input-bordered w-full"
           minlength="3"
           hx-get="/catalog/albums/"
           hx-trigger="keyup changed delay:500ms, search"
           hx-target="#album-tiles"
           hx-push-url="true"
           hx-indicator="#loading-spinner"
           hx-include="[name='genre'], [name='vocal_style'], [name='page_size']">

    <div id="loading-spinner" class="htmx-indicator">
        <span class="loading loading-spinner loading-sm"></span>
    </div>

    {% if search_query %}
        <button hx-get="/catalog/albums/"
                hx-target="#album-tiles"
                hx-push-url="true"
                class="btn btn-sm btn-ghost">
            Clear search
        </button>
    {% endif %}
</div>
```

### Step 2.3: Add Search to View

**File**: `catalog/views.py` (update `get_queryset`)

```python
from django.db.models import Q

class AlbumListView(ListView):
    # ... existing code ...

    def get_queryset(self):
        """Apply search and return filtered queryset."""
        qs = super().get_queryset()

        # Get search query
        search_query = self.request.GET.get('q', '').strip()

        # Apply search if query is valid (>= 3 characters)
        if search_query and len(search_query) >= 3:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(artist__name__icontains=search_query) |
                Q(genre__name__icontains=search_query) |
                Q(vocal_style__name__icontains=search_query)
            ).distinct()

        return qs

    def get_context_data(self, **kwargs):
        """Add search state to context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['has_search'] = bool(context['search_query'])
        return context
```

### Step 2.4: Add Client-Side Validation

**File**: `catalog/templates/catalog/base.html` (or album_list.html `<script>` section)

```html
<script>
// Prevent search requests for queries < 3 characters
document.addEventListener('htmx:configRequest', (event) => {
    const searchQuery = event.detail.parameters.q;
    if (searchQuery && searchQuery.length > 0 && searchQuery.length < 3) {
        event.preventDefault();  // Block request
    }
});
</script>
```

### Step 2.5: Update Main Template

```html
<!-- Add search box above album grid -->
<h1 class="text-3xl font-bold my-6">Album Catalog</h1>

{% include "catalog/components/search_box.html" %}

<div id="album-tiles" class="grid ...">
    ...
</div>
```

### Step 2.6: Test Search

```bash
# Test in browser:
# - Type "periphery" (should show Periphery albums)
# - Type "djent" (should show albums tagged with Djent genre)
# - Type "ab" (should not trigger search - < 3 chars)

# Run tests
pytest tests/test_search.py -v
```

---

## Phase 3: Checkbox Filters (P3)

### Step 3.1: Create Filter Form

**File**: `catalog/forms.py` (add to existing file)

```python
class FilterForm(forms.Form):
    """Form for checkbox filters."""
    genre = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    vocal_style = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        """Populate choices from database."""
        super().__init__(*args, **kwargs)
        self.fields['genre'].choices = [
            (g.slug, g.name) for g in Genre.objects.all().order_by('name')
        ]
        self.fields['vocal_style'].choices = [
            (v.slug, v.name) for v in VocalStyle.objects.all().order_by('name')
        ]
```

### Step 3.2: Create Filters Component

**File**: `catalog/templates/catalog/components/filters.html`

```html
<div class="filters mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
    <!-- Genre filters -->
    <div class="filter-group card bg-base-200 p-4">
        <h3 class="font-semibold mb-2">Genre</h3>
        {% for genre in all_genres %}
            <label class="label cursor-pointer justify-start gap-2">
                <input type="checkbox"
                       name="genre"
                       value="{{ genre.slug }}"
                       class="checkbox checkbox-sm"
                       {% if genre.slug in selected_genres %}checked{% endif %}
                       hx-get="/catalog/albums/"
                       hx-trigger="change"
                       hx-target="#album-tiles"
                       hx-push-url="true"
                       hx-include="[name='q'], [name='genre'], [name='vocal_style'], [name='page_size']">
                <span class="label-text">{{ genre.name }}</span>
            </label>
        {% endfor %}
    </div>

    <!-- Vocal style filters -->
    <div class="filter-group card bg-base-200 p-4">
        <h3 class="font-semibold mb-2">Vocal Style</h3>
        {% for vocal in all_vocals %}
            <label class="label cursor-pointer justify-start gap-2">
                <input type="checkbox"
                       name="vocal_style"
                       value="{{ vocal.slug }}"
                       class="checkbox checkbox-sm"
                       {% if vocal.slug in selected_vocals %}checked{% endif %}
                       hx-get="/catalog/albums/"
                       hx-trigger="change"
                       hx-target="#album-tiles"
                       hx-push-url="true"
                       hx-include="[name='q'], [name='genre'], [name='vocal_style'], [name='page_size']">
                <span class="label-text">{{ vocal.name }}</span>
            </label>
        {% endfor %}
    </div>

    <!-- Clear filters button -->
    {% if has_filters %}
        <div class="col-span-2">
            <button hx-get="/catalog/albums/"
                    hx-target="#album-tiles"
                    hx-push-url="true"
                    hx-include="[name='q'], [name='page_size']"
                    class="btn btn-sm btn-outline">
                Clear all filters ({{ filter_count }})
            </button>
        </div>
    {% endif %}
</div>
```

### Step 3.3: Update View for Filters

**File**: `catalog/views.py` (update `get_queryset` and `get_context_data`)

```python
class AlbumListView(ListView):
    # ... existing code ...

    def get_queryset(self):
        """Apply search and filters."""
        qs = super().get_queryset()

        # Search (from Phase 2)
        search_query = self.request.GET.get('q', '').strip()
        if search_query and len(search_query) >= 3:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(artist__name__icontains=search_query) |
                Q(genre__name__icontains=search_query) |
                Q(vocal_style__name__icontains=search_query)
            ).distinct()

        # Genre filters (OR within category)
        selected_genres = self.request.GET.getlist('genre')
        if selected_genres:
            qs = qs.filter(genre__slug__in=selected_genres)

        # Vocal style filters (OR within category)
        selected_vocals = self.request.GET.getlist('vocal_style')
        if selected_vocals:
            qs = qs.filter(vocal_style__slug__in=selected_vocals)

        return qs

    def get_context_data(self, **kwargs):
        """Add filter state to context."""
        context = super().get_context_data(**kwargs)

        # Search state (from Phase 2)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['has_search'] = bool(context['search_query'])

        # Filter state
        context['selected_genres'] = self.request.GET.getlist('genre')
        context['selected_vocals'] = self.request.GET.getlist('vocal_style')
        context['has_filters'] = bool(context['selected_genres'] or context['selected_vocals'])
        context['filter_count'] = len(context['selected_genres']) + len(context['selected_vocals'])

        # Available filter options
        context['all_genres'] = Genre.objects.all().order_by('name')
        context['all_vocals'] = VocalStyle.objects.all().order_by('name')

        return context
```

### Step 3.4: Test Filters

```bash
# Test in browser:
# - Check "Djent" and "Progressive Metal" (should show albums with either genre)
# - Check "Djent" (genre) AND "Clean" (vocal) (should show only Djent with clean vocals)
# - Clear filters (should show all albums)

# Run tests
pytest tests/test_filters.py -v
```

---

## Phase 4: Page Size Configuration (P4)

### Step 4.1: Create Page Size Selector Component

**File**: `catalog/templates/catalog/components/page_size_selector.html`

```html
<div class="page-size-selector flex items-center gap-2 my-4">
    <label for="page-size" class="text-sm">Items per page:</label>
    <select id="page-size"
            name="page_size"
            class="select select-sm select-bordered"
            hx-get="/catalog/albums/"
            hx-trigger="change"
            hx-target="#album-tiles"
            hx-push-url="true"
            hx-include="[name='q'], [name='genre'], [name='vocal_style']">
        <option value="25" {% if page_size == 25 %}selected{% endif %}>25</option>
        <option value="50" {% if page_size == 50 %}selected{% endif %}>50</option>
        <option value="100" {% if page_size == 100 %}selected{% endif %}>100</option>
    </select>
</div>

<script>
// Save page size to sessionStorage
document.getElementById('page-size').addEventListener('change', (e) => {
    sessionStorage.setItem('catalog_page_size', e.target.value);
});

// Restore page size on load (if not in URL)
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    if (!urlParams.has('page_size')) {
        const savedSize = sessionStorage.getItem('catalog_page_size');
        if (savedSize && [25, 50, 100].includes(parseInt(savedSize))) {
            document.getElementById('page-size').value = savedSize;
        }
    }
});
</script>
```

### Step 4.2: Update Context Data

**File**: `catalog/views.py` (update `get_context_data`)

```python
def get_context_data(self, **kwargs):
    """Add page size to context."""
    context = super().get_context_data(**kwargs)

    # ... existing context ...

    # Page size state
    context['page_size'] = self.get_paginate_by(self.get_queryset())
    context['page_size_options'] = [25, 50, 100]

    return context
```

### Step 4.3: Add to Main Template

```html
<!-- Add above or below filters -->
{% include "catalog/components/page_size_selector.html" %}
```

### Step 4.4: Test Page Size

```bash
# Test in browser:
# - Select "25 items per page" (should show 25 albums)
# - Navigate to page 2 (should maintain 25 items per page)
# - Close tab, reopen (should remember preference)

# Run tests
pytest tests/test_page_size.py -v
```

---

## HTMX Partial Template

Create a partial template that returns only album tiles for HTMX requests.

**File**: `catalog/views.py` (update `get_template_names`)

```python
def get_template_names(self):
    """Return partial template for HTMX requests."""
    if self.request.htmx:
        return ['catalog/components/album_tiles_partial.html']
    return [self.template_name]
```

**File**: `catalog/templates/catalog/components/album_tiles_partial.html`

```html
{% load catalog_extras %}

<!-- Album tiles only (no page structure) -->
{% for album in page_obj %}
    {% include "catalog/components/album_tile.html" %}
{% endfor %}

<!-- Empty state -->
{% if not page_obj %}
    <div class="col-span-full text-center py-12">
        <p class="text-lg text-base-content/60">
            {% if search_query %}
                No albums found matching "{{ search_query }}"
            {% else %}
                No albums found matching your filters
            {% endif %}
        </p>
        <button hx-get="/catalog/albums/"
                hx-target="#album-tiles"
                hx-push-url="true"
                class="btn btn-primary mt-4">
            Clear filters
        </button>
    </div>
{% endif %}

<!-- Update pagination (outside album-tiles div) -->
<div id="pagination" hx-swap-oob="true">
    {% include "catalog/components/pagination.html" %}
</div>
```

---

## Testing Checklist

### Manual Testing

- [ ] Pagination works without JavaScript (fallback to full page reload)
- [ ] Search debounces correctly (500ms delay)
- [ ] Short queries (< 3 chars) don't trigger search
- [ ] Filters combine correctly (OR within category, AND between categories)
- [ ] Page size persists across page navigation
- [ ] URL can be bookmarked and shared
- [ ] Browser back/forward buttons work correctly
- [ ] Empty states display correctly

### Automated Tests

```bash
# Run all tests
pytest tests/test_pagination.py tests/test_search.py tests/test_filters.py tests/test_integration.py -v

# Run type checking
pyright catalog/

# Run linting
ruff check catalog/

# Run formatting
ruff format catalog/
```

---

## Performance Checklist

- [ ] Database indexes exist on searched/filtered fields
- [ ] `select_related()` used to avoid N+1 queries
- [ ] `distinct()` used when searching across joins
- [ ] Page load time < 2s (use Django Debug Toolbar)
- [ ] HTMX updates < 500ms (use browser DevTools Network tab)

---

## Deployment

### Database Migrations

```bash
# No migrations needed (no model changes)
# Verify indexes exist:
python manage.py dbshell
\d album  # PostgreSQL
.schema album  # SQLite
```

### Static Files

```bash
# Collect static files (if using whitenoise/nginx)
python manage.py collectstatic --noinput
```

### Environment Variables

No new environment variables required.

---

## Troubleshooting

### Search not working

- **Check**: Minimum 3 characters entered
- **Check**: `distinct()` called on queryset when searching
- **Check**: Database indexes exist on searched fields

### Filters not combining correctly

- **Check**: Using `getlist()` for multi-value parameters
- **Check**: Separate `.filter()` calls for each category (ensures AND logic)

### HTMX not updating

- **Check**: `hx-target` selector matches element ID
- **Check**: `HX-Request` header present in Django view
- **Check**: Partial template returns correct HTML fragment

### Page size not persisting

- **Check**: `sessionStorage` supported in browser
- **Check**: JavaScript console for errors
- **Check**: `page_size` parameter in URL overrides sessionStorage

---

**Implementation Complete**: Follow phases 1-4 in order for incremental delivery of user stories
