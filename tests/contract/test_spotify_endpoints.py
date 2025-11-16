"""
Contract tests for Spotify JIT loading endpoints.

These tests verify the API contract for cover art and metadata endpoints.
"""

import pytest
from django.urls import reverse
from unittest.mock import patch, Mock
from catalog.models import Album, Artist
from spotipy.exceptions import SpotifyException


@pytest.mark.django_db
class TestAlbumCoverArtEndpoint:
    """Contract tests for GET /catalog/album/<id>/cover-art/ endpoint."""

    @pytest.fixture
    def test_album(self):
        """Create a test album with Spotify URL."""
        artist = Artist.objects.create(name="Test Artist", country="US")
        album = Album.objects.create(
            spotify_album_id="1234567890123456789012",
            name="Test Album",
            artist=artist,
            spotify_url="https://open.spotify.com/album/1234567890123456789012",
        )
        return album

    def test_cover_art_endpoint_exists(self, client, test_album):
        """Test that the cover art endpoint exists and returns 200."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        with patch('catalog.views.SpotifyClient') as mock_spotify:
            mock_client = Mock()
            mock_client.fetch_album_cover.return_value = "https://i.scdn.co/image/test.jpg"
            mock_spotify.return_value = mock_client

            response = client.get(url)

        assert response.status_code == 200

    def test_cover_art_html_response_format(self, client, test_album):
        """Test that HTML response contains <img> tag with cover art."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        with patch('catalog.views.SpotifyClient') as mock_spotify:
            mock_client = Mock()
            mock_client.fetch_album_cover.return_value = "https://i.scdn.co/image/test.jpg"
            mock_spotify.return_value = mock_client

            response = client.get(url)
            content = response.content.decode()

        assert response.status_code == 200
        assert '<img' in content
        assert 'https://i.scdn.co/image/test.jpg' in content
        assert test_album.name in content

    def test_cover_art_json_response_format(self, client, test_album):
        """Test that JSON response format contains cover_url field."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        with patch('catalog.views.SpotifyClient') as mock_spotify:
            mock_client = Mock()
            mock_client.fetch_album_cover.return_value = "https://i.scdn.co/image/test.jpg"
            mock_spotify.return_value = mock_client

            response = client.get(url, {"format": "json"})

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

        data = response.json()
        assert 'cover_url' in data
        assert data['cover_url'] == "https://i.scdn.co/image/test.jpg"
        assert 'cached' in data

    def test_cover_art_404_for_nonexistent_album(self, client):
        """Test that endpoint returns 404 for non-existent album."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": 99999})
        response = client.get(url)

        assert response.status_code == 404

    def test_cover_art_rate_limit_error_handling(self, client, test_album):
        """Test that rate limit errors return appropriate placeholder."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        with patch('catalog.views.SpotifyClient') as mock_spotify:
            mock_client = Mock()
            mock_client.fetch_album_cover.side_effect = SpotifyException(
                429, -1, 'Rate limit exceeded', headers={'Retry-After': '30'}
            )
            mock_spotify.return_value = mock_client

            response = client.get(url)
            content = response.content.decode()

        # Should return 200 with placeholder, not 429 error
        assert response.status_code == 200
        assert 'placeholder' in content.lower() or 'skeleton' in content.lower()

    def test_cover_art_api_failure_handling(self, client, test_album):
        """Test that API failures return unavailable placeholder."""
        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        with patch('catalog.views.SpotifyClient') as mock_spotify:
            mock_client = Mock()
            mock_client.fetch_album_cover.side_effect = Exception("API Error")
            mock_spotify.return_value = mock_client

            response = client.get(url)
            content = response.content.decode()

        # Should return 200 with placeholder, not 500 error
        assert response.status_code == 200
        assert 'unavailable' in content.lower() or 'placeholder' in content.lower()

    def test_cover_art_missing_spotify_url(self, client):
        """Test that albums without Spotify URL return no-spotify placeholder."""
        artist = Artist.objects.create(name="Test Artist", country="US")
        album = Album.objects.create(
            spotify_album_id="",
            name="Test Album",
            artist=artist,
            spotify_url="",
        )

        url = reverse("catalog:album-cover-art", kwargs={"album_id": album.id})
        response = client.get(url)
        content = response.content.decode()

        assert response.status_code == 200
        assert 'spotify' in content.lower() or 'unavailable' in content.lower()

    def test_cover_art_cached_response(self, client, test_album):
        """Test that cached cover art is returned without API call."""
        # Pre-populate cache
        test_album.spotify_cover_url = "https://i.scdn.co/image/cached.jpg"
        test_album.save()

        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})

        # No mock needed - should use cached value
        response = client.get(url)
        content = response.content.decode()

        assert response.status_code == 200
        assert 'https://i.scdn.co/image/cached.jpg' in content

    def test_cover_art_json_cached_response(self, client, test_album):
        """Test that JSON response indicates cache hit."""
        # Pre-populate cache
        test_album.spotify_cover_url = "https://i.scdn.co/image/cached.jpg"
        test_album.save()

        url = reverse("catalog:album-cover-art", kwargs={"album_id": test_album.id})
        response = client.get(url, {"format": "json"})

        data = response.json()
        assert data['cached'] is True
        assert data['cover_url'] == "https://i.scdn.co/image/cached.jpg"
