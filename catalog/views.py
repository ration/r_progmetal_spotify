"""Views for the Album Catalog application."""

import os
from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView

from catalog.models import Album, Genre, VocalStyle, SyncOperation, SyncRecord
from catalog.services.sync_manager import SyncManager


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
        page_size_param = self.request.GET.get("page_size", str(self.paginate_by))
        try:
            page_size = int(page_size_param)
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
                Q(name__icontains=search_query)
                | Q(artist__name__icontains=search_query)
                | Q(genre__name__icontains=search_query)
                | Q(vocal_style__name__icontains=search_query)
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


@csrf_protect
@require_http_methods(["POST"])
def sync_trigger(request: HttpRequest) -> HttpResponse:
    """
    Trigger a manual synchronization operation.

    Creates a new SyncOperation and starts a background thread to perform
    the sync. Returns immediately with 202 Accepted status.

    Error Handling:
    - 409 Conflict: If a sync is already running
    - 503 Service Unavailable: If Spotify credentials are missing

    Args:
        request: HTTP POST request (requires CSRF token)

    Returns:
        HttpResponse: 202 with HX-Trigger header on success, error HTML on failure
    """
    # Check for missing Spotify credentials
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not spotify_client_id or not spotify_client_secret:
        html = """
        <div class="alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
                <div class="font-bold">Configuration Error</div>
                <div class="text-sm">Spotify credentials not configured. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.</div>
            </div>
        </div>
        """
        return HttpResponse(html, status=503, content_type="text/html")

    # Check for active sync with database lock
    try:
        with transaction.atomic():
            active_sync = (
                SyncOperation.objects.filter(Q(status="pending") | Q(status="running"))
                .select_for_update(nowait=True)
                .first()
            )

            if active_sync:
                html = """
                <div class="alert alert-warning">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>Synchronization already in progress. Please wait for it to complete.</span>
                </div>
                """
                return HttpResponse(html, status=409, content_type="text/html")

            # Create new sync operation
            sync_op = SyncOperation.objects.create(
                status="pending",
                created_by_ip=request.META.get("REMOTE_ADDR"),
            )

    except Exception as e:
        html = f"""
        <div class="alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
                <div class="font-bold">Error</div>
                <div class="text-sm">Unable to start synchronization: {str(e)}</div>
            </div>
        </div>
        """
        return HttpResponse(html, status=500, content_type="text/html")

    # Start sync in background thread
    # Note: sync_op.id is set by Django after save() and will always exist here
    sync_op_id = getattr(sync_op, "id", 0)
    SyncManager.start_sync(sync_op_id)

    # Return success response with HX-Trigger header
    html = """
    <div class="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <span>Synchronization started. Fetching albums...</span>
    </div>
    """
    response = HttpResponse(html, status=202, content_type="text/html")
    response["HX-Trigger"] = "syncStarted"
    return response


@require_http_methods(["GET"])
def sync_status(request: HttpRequest) -> HttpResponse:
    """
    Poll for current synchronization status.

    Returns HTML fragment showing current sync progress, or idle state
    if no sync is active.

    Response Headers:
    - HX-Trigger: stopPolling (when sync completes)
    - HX-Trigger: syncCompleted (when sync succeeds)

    Args:
        request: HTTP GET request

    Returns:
        HttpResponse: HTML fragment with current status
    """
    # Query for active sync operation
    current_sync = (
        SyncOperation.objects.filter(Q(status="pending") | Q(status="running"))
        .order_by("-started_at")
        .first()
    )

    # If no active sync, check for recently completed
    if not current_sync:
        completed_sync = (
            SyncOperation.objects.filter(Q(status="completed") | Q(status="failed"))
            .order_by("-completed_at")
            .first()
        )

        if completed_sync and completed_sync.status == "completed":
            # Show success or warning message based on error_message presence
            duration = completed_sync.duration()
            duration_str = (
                f"{int(duration.total_seconds() // 60)} minutes"
                if duration
                else "unknown"
            )

            # Check if this is a partial failure (has error_message despite completed status)
            if (
                completed_sync.error_message
                and "Warning:" in completed_sync.error_message
            ):
                # Partial success - show warning
                html = f"""
                <div class="alert alert-warning">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                        <div class="font-bold">Sync Completed with Warnings</div>
                        <div class="text-sm">{completed_sync.error_message}</div>
                        <div class="text-sm mt-1">Completed in {duration_str}.</div>
                    </div>
                </div>
                """
            else:
                # Full success
                html = f"""
                <div class="alert alert-success">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                        <div class="font-bold">Sync Complete!</div>
                        <div class="text-sm">Updated {completed_sync.albums_processed} albums successfully. Completed in {duration_str}.</div>
                    </div>
                </div>
                """

            response = HttpResponse(html, content_type="text/html")
            response["HX-Trigger"] = "syncCompleted, stopPolling"
            return response

        elif completed_sync and completed_sync.status == "failed":
            # Show error message
            html = f"""
            <div class="alert alert-error">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                    <div class="font-bold">Sync Failed</div>
                    <div class="text-sm">{completed_sync.error_message or "An unknown error occurred."}</div>
                </div>
            </div>
            """
            response = HttpResponse(html, content_type="text/html")
            response["HX-Trigger"] = "syncFailed, stopPolling"
            return response

        # No sync active or recently completed
        html = '<div class="text-sm text-base-content/70">No synchronization in progress.</div>'
        return HttpResponse(html, content_type="text/html")

    # Sync is active - show progress
    progress_pct = current_sync.progress_percentage()
    duration = current_sync.duration()
    duration_str = (
        f"{int(duration.total_seconds() // 60)} minutes" if duration else "0 minutes"
    )

    html = f"""
    <div class="flex items-center gap-4">
        <span class="loading loading-spinner loading-md"></span>
        <div class="flex-1">
            <div class="font-semibold">{current_sync.display_status()}</div>
            <div class="text-sm text-base-content/70">Processing albums from Google Sheets and Spotify</div>
            """

    if progress_pct is not None:
        html += f"""
            <progress class="progress progress-primary w-full mt-2" value="{progress_pct}" max="100"></progress>
            <div class="text-xs text-base-content/60 mt-1">{progress_pct}% complete • Started {duration_str} ago</div>
        """

    html += """
        </div>
    </div>
    """

    return HttpResponse(html, content_type="text/html")
