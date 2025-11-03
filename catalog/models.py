"""
Django models for the Album Catalog application.

This module defines the data models for storing album, artist, genre, and vocal style
information. Album data is sourced from Google Sheets CSV and enriched via Spotify API.
"""

from __future__ import annotations
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
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        """Return genre name."""
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_albums_count(self) -> int:
        """Return count of albums in this genre."""
        return self.album_set.count()  # type: ignore[attr-defined]


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
        genre: Foreign key to Genre model (optional)
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
    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="album_set",
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

    class Meta:
        ordering = ["-release_date", "-imported_at"]
        indexes = [
            models.Index(fields=["spotify_album_id"]),
            models.Index(fields=["-release_date"]),
            models.Index(fields=["artist", "genre", "vocal_style"]),
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
