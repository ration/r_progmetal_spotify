"""
Django models for the Album Catalog application.

This module defines the data models for storing album, artist, genre, and vocal style
information. Album data is sourced from Google Sheets CSV and enriched via Spotify API.
"""

from __future__ import annotations
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify

if TYPE_CHECKING:
    from django.db.models import QuerySet


class Artist(models.Model):
    """
    Represents a musical artist or band.

    Attributes:
        name: Artist/band name
        country: Country of origin (from Google Sheets CSV)
        spotify_artist_id: Spotify's unique artist ID (optional, for future enhancements)
    """

    name = models.CharField(max_length=200, db_index=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    spotify_artist_id = models.CharField(
        max_length=50, unique=True, blank=True, null=True, db_index=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Artists"

    def __str__(self):
        """Return string representation of artist."""
        if self.country:
            return f"{self.name} ({self.country})"
        return self.name

    def get_albums(self) -> QuerySet[Album]:
        """Return QuerySet of albums by this artist, ordered by release date."""
        return self.album_set.order_by("-release_date")  # type: ignore[attr-defined]


class Genre(models.Model):
    """
    Categorizes albums by musical style (progressive metal subgenres).

    Attributes:
        name: Human-readable genre name (e.g., "Progressive Metal")
        slug: URL-safe identifier (e.g., "progressive-metal")
        is_ignored: If True, genre is hidden from filters and UI
        canonical_genre: If set, this genre is an alias/duplicate of the canonical genre
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    is_ignored = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Hide this genre from filters and UI"
    )
    canonical_genre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aliases',
        help_text="If this is a duplicate/alias, select the canonical genre to use instead"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        """Return genre name."""
        if self.canonical_genre:
            return f"{self.name} → {self.canonical_genre.name}"
        elif self.is_ignored:
            return f"{self.name} (ignored)"
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Prevent self-reference
        if self.canonical_genre == self:
            raise ValidationError(
                {"canonical_genre": "A genre cannot be its own canonical genre."}
            )

        # Prevent circular references
        if self.canonical_genre:
            if self.canonical_genre.canonical_genre:
                raise ValidationError(
                    {"canonical_genre": "Cannot reference a genre that is itself an alias. Choose the canonical genre directly."}
                )

    def get_effective_genre(self) -> 'Genre':
        """
        Return the canonical genre if this is an alias, otherwise return self.

        Returns:
            Genre: The canonical genre to use for filtering and display
        """
        return self.canonical_genre if self.canonical_genre else self

    def get_albums_count(self) -> int:
        """Return count of albums in this genre."""
        return self.albums.count()  # type: ignore[attr-defined]


class VocalStyle(models.Model):
    """
    Categorizes albums by vocal approach.

    Attributes:
        name: Vocal style name (e.g., "Clean Vocals", "Harsh Vocals")
        slug: URL-safe identifier (e.g., "clean-vocals")
    """

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Vocal Styles"

    def __str__(self):
        """Return vocal style name."""
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_albums_count(self) -> int:
        """Return count of albums with this vocal style."""
        return self.album_set.count()  # type: ignore[attr-defined]


class Album(models.Model):
    """
    Represents a music album release with metadata from Spotify API.

    Attributes:
        spotify_album_id: Spotify's unique album ID (extracted from URL)
        name: Album title
        artist: Foreign key to Artist model
        genres: Many-to-many relationship to Genre model (supports multiple genres per album)
        vocal_style: Foreign key to VocalStyle model (optional)
        release_date: Official release date (can be partial: year or year-month)
        cover_art_url: Spotify CDN URL for album cover art
        spotify_url: Full Spotify album link
        imported_at: Timestamp of data import
        updated_at: Timestamp of last update
    """

    spotify_album_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Spotify's unique album identifier",
    )
    name = models.CharField(max_length=500)
    artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name="album_set"
    )
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name="albums",
        help_text="Genres this album belongs to (supports multiple genres)",
    )
    vocal_style = models.ForeignKey(
        VocalStyle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="album_set",
    )
    release_date = models.DateField(null=True, blank=True)
    cover_art_url = models.URLField(max_length=1000, blank=True, null=True)
    spotify_url = models.URLField(max_length=500)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Just-in-Time Spotify API cache fields
    spotify_cover_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
        help_text="Cached Spotify cover art URL fetched on-demand",
    )
    spotify_cover_cached_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when cover art was cached",
    )
    spotify_metadata_json = models.JSONField(
        blank=True,
        null=True,
        help_text="Cached detailed Spotify metadata (genres, tracks, popularity)",
    )
    spotify_metadata_cached_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when metadata was cached",
    )

    class Meta:
        ordering = ["-release_date", "-imported_at"]
        indexes = [
            models.Index(fields=["spotify_album_id"]),
            models.Index(fields=["-release_date"]),
            models.Index(fields=["artist", "vocal_style"]),
            models.Index(fields=["spotify_cover_cached_at"]),
        ]

    def __str__(self):
        """Return string representation of album."""
        if self.release_date:
            year = self.release_date.year
            return f"{self.artist.name} - {self.name} ({year})"
        return f"{self.artist.name} - {self.name}"

    def get_absolute_url(self) -> str:
        """Return URL for album detail view."""
        return reverse("catalog:album-detail", kwargs={"pk": self.pk})

    def get_cover_art_or_placeholder(self) -> str:
        """
        Return cover art URL or placeholder if not available.

        Returns:
            str: URL to album cover art or placeholder image path
        """
        if self.cover_art_url:
            return self.cover_art_url
        # Return path to placeholder image
        return "/static/catalog/images/placeholder-album.svg"

    def formatted_release_date(self) -> str:
        """
        Return human-readable release date.

        Returns:
            str: Formatted date (e.g., "January 2025", "2025", "Jan 15, 2025")
        """
        if not self.release_date:
            return "Unknown"

        # Full date available
        if self.release_date.day != 1:
            return self.release_date.strftime("%b %d, %Y")

        # Only year-month available
        if self.release_date.month != 1:
            return self.release_date.strftime("%B %Y")

        # Only year available
        return str(self.release_date.year)

    def clean(self):
        """
        Validate model fields.

        Raises:
            ValidationError: If spotify_url is invalid or spotify_album_id format is wrong
        """
        super().clean()

        # Validate Spotify URL
        if self.spotify_url and not self.spotify_url.startswith(
            "https://open.spotify.com/album/"
        ):
            raise ValidationError(
                {
                    "spotify_url": "Invalid Spotify album URL. Must start with https://open.spotify.com/album/"
                }
            )

        # Validate Spotify album ID format (22 character alphanumeric)
        if self.spotify_album_id and len(self.spotify_album_id) != 22:
            raise ValidationError(
                {
                    "spotify_album_id": "Invalid Spotify album ID format. Must be 22 characters."
                }
            )

        # Strip whitespace from name
        if self.name:
            self.name = self.name.strip()

        # Warn if release date is in the future (allow pre-orders)
        if self.release_date and self.release_date > timezone.now().date():
            # This is acceptable for pre-orders, just a note
            pass

        # Validate cache field consistency (JIT Spotify API feature)
        if self.spotify_cover_url and not self.spotify_cover_cached_at:
            raise ValidationError(
                {
                    "spotify_cover_cached_at": "Must be set when cover URL is cached"
                }
            )

        if self.spotify_metadata_json and not self.spotify_metadata_cached_at:
            raise ValidationError(
                {
                    "spotify_metadata_cached_at": "Must be set when metadata is cached"
                }
            )


class SyncRecord(models.Model):
    """
    Records catalog synchronization operations.

    Tracks metadata about each sync run to enable display of synchronization
    statistics to users (last sync time, albums added, total count).

    Attributes:
        sync_timestamp: When this synchronization completed
        albums_created: Number of new albums added during this sync
        albums_updated: Number of existing albums updated during this sync
        albums_skipped: Number of albums skipped (already current)
        total_albums_in_catalog: Total album count in catalog after this sync
        success: Whether sync completed successfully
        error_message: Error details if sync failed
    """

    sync_timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this synchronization completed",
    )
    albums_created = models.IntegerField(
        default=0, help_text="Number of new albums added during this sync"
    )
    albums_updated = models.IntegerField(
        default=0, help_text="Number of existing albums updated during this sync"
    )
    albums_skipped = models.IntegerField(
        default=0, help_text="Number of albums skipped (already current)"
    )
    total_albums_in_catalog = models.IntegerField(
        help_text="Total album count in catalog after this sync"
    )
    success = models.BooleanField(
        default=True, help_text="Whether sync completed successfully"
    )
    error_message = models.TextField(
        blank=True, null=True, help_text="Error details if sync failed"
    )

    class Meta:
        ordering = ["-sync_timestamp"]
        verbose_name = "Sync Record"
        verbose_name_plural = "Sync Records"
        indexes = [
            models.Index(fields=["-sync_timestamp"], name="idx_sync_timestamp_desc")
        ]

    def __str__(self) -> str:
        """String representation for admin interface."""
        status = "Success" if self.success else "Failed"
        timestamp_str = self.sync_timestamp.strftime("%Y-%m-%d %H:%M")
        return f"Sync at {timestamp_str} - {status}"

    def albums_added_display(self) -> str:
        """Format albums_created for display (e.g., '+15 new' or '+0 new')."""
        return f"+{self.albums_created} new" if self.albums_created > 0 else "+0 new"

    @property
    def total_changes(self) -> int:
        """Total albums affected by this sync (created + updated)."""
        return self.albums_created + self.albums_updated


class SyncOperation(models.Model):
    """
    Tracks real-time status and progress of an active synchronization operation.

    This model is used for in-progress sync operations to enable status polling
    and progress display. When a sync completes, a SyncRecord is created for
    historical logging.

    Attributes:
        status: Current operation state (pending, running, completed, failed)
        stage: Current sync stage (fetching, processing, finalizing)
        stage_message: Human-readable status text for UI display
        albums_processed: Number of albums processed so far
        total_albums: Total albums to process (set after fetching from Google Sheets)
        started_at: When sync operation began
        completed_at: When sync operation finished (success or failure)
        error_message: Error details if status is failed
        created_by_ip: IP address that triggered sync (for audit logging)
        current_tab: Name of the currently processing Google Sheets tab (empty when not processing)
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    STAGE_CHOICES = [
        ("fetching", "Fetching"),
        ("processing", "Processing"),
        ("finalizing", "Finalizing"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current operation state",
        db_index=True,
    )
    stage = models.CharField(
        max_length=50,
        choices=STAGE_CHOICES,
        blank=True,
        help_text="Current sync stage",
    )
    stage_message = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable status text",
    )
    albums_processed = models.IntegerField(
        default=0, help_text="Number of albums processed so far"
    )
    total_albums = models.IntegerField(
        null=True, blank=True, help_text="Total albums to process"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When sync operation began",
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When sync operation finished"
    )
    error_message = models.TextField(
        blank=True, help_text="Error details if status is failed"
    )
    created_by_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address that triggered sync"
    )
    current_tab = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Name of the currently processing Google Sheets tab",
    )

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Sync Operation"
        verbose_name_plural = "Sync Operations"
        indexes = [
            models.Index(fields=["status"], name="idx_sync_op_status"),
            models.Index(fields=["-started_at"], name="idx_sync_op_started"),
        ]

    def __str__(self) -> str:
        """String representation for admin interface."""
        # Note: self.id is a Django-added attribute for primary key
        sync_id = getattr(self, "id", "unknown")
        return f"Sync {sync_id} - {self.status} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"

    def progress_percentage(self) -> int | None:
        """
        Calculate completion percentage (0-100) or None if total unknown.

        Returns:
            int: Progress percentage (0-100), or None if total_albums is not set
        """
        if self.total_albums and self.total_albums > 0:
            return min(100, int((self.albums_processed / self.total_albums) * 100))
        return None

    def duration(self) -> timedelta | None:
        """
        Calculate sync duration or current duration if running.

        Returns:
            timedelta: Duration from start to completion (or current time if running)
        """
        if self.completed_at:
            return self.completed_at - self.started_at
        elif self.status == "running":
            return timezone.now() - self.started_at
        return None

    def is_active(self) -> bool:
        """
        Return True if sync is pending or running.

        Returns:
            bool: True if status is pending or running
        """
        return self.status in ("pending", "running")

    def is_cancellable(self) -> bool:
        """
        Return True if sync can be cancelled (pending or running).

        Returns:
            bool: True if status is pending or running (not completed, failed, or already cancelled)
        """
        return self.status in ("pending", "running")

    def display_status(self) -> str:
        """
        Return human-readable status for UI display.

        Returns:
            str: Stage message if present, otherwise formatted status
        """
        if self.stage_message:
            return self.stage_message
        # Note: get_status_display is a Django-added method for choice fields
        return f"Status: {getattr(self, 'get_status_display', lambda: self.status)()}"


