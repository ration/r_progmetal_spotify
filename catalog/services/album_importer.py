"""
Album importer service.

This module coordinates importing album data from Google Sheets and enriching it
with metadata from Spotify API. It handles creating/updating Django model instances.
"""

import logging
from typing import Dict, Tuple, Optional
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
        self,
        sheets_service: GoogleSheetsService,
        spotify_client: Optional[SpotifyClient] = None,
    ):
        """
        Initialize the album importer.

        Args:
            sheets_service: Configured GoogleSheetsService instance
            spotify_client: Configured SpotifyClient instance (optional for just-in-time mode)
        """
        self.sheets_service = sheets_service
        self.spotify_client = spotify_client
        logger.info("Initialized AlbumImporter")

    def import_albums(
        self, limit: int = None, skip_existing: bool = True, skip_spotify: bool = True
    ) -> Tuple[int, int, int]:
        """
        Import albums from Google Sheets and optionally enrich with Spotify metadata.

        Args:
            limit: Maximum number of albums to import (None for all)
            skip_existing: If True, skip albums that already exist in database
            skip_spotify: If True, skip Spotify API calls (just-in-time loading mode)

        Returns:
            Tuple of (created_count, updated_count, skipped_count)

        Raises:
            Exception: If import process fails critically
        """
        mode = "JIT (skip Spotify)" if skip_spotify else "eager (fetch Spotify)"
        logger.info(
            f"Starting album import (limit={limit}, skip_existing={skip_existing}, mode={mode})"
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
                    # Use album_cache for extraction (consistent with JIT loading)
                    from catalog.services.album_cache import extract_spotify_album_id

                    album_id = extract_spotify_album_id(sheets_data["spotify_url"])
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

                    # Conditionally fetch metadata from Spotify
                    spotify_metadata = None
                    if not skip_spotify:
                        if not self.spotify_client:
                            logger.error(
                                "Spotify client not initialized but skip_spotify=False"
                            )
                            skipped_count += 1
                            continue

                        spotify_metadata = self.spotify_client.get_album_metadata(
                            album_id
                        )
                        if not spotify_metadata:
                            logger.warning(
                                f"Could not fetch Spotify metadata for album {album_id}"
                            )
                            skipped_count += 1
                            continue

                    # Import album with combined data
                    # If skip_spotify=True, spotify_metadata will be None
                    created = self._import_single_album(
                        sheets_data, spotify_metadata, album_id
                    )

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
    def _import_single_album(
        self, sheets_data: Dict, spotify_metadata: Optional[Dict], album_id: str
    ) -> bool:
        """
        Import a single album into the database.

        Args:
            sheets_data: Album data from Google Sheets
            spotify_metadata: Album metadata from Spotify API (None if skip_spotify=True)
            album_id: Spotify album ID extracted from URL

        Returns:
            True if album was created, False if it was updated
        """
        if spotify_metadata:
            # Full import mode: Use Spotify metadata
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

            # Map genres from Google Sheets (may be multiple, comma-separated)
            genres = self._map_genres(sheets_data.get("genre", ""))

            # Map vocal style from Google Sheets to our VocalStyle model
            vocal_style = self._map_vocal_style(sheets_data.get("vocal_style", ""))

            # Create or update album with Spotify metadata
            album, created = Album.objects.update_or_create(
                spotify_album_id=album_id,
                defaults={
                    "name": spotify_metadata["name"],
                    "artist": artist,
                    "vocal_style": vocal_style,
                    "release_date": spotify_metadata["release_date"],
                    "cover_art_url": spotify_metadata.get("cover_art_url", ""),
                    "spotify_url": spotify_metadata["spotify_url"],
                },
            )

            # Set ManyToMany genres relationship
            album.genres.set(genres)

            action = "Created" if created else "Updated"
            genre_names = ", ".join(g.name for g in genres)
            logger.debug(
                f"{action} album: {album.artist.name} - {album.name} "
                f"(Genres: {genre_names}, Released: {album.release_date})"
            )

        else:
            # JIT mode: Use only Google Sheets data (Spotify metadata will be loaded on-demand)
            # Get or create artist using only Google Sheets data
            artist, _ = Artist.objects.get_or_create(
                name=sheets_data["artist"],
                defaults={
                    "country": sheets_data.get("country", ""),
                },
            )

            # Map genres from Google Sheets (may be multiple, comma-separated)
            genres = self._map_genres(sheets_data.get("genre", ""))

            # Map vocal style from Google Sheets to our VocalStyle model
            vocal_style = self._map_vocal_style(sheets_data.get("vocal_style", ""))

            # Parse release date from Google Sheets
            # Combine tab year with release date (e.g., "January 15" + 2025 → 2025-01-15)
            release_date = None
            if sheets_data.get("release_date"):
                tab_year = sheets_data.get("tab_year")
                release_date = self.sheets_service.parse_release_date(
                    sheets_data["release_date"], tab_year
                )
                if release_date:
                    logger.debug(
                        f"Parsed release date: {sheets_data['release_date']} ({tab_year}) → {release_date}"
                    )

            # Create or update album with Google Sheets data only
            album, created = Album.objects.update_or_create(
                spotify_album_id=album_id,
                defaults={
                    "name": sheets_data["album"],
                    "artist": artist,
                    "vocal_style": vocal_style,
                    "release_date": release_date,  # Parsed from sheet + tab year
                    "cover_art_url": "",  # Will be fetched JIT when visible
                    "spotify_url": sheets_data["spotify_url"],
                },
            )

            # Set ManyToMany genres relationship
            album.genres.set(genres)

            action = "Created" if created else "Updated"
            genre_names = ", ".join(g.name for g in genres)
            release_info = f", Released: {album.release_date}" if album.release_date else ""
            logger.debug(
                f"{action} album (JIT mode): {album.artist.name} - {album.name} "
                f"(Genres: {genre_names}{release_info})"
            )

        return created

    def _map_genres(self, genre_text: str) -> list[Genre]:
        """
        Map genre text from Google Sheets to Genre model instances.

        The Google Sheets "Genre / Subgenres" field can contain:
        - Single genre: "Progressive Metal"
        - Multiple genres (comma-separated): "Black Metal, Mathcore"
        - Complex genre text: "Technical Death Metal"

        This method splits on commas and creates/finds a Genre instance for each part.

        Args:
            genre_text: Genre text from Google Sheets (may contain commas)

        Returns:
            List of Genre model instances (creates if don't exist)
        """
        if not genre_text:
            # Default to Progressive Metal for empty genres
            genre, _ = Genre.objects.get_or_create(
                name="Progressive Metal",
                defaults={"slug": slugify("Progressive Metal")},
            )
            return [genre]

        # Split on comma to handle multiple genres
        genre_names = [g.strip() for g in genre_text.split(",") if g.strip()]

        if not genre_names:
            # If no valid genres after splitting, default to Progressive Metal
            genre, _ = Genre.objects.get_or_create(
                name="Progressive Metal",
                defaults={"slug": slugify("Progressive Metal")},
            )
            return [genre]

        genres = []
        for genre_name in genre_names:
            # Try exact match first
            try:
                genre = Genre.objects.get(name__iexact=genre_name)
                genres.append(genre)
                continue
            except Genre.DoesNotExist:
                pass

            # Check if text contains any known genre as substring
            found = False
            for existing_genre in Genre.objects.all():
                if existing_genre.name.lower() in genre_name.lower():
                    genres.append(existing_genre)
                    found = True
                    break

            if found:
                continue

            # No match found - create new genre
            logger.info(
                f"Creating new genre: '{genre_name}' (no existing match found)"
            )
            genre, _ = Genre.objects.get_or_create(
                name=genre_name, defaults={"slug": slugify(genre_name)}
            )
            genres.append(genre)

        return genres

    def _map_vocal_style(self, vocal_style_text: str) -> VocalStyle:
        """
        Map vocal style text from Google Sheets to VocalStyle model instance.

        The Google Sheets "Vocal Style" field contains text like:
        "Clean", "Harsh", "Mixed", "Instrumental", etc.

        This method attempts to match or normalize the text to common vocal style patterns.
        If no match is found, creates a new VocalStyle with the provided text.

        Args:
            vocal_style_text: Vocal style text from Google Sheets

        Returns:
            VocalStyle model instance (creates if doesn't exist)
        """
        if not vocal_style_text:
            # Default to Mixed Vocals for empty vocal styles
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

        # Try fuzzy matching to standardize common variations
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

        # No match found - create new vocal style from the sheet data
        logger.info(
            f"Creating new vocal style: '{vocal_style_text}' (no existing match found)"
        )
        vocal_style, _ = VocalStyle.objects.get_or_create(
            name=vocal_style_text, defaults={"slug": slugify(vocal_style_text)}
        )
        return vocal_style

    def sync_albums(self, skip_spotify: bool = True) -> Tuple[int, int, int]:
        """
        Sync albums from Google Sheets with database.

        This method updates existing albums and adds new ones.
        Unlike import_albums with skip_existing=True, this will update
        existing albums with new metadata.

        Args:
            skip_spotify: If True, skip Spotify API calls (default: True)

        Returns:
            Tuple of (created_count, updated_count, skipped_count)
        """
        logger.info("Starting album sync (updating existing albums)")
        return self.import_albums(limit=None, skip_existing=False, skip_spotify=skip_spotify)
