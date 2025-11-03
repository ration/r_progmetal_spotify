"""Django admin configuration for the Album Catalog application."""

from django.contrib import admin
from catalog.models import Album, Artist, Genre, VocalStyle, SyncRecord


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    """Admin interface for Album model."""

    list_display = [
        "name",
        "artist",
        "genre",
        "vocal_style",
        "release_date",
        "imported_at",
    ]
    list_filter = ["genre", "vocal_style", "release_date"]
    search_fields = ["name", "artist__name"]
    readonly_fields = ["imported_at", "updated_at", "spotify_album_id"]
    date_hierarchy = "release_date"


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    """Admin interface for Artist model."""

    list_display = ["name", "country", "spotify_artist_id"]
    search_fields = ["name", "country"]
    readonly_fields = ["spotify_artist_id"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """Admin interface for Genre model."""

    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


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
