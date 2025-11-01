"""
Tests for Spotify API client service.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch
from spotipy.exceptions import SpotifyException

from catalog.services.spotify_client import SpotifyClient


@pytest.fixture
def mock_spotify_client():
    """Create SpotifyClient with mocked spotipy client."""
    with patch('catalog.services.spotify_client.Spotify') as mock_spotify_class:
        mock_client = Mock()
        mock_spotify_class.return_value = mock_client

        client = SpotifyClient.__new__(SpotifyClient)
        client.client = mock_client

        yield client


class TestSpotifyClient:
    """Tests for SpotifyClient class."""

    def test_initialization_success(self):
        """Test successful Spotify client initialization."""
        with patch('catalog.services.spotify_client.Spotify') as mock_spotify:
            mock_spotify.return_value = Mock()

            client = SpotifyClient('test_id', 'test_secret')

            assert client.client is not None
            mock_spotify.assert_called_once()

    def test_initialization_failure(self):
        """Test Spotify client initialization failure."""
        with patch('catalog.services.spotify_client.Spotify') as mock_spotify:
            mock_spotify.side_effect = SpotifyException(
                400, -1, 'Authentication failed'
            )

            with pytest.raises(SpotifyException):
                SpotifyClient('invalid_id', 'invalid_secret')

    def test_extract_album_id_standard_url(self, mock_spotify_client):
        """Test extracting album ID from standard Spotify URL."""
        url = "https://open.spotify.com/album/1bDkXZkb0ASVCz1NXQKiYh"

        album_id = mock_spotify_client.extract_album_id(url)

        assert album_id == "1bDkXZkb0ASVCz1NXQKiYh"
        assert len(album_id) == 22

    def test_extract_album_id_url_with_query_params(self, mock_spotify_client):
        """Test extracting album ID from URL with query parameters."""
        url = "https://open.spotify.com/album/1bDkXZkb0ASVCz1NXQKiYh?si=r2jEcYuCQri36p9oakdK6g"

        album_id = mock_spotify_client.extract_album_id(url)

        assert album_id == "1bDkXZkb0ASVCz1NXQKiYh"

    def test_extract_album_id_invalid_url(self, mock_spotify_client):
        """Test extracting album ID from invalid URL returns None."""
        url = "https://example.com/not-a-spotify-url"

        album_id = mock_spotify_client.extract_album_id(url)

        assert album_id is None

    def test_extract_album_id_empty_url(self, mock_spotify_client):
        """Test extracting album ID from empty URL returns None."""
        album_id = mock_spotify_client.extract_album_id("")

        assert album_id is None

    def test_extract_album_id_none(self, mock_spotify_client):
        """Test extracting album ID from None returns None."""
        album_id = mock_spotify_client.extract_album_id(None)

        assert album_id is None

    def test_get_album_metadata_success(self, mock_spotify_client):
        """Test fetching album metadata successfully."""
        mock_spotify_client.client.album.return_value = {
            'id': '1bDkXZkb0ASVCz1NXQKiYh',
            'name': 'Corporeal Furnace',
            'artists': [
                {'name': 'Estuarine', 'id': 'artist123'}
            ],
            'release_date': '2025-01-01',
            'release_date_precision': 'day',
            'images': [
                {'url': 'https://i.scdn.co/image/abc123', 'height': 640, 'width': 640}
            ],
            'external_urls': {
                'spotify': 'https://open.spotify.com/album/1bDkXZkb0ASVCz1NXQKiYh'
            },
            'total_tracks': 10
        }

        metadata = mock_spotify_client.get_album_metadata('1bDkXZkb0ASVCz1NXQKiYh')

        assert metadata is not None
        assert metadata['album_id'] == '1bDkXZkb0ASVCz1NXQKiYh'
        assert metadata['name'] == 'Corporeal Furnace'
        assert metadata['artist_name'] == 'Estuarine'
        assert metadata['artist_id'] == 'artist123'
        assert metadata['release_date'] == date(2025, 1, 1)
        assert metadata['cover_art_url'] == 'https://i.scdn.co/image/abc123'
        assert metadata['total_tracks'] == 10

    def test_get_album_metadata_not_found(self, mock_spotify_client):
        """Test fetching album metadata for non-existent album."""
        mock_spotify_client.client.album.side_effect = SpotifyException(
            404, -1, 'Album not found'
        )

        metadata = mock_spotify_client.get_album_metadata('invalid_id')

        assert metadata is None

    def test_get_album_metadata_no_artists(self, mock_spotify_client):
        """Test fetching album metadata with no artists returns None."""
        mock_spotify_client.client.album.return_value = {
            'id': 'test123',
            'name': 'Test Album',
            'artists': [],
            'release_date': '2025-01-01',
            'release_date_precision': 'day'
        }

        metadata = mock_spotify_client.get_album_metadata('test123')

        assert metadata is None

    def test_get_album_metadata_no_images(self, mock_spotify_client):
        """Test fetching album metadata with no cover art."""
        mock_spotify_client.client.album.return_value = {
            'id': 'test123',
            'name': 'Test Album',
            'artists': [{'name': 'Test Artist', 'id': 'artist123'}],
            'release_date': '2025-01-01',
            'release_date_precision': 'day',
            'images': [],
            'external_urls': {'spotify': 'https://open.spotify.com/album/test123'},
            'total_tracks': 5
        }

        metadata = mock_spotify_client.get_album_metadata('test123')

        assert metadata is not None
        assert metadata['cover_art_url'] is None

    def test_parse_release_date_day_precision(self, mock_spotify_client):
        """Test parsing release date with day precision."""
        result = mock_spotify_client._parse_release_date('2025-01-15', 'day')

        assert result == date(2025, 1, 15)

    def test_parse_release_date_month_precision(self, mock_spotify_client):
        """Test parsing release date with month precision."""
        result = mock_spotify_client._parse_release_date('2025-01', 'month')

        assert result == date(2025, 1, 1)

    def test_parse_release_date_year_precision(self, mock_spotify_client):
        """Test parsing release date with year precision."""
        result = mock_spotify_client._parse_release_date('2025', 'year')

        assert result == date(2025, 1, 1)

    def test_parse_release_date_invalid(self, mock_spotify_client):
        """Test parsing invalid release date returns None."""
        result = mock_spotify_client._parse_release_date('invalid', 'day')

        assert result is None

    def test_parse_release_date_empty(self, mock_spotify_client):
        """Test parsing empty release date returns None."""
        result = mock_spotify_client._parse_release_date('', 'day')

        assert result is None

    def test_get_artist_metadata_success(self, mock_spotify_client):
        """Test fetching artist metadata successfully."""
        mock_spotify_client.client.artist.return_value = {
            'id': 'artist123',
            'name': 'Estuarine',
            'genres': ['progressive metal', 'death metal'],
            'popularity': 45
        }

        metadata = mock_spotify_client.get_artist_metadata('artist123')

        assert metadata is not None
        assert metadata['artist_id'] == 'artist123'
        assert metadata['name'] == 'Estuarine'
        assert metadata['genres'] == ['progressive metal', 'death metal']
        assert metadata['popularity'] == 45

    def test_get_artist_metadata_not_found(self, mock_spotify_client):
        """Test fetching artist metadata for non-existent artist."""
        mock_spotify_client.client.artist.side_effect = SpotifyException(
            404, -1, 'Artist not found'
        )

        metadata = mock_spotify_client.get_artist_metadata('invalid_id')

        assert metadata is None

    def test_get_artist_metadata_no_genres(self, mock_spotify_client):
        """Test fetching artist metadata with no genres."""
        mock_spotify_client.client.artist.return_value = {
            'id': 'artist123',
            'name': 'Test Artist',
            'genres': [],
            'popularity': 30
        }

        metadata = mock_spotify_client.get_artist_metadata('artist123')

        assert metadata is not None
        assert metadata['genres'] == []
