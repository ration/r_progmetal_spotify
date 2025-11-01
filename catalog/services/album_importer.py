"""
Album importer service.

This module coordinates importing album data from Google Sheets and enriching it
with metadata from Spotify API. It handles creating/updating Django model instances.
"""

import logging
from typing import Dict, Tuple
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Artist, Album, Genre, VocalStyle
from catalog.services.google_sheets import GoogleSheetsService
from catalog.services.spotify_client import SpotifyClient

logger = logging.getLogger(__name__)


class AlbumImporter:
    """
    Service for importing and syncing album data from Google Sheets and Spotify.

    This service:
    1. Fetches album list from Google Sheets (with Spotify URLs)
    2. Enriches each album with metadata from Spotify API
    3. Creates or updates Django model instances (Artist, Album, Genre, VocalStyle)
    4. Handles genre and vocal style mapping

    Attributes:
        sheets_service: GoogleSheetsService instance
        spotify_client: SpotifyClient instance
    """

    def __init__(
        self, sheets_service: GoogleSheetsService, spotify_client: SpotifyClient
    ):
        """
        Initialize the album importer.

        Args:
            sheets_service: Configured GoogleSheetsService instance
            spotify_client: Configured SpotifyClient instance
        """
        self.sheets_service = sheets_service
        self.spotify_client = spotify_client
        logger.info("Initialized AlbumImporter")

    def import_albums(
        self, limit: int = None, skip_existing: bool = True
    ) -> Tuple[int, int, int]:
        """
        Import albums from Google Sheets and enrich with Spotify metadata.

        Args:
            limit: Maximum number of albums to import (None for all)
            skip_existing: If True, skip albums that already exist in database

        Returns:
            Tuple of (created_count, updated_count, skipped_count)

        Raises:
            Exception: If import process fails critically
        """
        logger.info(
            f"Starting album import (limit={limit}, skip_existing={skip_existing})"
        )

        try:
            # Fetch album data from Google Sheets
            sheets_albums = self.sheets_service.fetch_albums()
            logger.info(f"Fetched {len(sheets_albums)} albums from Google Sheets")

            if limit:
                sheets_albums = sheets_albums[:limit]
                logger.info(f"Limited to {limit} albums")

            created_count = 0
            updated_count = 0
            skipped_count = 0

            for idx, sheets_data in enumerate(sheets_albums, 1):
                try:
                    logger.debug(
                        f"Processing album {idx}/{len(sheets_albums)}: "
                        f"{sheets_data['artist']} - {sheets_data['album']}"
                    )

                    # Extract Spotify album ID from URL
                    album_id = self.spotify_client.extract_album_id(
                        sheets_data["spotify_url"]
                    )
                    if not album_id:
                        logger.warning(
                            f"Could not extract Spotify ID from URL: "
                            f"{sheets_data['spotify_url']}"
                        )
                        skipped_count += 1
                        continue

                    # Check if album already exists
                    if (
                        skip_existing
                        and Album.objects.filter(spotify_album_id=album_id).exists()
                    ):
                        logger.debug(f"Album {album_id} already exists, skipping")
                        skipped_count += 1
                        continue

                    # Fetch metadata from Spotify
                    spotify_metadata = self.spotify_client.get_album_metadata(album_id)
                    if not spotify_metadata:
                        logger.warning(
                            f"Could not fetch Spotify metadata for album {album_id}"
                        )
                        skipped_count += 1
                        continue

                    # Import album with combined data
                    created = self._import_single_album(sheets_data, spotify_metadata)

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to import album {sheets_data.get('artist')} - "
                        f"{sheets_data.get('album')}: {e}"
                    )
                    skipped_count += 1
                    continue

            logger.info(
                f"Album import complete: {created_count} created, "
                f"{updated_count} updated, {skipped_count} skipped"
            )

            return created_count, updated_count, skipped_count

        except Exception as e:
            logger.error(f"Album import failed: {e}")
            raise

    @transaction.atomic
    def _import_single_album(self, sheets_data: Dict, spotify_metadata: Dict) -> bool:
        """
        Import a single album into the database.

        Args:
            sheets_data: Album data from Google Sheets
            spotify_metadata: Album metadata from Spotify API

        Returns:
            True if album was created, False if it was updated
        """
        # Get or create artist
        artist, _ = Artist.objects.get_or_create(
            spotify_artist_id=spotify_metadata["artist_id"],
            defaults={
                "name": spotify_metadata["artist_name"],
                "country": sheets_data.get("country", ""),
            },
        )

        # Update artist country if we have new data and it's not already set
        if sheets_data.get("country") and not artist.country:
            artist.country = sheets_data["country"]
            artist.save()

        # Map genre from Google Sheets to our Genre model
        genre = self._map_genre(sheets_data.get("genre", ""))

        # Map vocal style from Google Sheets to our VocalStyle model
        vocal_style = self._map_vocal_style(sheets_data.get("vocal_style", ""))

        # Create or update album
        album, created = Album.objects.update_or_create(
            spotify_album_id=spotify_metadata["album_id"],
            defaults={
                "name": spotify_metadata["name"],
                "artist": artist,
                "genre": genre,
                "vocal_style": vocal_style,
                "release_date": spotify_metadata["release_date"],
                "cover_art_url": spotify_metadata.get("cover_art_url", ""),
                "spotify_url": spotify_metadata["spotify_url"],
            },
        )

        action = "Created" if created else "Updated"
        logger.debug(
            f"{action} album: {album.artist.name} - {album.name} ({album.release_date})"
        )

        return created

    def _map_genre(self, genre_text: str) -> Genre:
        """
        Map genre text from Google Sheets to Genre model instance.

        The Google Sheets "Genre / Subgenres" field contains free text like:
        "Progressive Metal", "Technical Death Metal", etc.

        This method attempts to match the text to existing Genre entries.
        If no match is found, defaults to "Progressive Metal".

        Args:
            genre_text: Genre text from Google Sheets

        Returns:
            Genre model instance (creates if doesn't exist)
        """
        if not genre_text:
            # Default to Progressive Metal
            genre, _ = Genre.objects.get_or_create(
                name="Progressive Metal",
                defaults={"slug": slugify("Progressive Metal")},
            )
            return genre

        # Try exact match first
        try:
            return Genre.objects.get(name__iexact=genre_text)
        except Genre.DoesNotExist:
            pass

        # Try matching first part (before comma)
        first_genre = genre_text.split(",")[0].strip()
        try:
            return Genre.objects.get(name__iexact=first_genre)
        except Genre.DoesNotExist:
            pass

        # Check if text contains any known genre as substring
        for genre in Genre.objects.all():
            if genre.name.lower() in genre_text.lower():
                return genre

        # Default to Progressive Metal if no match found
        logger.debug(
            f"No genre match for '{genre_text}', defaulting to Progressive Metal"
        )
        genre, _ = Genre.objects.get_or_create(
            name="Progressive Metal", defaults={"slug": slugify("Progressive Metal")}
        )
        return genre

    def _map_vocal_style(self, vocal_style_text: str) -> VocalStyle:
        """
        Map vocal style text from Google Sheets to VocalStyle model instance.

        The Google Sheets "Vocal Style" field contains text like:
        "Clean", "Harsh", "Mixed", "Instrumental", etc.

        Args:
            vocal_style_text: Vocal style text from Google Sheets

        Returns:
            VocalStyle model instance (creates if doesn't exist)
        """
        if not vocal_style_text:
            # Default to Mixed Vocals
            vocal_style, _ = VocalStyle.objects.get_or_create(
                name="Mixed Vocals (Clean & Harsh)",
                defaults={"slug": slugify("Mixed Vocals (Clean & Harsh)")},
            )
            return vocal_style

        # Normalize text for matching
        normalized = vocal_style_text.strip().lower()

        # Try exact match
        try:
            return VocalStyle.objects.get(name__iexact=vocal_style_text)
        except VocalStyle.DoesNotExist:
            pass

        # Try fuzzy matching
        if "instrumental" in normalized or "no vocal" in normalized:
            vocal_style, _ = VocalStyle.objects.get_or_create(
                name="Instrumental (No Vocals)",
                defaults={"slug": slugify("Instrumental (No Vocals)")},
            )
            return vocal_style

        if "mixed" in normalized:
            vocal_style, _ = VocalStyle.objects.get_or_create(
                name="Mixed Vocals (Clean & Harsh)",
                defaults={"slug": slugify("Mixed Vocals (Clean & Harsh)")},
            )
            return vocal_style

        if "clean" in normalized:
            vocal_style, _ = VocalStyle.objects.get_or_create(
                name="Clean Vocals", defaults={"slug": slugify("Clean Vocals")}
            )
            return vocal_style

        if "harsh" in normalized or "scream" in normalized or "growl" in normalized:
            vocal_style, _ = VocalStyle.objects.get_or_create(
                name="Harsh Vocals", defaults={"slug": slugify("Harsh Vocals")}
            )
            return vocal_style

        # Default to Mixed if no match found
        logger.debug(
            f"No vocal style match for '{vocal_style_text}', defaulting to Mixed Vocals"
        )
        vocal_style, _ = VocalStyle.objects.get_or_create(
            name="Mixed Vocals (Clean & Harsh)",
            defaults={"slug": slugify("Mixed Vocals (Clean & Harsh)")},
        )
        return vocal_style

    def sync_albums(self) -> Tuple[int, int, int]:
        """
        Sync albums from Google Sheets with database.

        This method updates existing albums and adds new ones.
        Unlike import_albums with skip_existing=True, this will update
        existing albums with new metadata.

        Returns:
            Tuple of (created_count, updated_count, skipped_count)
        """
        logger.info("Starting album sync (updating existing albums)")
        return self.import_albums(limit=None, skip_existing=False)
