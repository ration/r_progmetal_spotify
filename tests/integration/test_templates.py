"""Integration tests for template rendering and CSS."""

import pytest
from django.urls import reverse
from datetime import date
from catalog.models import Album, Artist


@pytest.mark.django_db
class TestResponsiveGridLayout:
    """Test responsive grid layout CSS and rendering."""

    def test_album_grid_container_present(self, client):
        """Test that album grid container with proper classes is rendered."""
        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Check for grid container or empty state (which is still valid)
        assert (
            'class="album-grid"' in content
            or 'id="album-tiles"' in content
            or "No Albums Yet" in content
        )

    def test_album_tile_structure(self, client):
        """Test that album tiles have proper structure for responsive layout."""
        artist = Artist.objects.create(name="Karnivool", country="Australia")
        Album.objects.create(
            spotify_album_id="9" * 22,
            name="Sound Awake",
            artist=artist,
            release_date=date(2009, 6, 5),
            spotify_url="https://open.spotify.com/album/" + "9" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Check for tile structure
        assert "album-tile" in content or "card" in content
        assert "Sound Awake" in content
        assert "Karnivool" in content

    def test_album_cover_image_lazy_loading(self, client):
        """Test that album cover images use lazy loading attribute."""
        artist = Artist.objects.create(name="Caligula's Horse", country="Australia")
        Album.objects.create(
            spotify_album_id="A" * 22,
            name="In Contact",
            artist=artist,
            cover_art_url="https://example.com/incontact.jpg",
            release_date=date(2017, 9, 15),
            spotify_url="https://open.spotify.com/album/" + "A" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Check for lazy loading
        assert 'loading="lazy"' in content

    def test_placeholder_image_fallback(self, client):
        """Test that albums without cover art show placeholder."""
        artist = Artist.objects.create(name="Protest the Hero", country="Canada")
        Album.objects.create(
            spotify_album_id="B" * 22,
            name="Fortress",
            artist=artist,
            cover_art_url=None,  # No cover art
            release_date=date(2008, 1, 29),
            spotify_url="https://open.spotify.com/album/" + "B" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Check for placeholder image path
        assert "placeholder-album" in content

    def test_responsive_meta_viewport(self, client):
        """Test that viewport meta tag is present for mobile responsiveness."""
        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        assert 'name="viewport"' in content
        assert 'width=device-width' in content
