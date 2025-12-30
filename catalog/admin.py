"""Django admin configuration for the Album Catalog application."""

from django.contrib import admin
from catalog.models import Album, Artist, Genre, VocalStyle, SyncRecord, ListenedAlbum


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    """Admin interface for Album model."""

    list_display = [
        "name",
        "artist",
        "get_genres",
        "vocal_style",
        "release_date",
        "imported_at",
    ]
    list_filter = ["genres", "vocal_style", "release_date"]
    search_fields = ["name", "artist__name"]
    readonly_fields = ["imported_at", "updated_at", "spotify_album_id"]
    date_hierarchy = "release_date"
    filter_horizontal = ["genres"]

    @admin.display(description="Genres")
    def get_genres(self, obj):
        """Display comma-separated list of genres for admin list view."""
        return ", ".join(genre.name for genre in obj.genres.all())


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    """Admin interface for Artist model."""

    list_display = ["name", "country", "spotify_artist_id"]
    search_fields = ["name", "country"]
    readonly_fields = ["spotify_artist_id"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """Admin interface for Genre model."""

    list_display = ["name", "slug", "is_ignored", "canonical_genre", "get_albums_count", "get_alias_count"]
    list_filter = ["is_ignored"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}
    list_editable = ["is_ignored", "canonical_genre"]
    ordering = ["name"]

    fieldsets = [
        ("Basic Information", {
            "fields": ["name", "slug"]
        }),
        ("Genre Management", {
            "fields": ["is_ignored", "canonical_genre"],
            "description": (
                "Mark duplicates/aliases by setting 'canonical genre'. "
                "Mark unwanted genres as 'ignored' to hide from filters."
            )
        }),
    ]

    @admin.display(description="Albums")
    def get_albums_count(self, obj):
        """Display count of albums with this genre."""
        count = obj.get_albums_count()
        return f"{count} album{'s' if count != 1 else ''}"

    @admin.display(description="Aliases")
    def get_alias_count(self, obj):
        """Display count of genres that use this as canonical."""
        count = obj.aliases.count()
        if count > 0:
            alias_names = ", ".join(a.name for a in obj.aliases.all()[:3])
            if count > 3:
                alias_names += f" (+{count - 3} more)"
            return f"{count}: {alias_names}"
        return "—"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize canonical_genre dropdown to exclude ignored genres and aliases."""
        if db_field.name == "canonical_genre":
            # Only show genres that are not ignored and not themselves aliases
            kwargs["queryset"] = Genre.objects.filter(
                is_ignored=False,
                canonical_genre__isnull=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(VocalStyle)
class VocalStyleAdmin(admin.ModelAdmin):
    """Admin interface for VocalStyle model."""

    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(SyncRecord)
class SyncRecordAdmin(admin.ModelAdmin):
    """Admin interface for viewing sync history."""

    list_display = [
        "sync_timestamp",
        "albums_created",
        "albums_updated",
        "total_albums_in_catalog",
        "success",
    ]
    list_filter = ["success", "sync_timestamp"]
    readonly_fields = ["sync_timestamp"]  # Prevent manual timestamp editing
    ordering = ["-sync_timestamp"]

    def has_add_permission(self, request):
        """Disable manual creation - SyncRecords created by management command only."""
        return False


@admin.register(ListenedAlbum)
class ListenedAlbumAdmin(admin.ModelAdmin):
    """Admin interface for viewing listened album history."""

    list_display = [
        "user",
        "album",
        "listened_at",
    ]
    list_filter = ["listened_at", "user"]
    search_fields = ["user__display_name", "album__name", "album__artist__name"]
    readonly_fields = ["listened_at"]
    ordering = ["-listened_at"]

    def has_add_permission(self, request):
        """Allow manual creation for testing/admin purposes."""
        return True
