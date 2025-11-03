"""Views for the Album Catalog application."""

from typing import Any

from django.db.models import QuerySet
from django.views.generic import ListView, DetailView

from catalog.models import Album, Genre, VocalStyle, SyncRecord


class AlbumListView(ListView):
    """
    Display a list of albums in a responsive grid layout.

    Albums are ordered by release date (newest first), with a secondary
    sort by import date. Optimizes queries using select_related for
    artist, genre, and vocal_style foreign keys.

    Supports HTMX partial updates: When HX-Request header is present,
    returns only the album tiles fragment without page chrome.
    """

    model = Album
    template_name = "catalog/album_list.html"
    context_object_name = "albums"

    def get_template_names(self) -> list[str]:
        """
        Return template name based on request type.

        For HTMX requests (HX-Request header present), return the fragment
        template containing only album tiles. For regular requests, return
        the full page template.

        Returns:
            list[str]: List containing the appropriate template name
        """
        if self.request.headers.get("HX-Request"):
            return ["catalog/album_list_tiles.html"]
        template_name = self.template_name
        if template_name is None:
            return ["catalog/album_list.html"]
        return [template_name]

    def get_queryset(self) -> QuerySet[Album]:
        """
        Return optimized queryset of albums ordered by release date.

        Supports filtering by genre and vocal style via query parameters:
        - ?genre=<slug> - Filter by genre slug
        - ?vocal=<slug> - Filter by vocal style slug

        Returns:
            QuerySet[Album]: Albums with related artist, genre, and vocal_style
                pre-fetched, ordered by release_date DESC, then imported_at DESC
        """
        queryset = Album.objects.select_related("artist", "genre", "vocal_style")

        # Filter by genre if provided
        genre_slug = self.request.GET.get("genre")
        if genre_slug:
            queryset = queryset.filter(genre__slug=genre_slug)

        # Filter by vocal style if provided
        vocal_slug = self.request.GET.get("vocal")
        if vocal_slug:
            queryset = queryset.filter(vocal_style__slug=vocal_slug)

        return queryset.order_by("-release_date", "-imported_at")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Add additional context for the template.

        Includes available genres and vocal styles for filter dropdowns,
        and tracks active filter state.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            dict[str, Any]: Context dictionary with page title, filters, and active state
        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "New Progressive Metal Releases"

        # Add available genres and vocal styles for filters
        context["genres"] = Genre.objects.all().order_by("name")
        context["vocal_styles"] = VocalStyle.objects.all().order_by("name")

        # Track active filters
        context["active_genre"] = self.request.GET.get("genre", "")
        context["active_vocal"] = self.request.GET.get("vocal", "")
        context["has_active_filters"] = bool(
            context["active_genre"] or context["active_vocal"]
        )

        # Add synchronization statistics
        context["latest_sync"] = SyncRecord.objects.filter(success=True).first()
        context["total_albums"] = Album.objects.count()

        return context


class AlbumDetailView(DetailView):
    """
    Display detailed information for a single album.

    Shows high-resolution cover art, all album metadata, and provides
    a link to listen on Spotify. Includes a back button to return to
    the catalog listing.
    """

    model = Album
    template_name = "catalog/album_detail.html"
    context_object_name = "album"

    def get_queryset(self) -> QuerySet[Album]:
        """
        Return optimized queryset with related objects pre-fetched.

        Returns:
            QuerySet[Album]: Albums with artist, genre, and vocal_style pre-loaded
        """
        return Album.objects.select_related("artist", "genre", "vocal_style")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Add additional context for the template.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            dict[str, Any]: Context dictionary with page title
        """
        context = super().get_context_data(**kwargs)
        album = self.get_object()
        context["page_title"] = f"{album.name} by {album.artist.name}"
        return context
