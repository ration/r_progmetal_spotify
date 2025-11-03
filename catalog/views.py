"""Views for the Album Catalog application."""

from typing import Any

from django.db.models import Q, QuerySet
from django.views.generic import ListView, DetailView

from catalog.models import Album, Genre, VocalStyle, SyncRecord


class AlbumListView(ListView):
    """
    Display a list of albums in a responsive grid layout with pagination.

    Albums are ordered by release date (newest first), with a secondary
    sort by import date. Optimizes queries using select_related for
    artist, genre, and vocal_style foreign keys.

    Pagination: Displays 50 albums per page by default, configurable via
    ?page_size= query parameter.

    Supports HTMX partial updates: When HX-Request header is present,
    returns only the album tiles fragment without page chrome.
    """

    model = Album
    template_name = "catalog/album_list.html"
    context_object_name = "albums"
    paginate_by = 50  # Default page size

    def get_paginate_by(self, queryset: QuerySet[Album]) -> int:
        """
        Return dynamic page size from URL parameter or default.

        Supports ?page_size=25|50|100 query parameter for user preference.

        Args:
            queryset: The album queryset being paginated

        Returns:
            int: Number of items per page (25, 50, or 100)
        """
        page_size = self.request.GET.get("page_size", self.paginate_by)
        try:
            page_size = int(page_size)
            # Validate against allowed values
            if page_size in [25, 50, 100]:
                return page_size
        except (ValueError, TypeError):
            pass
        return self.paginate_by  # type: ignore[return-value]

    def get_template_names(self) -> list[str]:
        """
        Return template name based on request type.

        For HTMX requests (HX-Request header present), return the fragment
        template containing only album tiles and pagination. For regular
        requests, return the full page template.

        Returns:
            list[str]: List containing the appropriate template name
        """
        if self.request.headers.get("HX-Request"):
            return ["catalog/components/album_tiles_partial.html"]
        template_name = self.template_name
        if template_name is None:
            return ["catalog/album_list.html"]
        return [template_name]

    def get_queryset(self) -> QuerySet[Album]:
        """
        Return optimized queryset of albums with search and filtering.

        Supports:
        - ?q=<search> - Free-text search (min 3 chars) across album name,
                        artist name, genre name, vocal style name
        - ?genre=<slug> - Filter by genre slug
        - ?vocal=<slug> - Filter by vocal style slug

        Returns:
            QuerySet[Album]: Albums with related artist, genre, and vocal_style
                pre-fetched, ordered by release_date DESC, then imported_at DESC
        """
        queryset = Album.objects.select_related("artist", "genre", "vocal_style")

        # Free-text search (minimum 3 characters)
        search_query = self.request.GET.get("q", "").strip()
        if search_query and len(search_query) >= 3:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(artist__name__icontains=search_query) |
                Q(genre__name__icontains=search_query) |
                Q(vocal_style__name__icontains=search_query)
            ).distinct()

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

        Includes search query, available genres and vocal styles for filters,
        and tracks active filter state.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            dict[str, Any]: Context dictionary with search, filters, and pagination
        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "New Progressive Metal Releases"

        # Add search query context
        search_query = self.request.GET.get("q", "").strip()
        context["search_query"] = search_query
        context["has_search"] = bool(search_query and len(search_query) >= 3)

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
