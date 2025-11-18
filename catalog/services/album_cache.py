"""
Album cache service for just-in-time Spotify API loading.

This module provides caching functionality for Spotify cover art and metadata,
enabling on-demand loading instead of eager fetching during import.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from catalog.models import Album

logger = logging.getLogger(__name__)

# Regex pattern for extracting Spotify album ID from URL
SPOTIFY_ALBUM_URL_PATTERN = re.compile(r"open\.spotify\.com/album/([a-zA-Z0-9]{22})")


def extract_spotify_album_id(spotify_url: str) -> Optional[str]:
    """
    Extract Spotify album ID from a Spotify URL.

    Args:
        spotify_url: Full Spotify album URL (e.g., "https://open.spotify.com/album/abc123...")

    Returns:
        str: 22-character Spotify album ID if found, None otherwise

    Examples:
        >>> extract_spotify_album_id("https://open.spotify.com/album/1234567890123456789012")
        "1234567890123456789012"
        >>> extract_spotify_album_id("invalid-url")
        None
    """
    if not spotify_url:
        return None

    match = SPOTIFY_ALBUM_URL_PATTERN.search(spotify_url)
    if match:
        return match.group(1)

    logger.warning(f"Could not extract Spotify album ID from URL: {spotify_url}")
    return None


def get_cached_cover_url(album_id: int) -> Optional[str]:
    """
    Check if cover art URL is cached for an album.

    Args:
        album_id: Album primary key

    Returns:
        str: Cached cover art URL if available, None otherwise
    """
    try:
        album = Album.objects.filter(id=album_id).values("spotify_cover_url").first()
        if album and album["spotify_cover_url"]:
            logger.debug(f"Cache hit for album {album_id} cover art")
            return album["spotify_cover_url"]

        logger.debug(f"Cache miss for album {album_id} cover art")
        return None

    except Album.DoesNotExist:
        logger.warning(f"Album {album_id} does not exist")
        return None


@transaction.atomic
def cache_cover_url(album_id: int, cover_url: str) -> None:
    """
    Cache cover art URL for an album with database-level locking.

    Uses select_for_update() to prevent duplicate API calls when multiple
    users request cover art for the same album simultaneously.

    Args:
        album_id: Album primary key
        cover_url: Spotify cover art URL to cache

    Raises:
        Album.DoesNotExist: If album with given ID doesn't exist
    """
    # Acquire row-level lock
    album = Album.objects.select_for_update().get(id=album_id)

    # Check if another request already cached it
    if album.spotify_cover_url:
        logger.debug(f"Album {album_id} cover art already cached by another request")
        return

    # Update cache
    album.spotify_cover_url = cover_url
    album.spotify_cover_cached_at = timezone.now()
    album.save(update_fields=["spotify_cover_url", "spotify_cover_cached_at"])

    logger.info(f"Cached cover art for album {album_id}")


def get_cached_metadata(album_id: int) -> Optional[dict]:
    """
    Check if detailed metadata is cached for an album.

    Args:
        album_id: Album primary key

    Returns:
        dict: Cached metadata JSON if available, None otherwise
    """
    try:
        album = Album.objects.filter(id=album_id).values(
            "spotify_metadata_json"
        ).first()
        if album and album["spotify_metadata_json"]:
            logger.debug(f"Cache hit for album {album_id} metadata")
            return album["spotify_metadata_json"]

        logger.debug(f"Cache miss for album {album_id} metadata")
        return None

    except Album.DoesNotExist:
        logger.warning(f"Album {album_id} does not exist")
        return None


@transaction.atomic
def cache_metadata(album_id: int, metadata: dict) -> None:
    """
    Cache detailed metadata for an album with database-level locking.

    Uses select_for_update() to prevent duplicate API calls when multiple
    users request metadata for the same album simultaneously.

    Args:
        album_id: Album primary key
        metadata: Spotify metadata dictionary to cache

    Raises:
        Album.DoesNotExist: If album with given ID doesn't exist
    """
    # Acquire row-level lock
    album = Album.objects.select_for_update().get(id=album_id)

    # Check if another request already cached it
    if album.spotify_metadata_json:
        logger.debug(f"Album {album_id} metadata already cached by another request")
        return

    # Update cache
    album.spotify_metadata_json = metadata
    album.spotify_metadata_cached_at = timezone.now()
    album.save(update_fields=["spotify_metadata_json", "spotify_metadata_cached_at"])

    logger.info(f"Cached metadata for album {album_id}")
