# Data Model: Album Catalog

**Feature**: Album Catalog Visualization
**Date**: 2025-11-01
**Purpose**: Define database entities, relationships, and validation rules

## Entity Relationship Diagram

```
┌─────────────┐         ┌──────────────┐
│   Artist    │◄────────│    Album     │
│─────────────│  1:N    │──────────────│
│ id (PK)     │         │ id (PK)      │
│ name        │         │ artist_id(FK)│
│ country     │         │ genre_id (FK)│
│ spotify_id  │         │ vocal_id (FK)│
│             │         │ name         │
│             │         │ spotify_id   │
│             │         │ release_date │
│             │         │ cover_art_url│
│             │         │ spotify_url  │
│             │         │ imported_at  │
└─────────────┘         └──────────────┘
                              ▲    ▲
                              │    │
                              │    │
                ┌─────────────┘    └─────────────┐
                │                                 │
                │ N:1                         N:1 │
         ┌──────────────┐               ┌─────────────┐
         │    Genre     │               │ VocalStyle  │
         │──────────────│               │─────────────│
         │ id (PK)      │               │ id (PK)     │
         │ name         │               │ name        │
         │ slug         │               │ slug        │
         └──────────────┘               └─────────────┘
```

## Entities

### Album

**Purpose**: Represents a music album release with metadata from Spotify API

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, Auto-increment | Internal database ID |
| spotify_album_id | String(50) | UNIQUE, NOT NULL, Indexed | Spotify's album ID (extracted from URL) |
| name | String(500) | NOT NULL | Album title (Spotify allows long names) |
| artist | ForeignKey | NOT NULL, ON DELETE CASCADE | Reference to Artist model |
| genre | ForeignKey | NULL, ON DELETE SET NULL | Primary genre classification |
| vocal_style | ForeignKey | NULL, ON DELETE SET NULL | Vocal approach category |
| release_date | Date | NULL | Official release date (partial dates supported) |
| cover_art_url | URL(1000) | NULL | Spotify CDN URL for album cover (high-res) |
| spotify_url | URL(500) | NOT NULL | Full Spotify album link (for user navigation) |
| imported_at | DateTime | NOT NULL, Auto | Timestamp of data import/last sync |
| updated_at | DateTime | NOT NULL, Auto | Timestamp of last update |

**Validation Rules**:
- `spotify_album_id`: Must match pattern `^[a-zA-Z0-9]{22}$` (Spotify ID format)
- `name`: Max 500 characters, strip leading/trailing whitespace
- `release_date`: Accept partial dates (year-only, year-month) via CharField with date parsing
- `cover_art_url`: Must be valid URL or NULL (fallback to placeholder)
- `spotify_url`: Must start with `https://open.spotify.com/album/`

**Methods**:
- `get_absolute_url()`: Returns `/catalog/albums/{id}/`
- `get_cover_art_or_placeholder()`: Returns cover_art_url or fallback image path
- `formatted_release_date()`: Returns human-readable date (e.g., "January 2025", "2025", "Jan 15, 2025")

**Indexes**:
- `spotify_album_id` (unique index for fast lookup during sync)
- `release_date` (for ordering by newest first)
- `artist_id, genre_id, vocal_style_id` (composite index for filtering)

**String Representation**: `"{artist.name} - {name} ({release_date.year})"`

---

### Artist

**Purpose**: Represents a musical artist or band

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, Auto-increment | Internal database ID |
| name | String(200) | NOT NULL, Indexed | Artist/band name |
| country | String(100) | NULL | Country of origin (from Google Sheets CSV) |
| spotify_artist_id | String(50) | UNIQUE, NULL, Indexed | Spotify's artist ID (for future enhancements) |

**Validation Rules**:
- `name`: Max 200 characters, strip whitespace
- `country`: Max 100 characters (handles "United Kingdom", "Czech Republic", etc.)
- `spotify_artist_id`: Optional, pattern `^[a-zA-Z0-9]{22}$`

**Methods**:
- `get_albums()`: Returns QuerySet of related albums ordered by release date

**Indexes**:
- `name` (for artist search/autocomplete in future)
- `spotify_artist_id` (unique index if present)

**String Representation**: `"{name} ({country})"` or `"{name}"` if country is NULL

---

### Genre

