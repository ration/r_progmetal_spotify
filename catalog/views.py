"""Views for the Album Catalog application."""

from typing import Any

from django.db.models import QuerySet
from django.views.generic import ListView

from catalog.models import Album


class AlbumListView(ListView):
    """
    Display a list of albums in a responsive grid layout.

    Albums are ordered by release date (newest first), with a secondary
    sort by import date. Optimizes queries using select_related for
    artist, genre, and vocal_style foreign keys.
    """

    model = Album
    template_name = "catalog/album_list.html"
    context_object_name = "albums"

    def get_queryset(self) -> QuerySet[Album]:
        """
        Return optimized queryset of albums ordered by release date.

        Returns:
            QuerySet[Album]: Albums with related artist, genre, and vocal_style
                pre-fetched, ordered by release_date DESC, then imported_at DESC
        """
        return Album.objects.select_related("artist", "genre", "vocal_style").order_by(
            "-release_date", "-imported_at"
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Add additional context for the template.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            dict[str, Any]: Context dictionary with page title
        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "New Progressive Metal Releases"
        return context
