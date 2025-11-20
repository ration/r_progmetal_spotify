"""Views for the Album Catalog application."""

import logging
import os
import secrets
from typing import Any, Optional

from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from spotipy.exceptions import SpotifyException

from catalog.models import Album, Genre, VocalStyle, SyncOperation, SyncRecord, SpotifyToken
from catalog.services.sync_manager import SyncManager
from catalog.services.album_cache import get_cached_cover_url, cache_cover_url
from catalog.services.spotify_client import SpotifyClient
from catalog.services.spotify_auth import spotify_auth_service

logger = logging.getLogger(__name__)


class AlbumListView(ListView):
    """
    Display a list of albums in a responsive grid layout with pagination.

    Albums are ordered by import date (newest added first), with a secondary
    sort by release date. Optimizes queries using select_related for
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
                        artist name, genre names, vocal style name
        - ?genre=<slug> - Filter by genre slug (matches any album with any of these genres)
                          Multiple genres can be specified (e.g., ?genre=djent&genre=prog-rock)
        - ?vocal=<slug> - Filter by vocal style slug (matches any album with any of these styles)
                          Multiple vocal styles can be specified
        - ?sort=<field> - Sort by field (imported_at, -imported_at, release_date, -release_date)

        Returns:
            QuerySet[Album]: Albums with related artist, vocal_style, and genres
                pre-fetched, ordered by specified sort or default
        """
        queryset = Album.objects.select_related("artist", "vocal_style").prefetch_related("genres")

        # Free-text search (minimum 3 characters)
        search_query = self.request.GET.get("q", "").strip()
        if search_query and len(search_query) >= 3:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(artist__name__icontains=search_query)
                | Q(genres__name__icontains=search_query)
                | Q(vocal_style__name__icontains=search_query)
            ).distinct()

        # Filter by genres if provided (matches albums with any of the selected genres)
        genre_slugs = self.request.GET.getlist("genre")
        if genre_slugs:
            # Get Genre objects for the requested slugs
            requested_genres = Genre.objects.filter(slug__in=genre_slugs)

            # Resolve aliases to their canonical genres
            effective_genre_ids = []
            for genre in requested_genres:
                effective_genre = genre.get_effective_genre()
                if not effective_genre.is_ignored:
                    effective_genre_ids.append(effective_genre.id)

            if effective_genre_ids:
                queryset = queryset.filter(genres__id__in=effective_genre_ids).distinct()

        # Filter by vocal styles if provided (matches albums with any of the selected styles)
        vocal_slugs = self.request.GET.getlist("vocal")
        if vocal_slugs:
            queryset = queryset.filter(vocal_style__slug__in=vocal_slugs)

        # Apply sorting
        sort_field = self.request.GET.get("sort", "-imported_at")
        # Validate sort field against allowed values
        allowed_sorts = ["imported_at", "-imported_at", "release_date", "-release_date"]
        if sort_field in allowed_sorts:
            # Primary sort by selected field
            if sort_field.startswith("-"):
                # Descending order (e.g., -imported_at means newest first)
                secondary_field = "-release_date" if "imported" in sort_field else "-imported_at"
            else:
                # Ascending order (e.g., imported_at means oldest first)
                secondary_field = "release_date" if "imported" in sort_field else "imported_at"
            queryset = queryset.order_by(sort_field, secondary_field)
        else:
            # Default sorting
            queryset = queryset.order_by("-imported_at", "-release_date")

        return queryset

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
        # Only show genres that are not ignored and not aliases
        context["genres"] = Genre.objects.filter(
            is_ignored=False,
            canonical_genre__isnull=True
        ).order_by("name")
        context["vocal_styles"] = VocalStyle.objects.all().order_by("name")

        # Track active filters
        context["active_genres"] = self.request.GET.getlist("genre")
        context["active_vocals"] = self.request.GET.getlist("vocal")
        context["active_sort"] = self.request.GET.get("sort", "-imported_at")
        context["has_active_filters"] = bool(
            context["active_genres"] or context["active_vocals"]
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
            QuerySet[Album]: Albums with artist, genres, and vocal_style pre-loaded
        """
        return Album.objects.select_related("artist", "vocal_style").prefetch_related("genres")

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


def admin_sync_page(request: HttpRequest) -> HttpResponse:
    """
    Display the admin sync page with sync controls.

    This view provides a dedicated administrative interface for managing
    album synchronization operations. It displays the sync button, real-time
    status updates, and the timestamp of the last successful sync.

    Context:
        latest_sync: SyncRecord | None - Most recent completed sync operation
        page_title: str - Page title for the template

    Args:
        request: HTTP request object

    Returns:
        Rendered admin sync page template
    """
    from django.shortcuts import render

    latest_sync: Optional[SyncRecord] = (
        SyncRecord.objects.filter(success=True)
        .order_by("-sync_timestamp")
        .first()
    )

    return render(
        request,
        "catalog/admin_sync.html",
        {
            "latest_sync": latest_sync,
            "page_title": "Sync Administration",
        },
    )


@csrf_protect
@require_http_methods(["POST"])
def sync_trigger(request: HttpRequest) -> HttpResponse:
    """
    Trigger a manual synchronization operation.

    Creates a new SyncOperation and starts a background thread to perform
    the sync. Returns immediately with 202 Accepted status.

    Note: Sync no longer requires Spotify credentials (JIT mode). Cover art
    will be loaded on-demand when albums are viewed in the catalog.

    Error Handling:
    - 409 Conflict: If a sync is already running

    Args:
        request: HTTP POST request (requires CSRF token)

    Returns:
        HttpResponse: 202 with HX-Trigger header on success, error HTML on failure
    """
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


@csrf_protect
@require_http_methods(["POST"])
def sync_stop(request: HttpRequest) -> HttpResponse:
    """
    Stop an ongoing synchronization operation.

    Sets the status to 'cancelled' for the active sync. The sync thread
    will detect this and gracefully terminate.

    Error Handling:
    - 404 Not Found: If no active sync operation exists

    Args:
        request: HTTP POST request (requires CSRF token)

    Returns:
        HttpResponse: 200 with success message or 404 if no active sync
    """
    # Find active sync operation
    active_sync = (
        SyncOperation.objects.filter(Q(status="pending") | Q(status="running"))
        .order_by("-started_at")
        .first()
    )

    if not active_sync:
        html = """
        <div class="alert alert-warning">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>No active synchronization to stop.</span>
        </div>
        """
        return HttpResponse(html, status=404, content_type="text/html")

    # Mark sync as cancelled
    active_sync.status = "cancelled"
    active_sync.stage_message = "Cancelling synchronization..."
    active_sync.save(update_fields=["status", "stage_message"])

    logger.info(f"Sync {active_sync.id} cancellation requested by user")

    # Return success response
    html = """
    <div class="alert alert-warning">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>Cancelling synchronization... This may take a moment.</span>
    </div>
    """
    response = HttpResponse(html, status=200, content_type="text/html")
    response["HX-Trigger"] = "syncStopped"
    return response


@require_http_methods(["GET"])
def sync_button(request: HttpRequest) -> HttpResponse:
    """
    Render the sync/stop button based on current sync state.

    Returns different button HTML depending on whether a sync is active:
    - Active sync: Show "Stop" button (red)
    - No active sync: Show "Sync Now" button (primary)

    Args:
        request: HTTP GET request

    Returns:
        HttpResponse: HTML fragment with appropriate button
    """
    # Check for active sync
    active_sync = (
        SyncOperation.objects.filter(Q(status="pending") | Q(status="running"))
        .order_by("-started_at")
        .first()
    )

    if active_sync:
        # Show Stop button when sync is active
        html = """
        <div class="mb-6">
            <button
                class="btn btn-error"
                hx-post="{% url 'catalog:sync-stop' %}"
                hx-target="#sync-status"
                hx-swap="innerHTML"
                hx-disabled-elt="this">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
                </svg>
                Stop Sync
            </button>

            <span class="text-sm text-base-content/70 ml-4">
                Stop the current synchronization operation
            </span>
        </div>
        """.replace("{% url 'catalog:sync-stop' %}", request.build_absolute_uri('/catalog/sync/stop/').replace(request.build_absolute_uri('/'), '/'))
    else:
        # Show Sync Now button when no sync is active
        html = """
        <div class="mb-6">
            <button
                class="btn btn-primary"
                hx-post="{% url 'catalog:sync-trigger' %}"
                hx-target="#sync-status"
                hx-swap="innerHTML"
                hx-disabled-elt="this"
                hx-indicator="#sync-spinner">
                <span id="sync-spinner" class="loading loading-spinner loading-sm htmx-indicator"></span>
                Sync Now
            </button>

            <span class="text-sm text-base-content/70 ml-4">
                Synchronize album catalog with Google Sheets and Spotify
            </span>
        </div>
        """.replace("{% url 'catalog:sync-trigger' %}", request.build_absolute_uri('/catalog/sync/trigger/').replace(request.build_absolute_uri('/'), '/'))

    return HttpResponse(html, content_type="text/html")


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

        elif completed_sync and completed_sync.status == "cancelled":
            # Show cancelled message
            html = f"""
            <div class="alert alert-warning">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                    <div class="font-bold">Sync Cancelled</div>
                    <div class="text-sm">Synchronization was cancelled by user. {completed_sync.albums_processed or 0} albums were processed before cancellation.</div>
                </div>
            </div>
            """
            response = HttpResponse(html, content_type="text/html")
            response["HX-Trigger"] = "syncCancelled, stopPolling"
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


@require_http_methods(["GET"])
def album_cover_art(request: HttpRequest, album_id: int) -> HttpResponse:
    """
    Fetch album cover art using just-in-time (JIT) loading from Spotify API.

    This view implements lazy loading of cover art:
    1. Check if cover art is cached in database
    2. If not cached, fetch from Spotify API
    3. Cache the result for future requests
    4. Return HTML <img> tag or JSON response

    Supports two response formats:
    - HTML (default): Returns <img> tag ready for HTMX swap
    - JSON: Returns {"cover_url": "...", "cached": true/false}

    Error Handling:
    - 404: Album not found in database
    - 200 with placeholder: Rate limit, API failure, or missing Spotify URL

    Args:
        request: HTTP GET request
            Query params:
                - format: "json" for JSON response (default: HTML)
        album_id: Album primary key

    Returns:
        HttpResponse: HTML fragment with <img> tag or JSON response
    """
    # Get album or return 404
    try:
        album = Album.objects.select_related("artist").get(id=album_id)
    except Album.DoesNotExist:
        raise Http404("Album not found")

    # Determine response format
    response_format = request.GET.get("format", "html").lower()

    # Check if album has Spotify URL
    if not album.spotify_album_id or not album.spotify_url:
        logger.warning(f"Album {album_id} has no Spotify URL")
        return _render_cover_placeholder(
            album, "no-spotify", response_format,
            "Album not available on Spotify"
        )

    # Check cache first
    cached_url = get_cached_cover_url(album_id)
    if cached_url:
        logger.debug(f"Cache hit for album {album_id} cover art")
        return _render_cover_art(album, cached_url, response_format, cached=True)

    # Cache miss - fetch from Spotify API
    logger.debug(f"Cache miss for album {album_id}, fetching from Spotify API")

    try:
        # Initialize Spotify client
        spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
        spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        if not spotify_client_id or not spotify_client_secret:
            logger.error("Spotify credentials not configured")
            return _render_cover_placeholder(
                album, "unavailable", response_format,
                "Spotify API credentials not configured"
            )

        spotify_client = SpotifyClient(spotify_client_id, spotify_client_secret)

        # Fetch cover art from Spotify
        cover_url = spotify_client.fetch_album_cover(album.spotify_album_id)

        if not cover_url:
            logger.warning(f"No cover art found for album {album_id}")
            return _render_cover_placeholder(
                album, "unavailable", response_format,
                "Cover art not available"
            )

        # Cache the cover art URL
        cache_cover_url(album_id, cover_url)
        logger.info(f"Cached cover art for album {album_id}")

        return _render_cover_art(album, cover_url, response_format, cached=False)

    except SpotifyException as e:
        if e.http_status == 429:
            # Rate limit hit - return skeleton placeholder
            logger.warning(f"Rate limit hit for album {album_id}")
            return _render_cover_placeholder(
                album, "skeleton", response_format,
                "Rate limit reached. Please try again later."
            )
        else:
            # Other Spotify API error
            logger.error(f"Spotify API error for album {album_id}: {e}")
            return _render_cover_placeholder(
                album, "unavailable", response_format,
                f"Spotify API error: {e.msg}"
            )

    except Exception as e:
        # Unexpected error
        logger.error(
            f"Unexpected error fetching cover art for album {album_id}: {e}",
            exc_info=True
        )
        return _render_cover_placeholder(
            album, "unavailable", response_format,
            "An unexpected error occurred"
        )


def _render_cover_art(
    album: Album,
    cover_url: str,
    response_format: str,
    cached: bool
) -> HttpResponse:
    """
    Render cover art as HTML <img> tag or JSON response.

    Args:
        album: Album model instance
        cover_url: Spotify cover art URL
        response_format: "html" or "json"
        cached: Whether the cover art was retrieved from cache

    Returns:
        HttpResponse: HTML or JSON response with cover art
    """
    if response_format == "json":
        return JsonResponse({
            "cover_url": cover_url,
            "cached": cached,
            "album_id": album.id,
            "album_name": album.name,
            "artist_name": album.artist.name
        })

    # HTML response with <img> tag
    html = f"""
    <img
        src="{cover_url}"
        alt="{album.name} by {album.artist.name}"
        class="w-full h-auto rounded-lg shadow-lg fade-in"
        loading="lazy"
    />
    """
    response = HttpResponse(html, content_type="text/html")
    response["HX-Trigger"] = "cover-art-loaded"
    return response


def _render_cover_placeholder(
    album: Album,
    placeholder_type: str,
    response_format: str,
    message: str
) -> HttpResponse:
    """
    Render placeholder for missing/unavailable cover art.

    Args:
        album: Album model instance
        placeholder_type: "skeleton", "unavailable", or "no-spotify"
        response_format: "html" or "json"
        message: Error/info message to display

    Returns:
        HttpResponse: HTML or JSON response with placeholder
    """
    if response_format == "json":
        return JsonResponse({
            "cover_url": None,
            "cached": False,
            "placeholder_type": placeholder_type,
            "message": message,
            "album_id": album.id,
            "album_name": album.name,
            "artist_name": album.artist.name
        })

    # HTML response with placeholder
    # Use different styles based on placeholder type
    placeholder_class = "skeleton" if placeholder_type == "skeleton" else "unavailable"

    html = f"""
    <div class="w-full aspect-square bg-base-300 rounded-lg shadow-lg flex items-center justify-center {placeholder_class}">
        <div class="text-center p-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
            <p class="text-xs text-base-content/50 mt-2">{message}</p>
        </div>
    </div>
    """

    return HttpResponse(html, content_type="text/html")


# ============================================================================
# Authentication Views
# ============================================================================


def login_page(request: HttpRequest) -> HttpResponse:
    """
    Display login page with 'Login with Spotify' button.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Rendered login page

    Query parameters:
        next: URL to redirect after successful login (default: /catalog/)
    """
    next_url = request.GET.get('next', '/catalog/')
    return render(request, 'catalog/login.html', {'next_url': next_url})


def spotify_oauth_initiate(request: HttpRequest) -> HttpResponse:
    """
    Initiate Spotify OAuth flow.

    Generates OAuth state for CSRF protection, stores it in session along with
    the next URL, then redirects to Spotify authorization page.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Redirect to Spotify authorization page

    Query parameters:
        next: URL to redirect after successful login (stored in session)
    """
    # Generate and store OAuth state
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state

    # Store next URL for post-login redirect
    next_url = request.GET.get('next', '/catalog/')
    request.session['next_url'] = next_url

    # Redirect to Spotify authorization
    auth_url = spotify_auth_service.generate_auth_url(state)
    return redirect(auth_url)


def spotify_oauth_callback(request: HttpRequest) -> HttpResponse:
    """
    Handle Spotify OAuth callback.

    Validates OAuth state parameter, exchanges authorization code for tokens,
    creates or updates user, and sets up user session.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Redirect to next URL on success, or error page/redirect on failure

    Query parameters:
        code: Authorization code from Spotify (on success)
        state: OAuth state parameter (must match session state)
        error: Error code if user denied authorization
    """
    # Handle user denial
    if 'error' in request.GET:
        error = request.GET.get('error')
        return redirect(f'/catalog/auth/login/?error={error}')

    # Validate OAuth state (CSRF protection)
    state = request.GET.get('state')
    session_state = request.session.get('oauth_state')
    if not state or state != session_state:
        return HttpResponse('Invalid OAuth state parameter', status=400)

    # Exchange code for tokens
    code = request.GET.get('code')
    if not code:
        return HttpResponse('Missing authorization code', status=400)

    try:
        tokens = spotify_auth_service.exchange_code_for_tokens(code)
        profile = spotify_auth_service.fetch_user_profile(tokens['access_token'])
        user = spotify_auth_service.create_or_update_user(profile, tokens)

        # Clear any existing session data
        request.session.flush()

        # Create new session with user_id
        request.session['user_id'] = user.id  # type: ignore[attr-defined]
        request.session.create()

        # Get next URL (use default since session was flushed)
        next_url = '/catalog/'

        logger.info(f"User {user.display_name} logged in successfully, redirecting to {next_url}")

        # Redirect to next URL
        return redirect(next_url)

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        return HttpResponse(f'OAuth error: {str(e)}', status=500)


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    Log out user and clear session.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Redirect to login page

    Requires CSRF token in POST request.
    """
    request.session.flush()
    return redirect('/catalog/auth/login/')


def profile_page(request: HttpRequest) -> HttpResponse:
    """
    Display user profile page.

    Shows Spotify profile information including display name, email,
    profile picture, and admin status.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Rendered profile page or redirect to login if not authenticated
    """
    if not hasattr(request, 'user') or request.user is None:
        return redirect('/catalog/auth/login/?next=/catalog/auth/profile/')

    return render(request, 'catalog/profile.html', {
        'user': request.user,
        'is_admin': request.user.is_admin,  # type: ignore[attr-defined]
    })


@require_http_methods(["POST"])
def disconnect_spotify(request: HttpRequest) -> HttpResponse:
    """
    Disconnect Spotify account and delete tokens.

    Removes the user's SpotifyToken and ends their session.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Redirect to login page with disconnected message

    Requires CSRF token in POST request.
    """
    if hasattr(request, 'user') and request.user:
        SpotifyToken.objects.filter(user=request.user).delete()

    request.session.flush()
    return redirect('/catalog/auth/login/?disconnected=true')