**Purpose**: Categorizes albums by musical style (progressive metal subgenres)

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, Auto-increment | Internal database ID |
| name | String(100) | UNIQUE, NOT NULL | Human-readable genre name |
| slug | String(100) | UNIQUE, NOT NULL, Indexed | URL-safe identifier (e.g., "progressive-metal") |

**Validation Rules**:
- `name`: Max 100 characters, unique (case-insensitive)
- `slug`: Auto-generated from name (lowercase, hyphens), unique

**Expected Values** (seeded during migration):
- Progressive Metal
- Technical Death Metal
- Djent
- Post-Metal
- Atmospheric Progressive Metal
- Progressive Death Metal
- Progressive Metalcore
- Instrumental Progressive Metal

**Methods**:
- `get_albums_count()`: Returns count of albums in this genre

**Indexes**:
- `slug` (for URL filtering: `/catalog/albums/?genre=djent`)

**String Representation**: `"{name}"`

---

### VocalStyle

**Purpose**: Categorizes albums by vocal approach

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, Auto-increment | Internal database ID |
| name | String(50) | UNIQUE, NOT NULL | Vocal style name |
| slug | String(50) | UNIQUE, NOT NULL, Indexed | URL-safe identifier |

**Validation Rules**:
- `name`: Max 50 characters, unique (case-insensitive)
- `slug`: Auto-generated from name

**Expected Values** (seeded during migration):
- Clean Vocals
- Harsh Vocals
- Mixed Vocals (Clean & Harsh)
- Instrumental (No Vocals)

**Methods**:
- `get_albums_count()`: Returns count of albums with this vocal style

**Indexes**:
- `slug` (for URL filtering: `/catalog/albums/?vocal=instrumental`)

**String Representation**: `"{name}"`

---

## Relationships

### Album → Artist (Many-to-One)

- **Foreign Key**: `Album.artist → Artist.id`
- **Cardinality**: Many albums can belong to one artist
- **Cascade Behavior**: ON DELETE CASCADE (if artist deleted, remove their albums)
- **Rationale**: Simplifies data model; multi-artist collaborations use primary artist

### Album → Genre (Many-to-One)

- **Foreign Key**: `Album.genre → Genre.id`
- **Cardinality**: Each album has one primary genre
- **Cascade Behavior**: ON DELETE SET NULL (preserve album if genre removed)
- **Rationale**: Simplifies filtering; complex tagging out of scope for MVP

### Album → VocalStyle (Many-to-One)

- **Foreign Key**: `Album.vocal_style → VocalStyle.id`
- **Cardinality**: Each album has one vocal style classification
- **Cascade Behavior**: ON DELETE SET NULL
- **Rationale**: Single classification sufficient for filtering needs

---

## Data Import Mapping

### Google Sheets CSV → Database

| CSV Column | Entity | Field | Transformation |
|------------|--------|-------|----------------|
| Release Date | Album | release_date | Parse string → Date (handle "YYYY", "YYYY-MM", "YYYY-MM-DD") |
| Artist | Artist | name | Lookup or create by name |
| Album | Album | name | Direct mapping |
| Spotify URL | Album | spotify_url | Direct mapping |
|  | Album | spotify_album_id | Extract from URL (last path segment) |
| Genre | Genre | name | Lookup by name (case-insensitive), create if missing |
| Country | Artist | country | Direct mapping to artist |
| Vocal Style | VocalStyle | name | Lookup by name, create if missing |

### Spotify API → Database