class User(models.Model):
    """
    User authenticated via Spotify OAuth.

    Stores Spotify profile information and application-specific attributes
    like admin status. Users are created on first login via OAuth.

    Attributes:
        spotify_user_id: Spotify's unique user ID (from OAuth profile)
        email: User's email address (from Spotify profile)
        display_name: User's display name (from Spotify profile)
        profile_picture_url: URL to user's Spotify profile picture (optional)
        is_admin: Administrator flag for application access control
        created_at: Timestamp of first login (user creation)
        updated_at: Timestamp of last profile update
    """

    spotify_user_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Spotify's unique user ID"
    )
    email = models.EmailField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    profile_picture_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to Spotify profile picture"
    )
    is_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Administrator flag for application access control"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_user'
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Return string representation of user."""
        return f"{self.display_name} ({self.email})"

    @property
    def is_authenticated(self) -> bool:
        """Always return True for authenticated custom User objects."""
        return True


class SpotifyToken(models.Model):
    """
    Stores Spotify OAuth access and refresh tokens for authenticated users.

    Separated from User model for security, token lifecycle management,
    and to support potential future multi-token scenarios.

    Attributes:
        user: One-to-one relationship with User
        access_token: Spotify OAuth access token (short-lived, ~1 hour)
        refresh_token: Spotify OAuth refresh token (long-lived, no expiry)
        expires_at: Timestamp when access_token expires
        created_at: Timestamp of initial token issuance
        updated_at: Timestamp of last token refresh
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='spotify_token'
    )
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_spotify_token'

    def __str__(self) -> str:
        """Return string representation of token."""
        return f"Token for {self.user.display_name}"

    def expires_soon(self) -> bool:
        """
        Returns True if token expires within 5 minutes.

        Returns:
            bool: True if expires_at < now + 5 minutes
        """
        return timezone.now() + timedelta(minutes=5) >= self.expires_at

    def refresh(
        self,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int
    ) -> None:
        """
        Update token with refreshed values from Spotify.

        Args:
            new_access_token: New Spotify access token
            new_refresh_token: New Spotify refresh token
            expires_in: Seconds until new access token expires

        Updates access_token, refresh_token, and expires_at atomically.
        """
        self.access_token = new_access_token
        self.refresh_token = new_refresh_token
        self.expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.save()
