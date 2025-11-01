"""Integration tests for album catalog views."""

import pytest
from django.urls import reverse
from datetime import date
from catalog.models import Album, Artist, Genre, VocalStyle


@pytest.mark.django_db
class TestAlbumListView:
    """Test album list view rendering and functionality."""

    def test_album_list_view_renders(self, client):
        """Test that album_list view renders successfully."""
        url = reverse("catalog:album-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "New Progressive Metal Releases" in response.content.decode()

    def test_album_list_view_displays_albums(self, client):
        """Test that album tiles display with all required fields."""
        # Create test data
        artist = Artist.objects.create(name="Meshuggah", country="Sweden")
        genre, _ = Genre.objects.get_or_create(name="Djent", defaults={"slug": "djent"})
        vocal_style, _ = VocalStyle.objects.get_or_create(
            name="Harsh Vocals", defaults={"slug": "harsh-vocals"}
        )

        album = Album.objects.create(
            spotify_album_id="4" * 22,
            name="ObZen",
            artist=artist,
            genre=genre,
            vocal_style=vocal_style,
            release_date=date(2008, 3, 7),
            cover_art_url="https://example.com/obzen.jpg",
            spotify_url="https://open.spotify.com/album/" + "4" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Verify all required fields are displayed
        assert "ObZen" in content
        assert "Meshuggah" in content
        assert "Djent" in content
        assert "Harsh Vocals" in content
        assert "Sweden" in content
        assert album.formatted_release_date() in content

    def test_album_list_view_empty_state(self, client):
        """Test that empty state message displays when no albums exist."""
        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        assert response.status_code == 200
        assert "No Albums Yet" in content
        assert "import_albums" in content

    def test_album_list_view_orders_by_newest_first(self, client):
        """Test that albums are displayed in reverse chronological order."""
        artist = Artist.objects.create(name="Leprous", country="Norway")

        # Create albums with different release dates
        album_old = Album.objects.create(
            spotify_album_id="5" * 22,
            name="Tall Poppy Syndrome",
            artist=artist,
            release_date=date(2009, 5, 22),
            spotify_url="https://open.spotify.com/album/" + "5" * 22,
        )
        album_new = Album.objects.create(
            spotify_album_id="6" * 22,
            name="Aphelion",
            artist=artist,
            release_date=date(2021, 8, 27),
            spotify_url="https://open.spotify.com/album/" + "6" * 22,
        )
        album_mid = Album.objects.create(
            spotify_album_id="7" * 22,
            name="Pitfalls",
            artist=artist,
            release_date=date(2019, 10, 25),
            spotify_url="https://open.spotify.com/album/" + "7" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url)
        content = response.content.decode()

        # Verify order by finding indices
        aphelion_pos = content.find("Aphelion")
        pitfalls_pos = content.find("Pitfalls")
        tall_poppy_pos = content.find("Tall Poppy Syndrome")

        assert aphelion_pos < pitfalls_pos < tall_poppy_pos

    def test_album_list_view_uses_select_related(self, client, django_assert_num_queries):
        """Test that view optimizes queries with select_related."""
        # Create test data with relationships
        artist = Artist.objects.create(name="Devin Townsend", country="Canada")
        genre, _ = Genre.objects.get_or_create(
            name="Progressive Metal", defaults={"slug": "progressive-metal"}
        )
        vocal_style, _ = VocalStyle.objects.get_or_create(
            name="Clean Vocals", defaults={"slug": "clean-vocals"}
        )

        for i in range(5):
            Album.objects.create(
                spotify_album_id=str(i) * 22,
                name=f"Album {i}",
                artist=artist,
                genre=genre,
                vocal_style=vocal_style,
                release_date=date(2020, 1, i + 1),
                spotify_url=f"https://open.spotify.com/album/{str(i) * 22}",
            )

        url = reverse("catalog:album-list")

        # Should use select_related to avoid N+1 queries
        # Expected queries: 1 for albums + related (due to select_related)
        with django_assert_num_queries(1):
            response = client.get(url)
            # Access the albums in the template rendering
            albums = response.context["albums"]
            # Access related fields to trigger potential N+1
            for album in albums:
                _ = album.artist.name
                _ = album.genre.name if album.genre else None
                _ = album.vocal_style.name if album.vocal_style else None

    def test_album_list_view_htmx_request(self, client):
        """Test that HTMX request returns fragment template."""
        artist = Artist.objects.create(name="Plini", country="Australia")
        Album.objects.create(
            spotify_album_id="8" * 22,
            name="Handmade Cities",
            artist=artist,
            release_date=date(2016, 10, 28),
            spotify_url="https://open.spotify.com/album/" + "8" * 22,
        )

        url = reverse("catalog:album-list")
        response = client.get(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        content = response.content.decode()

        # Fragment should contain album content but not full page chrome
        assert "Handmade Cities" in content
        assert "Plini" in content
        # Should NOT contain full page elements
        assert "<html" not in content
        assert "Progressive Metal Releases" not in content  # Header text