| Spotify API Field | Entity | Field | Notes |
|-------------------|--------|-------|-------|
| album.id | Album | spotify_album_id | Unique identifier |
| album.name | Album | name | May differ from CSV (use Spotify as source of truth) |
| album.images[0].url | Album | cover_art_url | Highest resolution image |
| album.release_date | Album | release_date | Spotify format: "YYYY-MM-DD" or "YYYY" |
| album.artists[0].name | Artist | name | Primary artist only |
| album.artists[0].id | Artist | spotify_artist_id | For future use |
| artist.genres[0] | Genre | name | Fetch from artist endpoint (albums don't have genres) |

**Note**: Spotify API data overrides CSV data for name, release_date, artist name (Spotify is authoritative source).

---

## Database Migrations

### Initial Migration

1. Create `Artist` table
2. Create `Genre` table with seed data (8 common genres)
3. Create `VocalStyle` table with seed data (4 vocal styles)
4. Create `Album` table with foreign keys
5. Create indexes on `spotify_album_id`, `release_date`, filter fields

### Seed Data

**Genres** (added via data migration):
```python
genres = [
    "Progressive Metal", "Technical Death Metal", "Djent",
    "Post-Metal", "Atmospheric Progressive Metal",
    "Progressive Death Metal", "Progressive Metalcore",
    "Instrumental Progressive Metal"
]
```

**Vocal Styles** (added via data migration):
```python
vocal_styles = [
    "Clean Vocals", "Harsh Vocals",
    "Mixed Vocals (Clean & Harsh)", "Instrumental (No Vocals)"
]
```

---

## Query Patterns

### Common Queries

**Browse all albums (newest first)**:
```python
Album.objects.select_related('artist', 'genre', 'vocal_style')\
    .order_by('-release_date', '-imported_at')
```

**Filter by genre**:
```python
Album.objects.filter(genre__slug='progressive-metal')\
    .select_related('artist', 'genre', 'vocal_style')\
    .order_by('-release_date')
```

**Filter by vocal style**:
```python
Album.objects.filter(vocal_style__slug='instrumental')\
    .select_related('artist', 'vocal_style')\
    .order_by('-release_date')
```

**Filter by multiple criteria**:
```python
Album.objects.filter(
    genre__slug='djent',
    vocal_style__slug='mixed-vocals'
)\
.select_related('artist', 'genre', 'vocal_style')\
.order_by('-release_date')
```

**Lookup album by Spotify ID (for sync)**:
```python
Album.objects.get(spotify_album_id='3IBcauSj5M2A6lTeffJzdv')
```

### Performance Optimizations

- `select_related()`: Always fetch artist, genre, vocal_style with album queries (avoids N+1 queries)
- `order_by('-release_date')`: Use index on release_date for fast sorting
- `prefetch_related()`: Not needed (no many-to-many relationships in MVP)

---

## Data Integrity Rules

### Import/Sync Rules

1. **Upsert Logic**: Use `spotify_album_id` as unique key
   - If exists: Update name, release_date, cover_art_url, updated_at
   - If new: Create album with all fields

2. **Artist Matching**: Lookup artist by name (case-insensitive)
   - If exists: Reuse existing artist record
   - If new: Create artist with name and country from CSV

3. **Genre/Vocal Style Matching**: Lookup by name (case-insensitive)
   - If exists: Use existing record
   - If missing: Create new record with auto-generated slug

4. **Null Handling**:
   - Missing genre in CSV: Set `Album.genre = None`
   - Missing vocal style: Set `Album.vocal_style = None`
   - Missing cover art URL: Set `Album.cover_art_url = None`
   - Missing release date: Set `Album.release_date = None`

5. **Error Handling**:
   - Invalid Spotify URL: Skip row, log error
   - Duplicate spotify_album_id: Update existing record
   - Spotify API failure: Retry 3 times, then skip, log error

### Validation at Model Level

**Album.clean()**:
```python
def clean(self):
    if self.spotify_url and not self.spotify_url.startswith('https://open.spotify.com/album/'):
        raise ValidationError('Invalid Spotify album URL')

    if self.spotify_album_id and len(self.spotify_album_id) != 22:
        raise ValidationError('Invalid Spotify album ID format')

    if self.name:
        self.name = self.name.strip()

    if self.release_date and self.release_date > timezone.now().date():
        # Allow future dates (pre-orders), but warn
        pass
```

---

## Summary

**Total Entities**: 4 (Album, Artist, Genre, VocalStyle)

**Relationships**: 3 foreign keys (Album → Artist, Album → Genre, Album → VocalStyle)

**Indexes**: 7 (spotify_album_id, release_date, artist.name, genre.slug, vocal_style.slug, artist.spotify_artist_id)

**Validation Layers**:
1. Database constraints (NOT NULL, UNIQUE, foreign keys)
2. Django model validation (clean() methods, field validators)
3. Import script validation (CSV parsing, Spotify API response checks)

**Design Principles**:
- Normalized for query efficiency (avoid data duplication)
- Foreign keys over many-to-many (simpler for MVP scope)
- Nullable foreign keys (graceful degradation if genre/vocal data missing)
- Indexed fields for common filter operations
- Spotify ID as authoritative unique identifier
