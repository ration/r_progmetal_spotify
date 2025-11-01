"""
Spotify API client service.

This module provides functionality to fetch album metadata from Spotify Web API using
spotipy library.
"""

import logging
import re
from typing import Dict, Optional
from datetime import datetime, date
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

logger = logging.getLogger(__name__)


class SpotifyClient:
    """
    Service for interacting with Spotify Web API.

    Uses Client Credentials Flow (no user authentication required) to fetch
    public album metadata.

    Attributes:
        client: Authenticated spotipy Spotify client
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Spotify API client.

        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret

        Raises:
            SpotifyException: If authentication fails
        """
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            self.client = Spotify(auth_manager=auth_manager)
            logger.info("Successfully initialized Spotify client")
        except SpotifyException as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            raise

    def extract_album_id(self, spotify_url: str) -> Optional[str]:
        """
        Extract Spotify album ID from URL.

        Spotify album URLs have format:
        https://open.spotify.com/album/{album_id}?si=...

        Args:
            spotify_url: Full Spotify album URL

        Returns:
            22-character Spotify album ID, or None if extraction fails
        """
        if not spotify_url:
            return None

        # Extract album ID using regex
        # Pattern matches: /album/{22-character-id}
        match = re.search(r'/album/([a-zA-Z0-9]{22})', spotify_url)
        if match:
            album_id = match.group(1)
            logger.debug(f"Extracted album ID {album_id} from URL {spotify_url}")
            return album_id

        logger.warning(f"Could not extract album ID from URL: {spotify_url}")
        return None

    def get_album_metadata(self, album_id: str) -> Optional[Dict]:
        """
        Fetch album metadata from Spotify API.

        Args:
            album_id: Spotify album ID (22 characters)

        Returns:
            Dictionary with album metadata:
            - album_id: Spotify album ID
            - name: Album title
            - artist_name: Primary artist name
            - artist_id: Spotify artist ID
            - release_date: Release date (date object or partial date string)
            - release_date_precision: "year", "month", or "day"
            - cover_art_url: URL to album cover art (640x640 if available)
            - spotify_url: Full Spotify album URL
            - total_tracks: Number of tracks on album

            Returns None if album not found or API error occurs.

        Raises:
            SpotifyException: If API request fails
        """
        try:
            logger.debug(f"Fetching metadata for album ID: {album_id}")
            album_data = self.client.album(album_id)

            # Extract primary artist (first artist in list)
            primary_artist = album_data['artists'][0] if album_data['artists'] else None
            if not primary_artist:
                logger.warning(f"Album {album_id} has no artists")
                return None

            # Parse release date based on precision
            release_date = self._parse_release_date(
                album_data.get('release_date', ''),
                album_data.get('release_date_precision', 'day')
            )

            # Get highest resolution cover art
            cover_art_url = None
            if album_data.get('images'):
                # Images are sorted by size (largest first)
                cover_art_url = album_data['images'][0]['url']

            metadata = {
                'album_id': album_data['id'],
                'name': album_data['name'],
                'artist_name': primary_artist['name'],
                'artist_id': primary_artist['id'],
                'release_date': release_date,
                'release_date_precision': album_data.get('release_date_precision', 'day'),
                'cover_art_url': cover_art_url,
                'spotify_url': album_data['external_urls']['spotify'],
                'total_tracks': album_data.get('total_tracks', 0)
            }

            logger.info(
                f"Successfully fetched metadata for '{metadata['name']}' "
                f"by {metadata['artist_name']}"
            )

            return metadata

        except SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"Album {album_id} not found on Spotify")
                return None
            logger.error(f"Spotify API error for album {album_id}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching album {album_id}: {e}")
            return None

    def _parse_release_date(
        self, date_str: str, precision: str
    ) -> Optional[date]:
        """
        Parse Spotify release date based on precision.

        Spotify returns dates in different precisions:
        - "day": YYYY-MM-DD (full date)
        - "month": YYYY-MM (year and month only)
        - "year": YYYY (year only)

        Args:
            date_str: Date string from Spotify API
            precision: Date precision ("day", "month", or "year")

        Returns:
            date object, or None if parsing fails.
            For partial dates (year/month only), defaults to first day of period.
        """
        if not date_str:
            return None

        try:
            if precision == 'day':
                # Full date: YYYY-MM-DD
                return datetime.strptime(date_str, '%Y-%m-%d').date()

            elif precision == 'month':
                # Year and month: YYYY-MM (default to first day of month)
                return datetime.strptime(date_str, '%Y-%m').date().replace(day=1)

            elif precision == 'year':
                # Year only: YYYY (default to January 1)
                return datetime.strptime(date_str, '%Y').date().replace(month=1, day=1)

            else:
                logger.warning(f"Unknown date precision: {precision}")
                return None

        except ValueError as e:
            logger.warning(f"Could not parse release date '{date_str}': {e}")
            return None

    def get_artist_metadata(self, artist_id: str) -> Optional[Dict]:
        """
        Fetch artist metadata from Spotify API.

        Args:
            artist_id: Spotify artist ID

        Returns:
            Dictionary with artist metadata:
            - artist_id: Spotify artist ID
            - name: Artist name
            - genres: List of genre strings
            - popularity: Popularity score (0-100)

            Returns None if artist not found or API error occurs.

        Raises:
            SpotifyException: If API request fails
        """
        try:
            logger.debug(f"Fetching metadata for artist ID: {artist_id}")
            artist_data = self.client.artist(artist_id)

            metadata = {
                'artist_id': artist_data['id'],
                'name': artist_data['name'],
                'genres': artist_data.get('genres', []),
                'popularity': artist_data.get('popularity', 0)
            }

            logger.info(f"Successfully fetched metadata for artist '{metadata['name']}'")
            return metadata

        except SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"Artist {artist_id} not found on Spotify")
                return None
            logger.error(f"Spotify API error for artist {artist_id}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching artist {artist_id}: {e}")
            return None
