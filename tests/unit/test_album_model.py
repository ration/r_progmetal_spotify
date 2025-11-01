"""Unit tests for Album model methods."""

import pytest
from datetime import date
from catalog.models import Album, Artist, Genre, VocalStyle


@pytest.mark.django_db
class TestAlbumModel:
    """Test Album model methods."""

    def test_album_str_with_release_date(self):
        """Test Album __str__ method includes year when release_date is set."""
        artist = Artist.objects.create(name="Opeth", country="Sweden")
        album = Album.objects.create(
            spotify_album_id="7ouMYWpwJ422jRcDASZB7P",
            name="Blackwater Park",
            artist=artist,
            release_date=date(2001, 2, 27),
            spotify_url="https://open.spotify.com/album/7ouMYWpwJ422jRcDASZB7P",
        )

        assert str(album) == "Opeth - Blackwater Park (2001)"

    def test_album_str_without_release_date(self):
        """Test Album __str__ method when release_date is None."""
        artist = Artist.objects.create(name="Dream Theater", country="USA")
        album = Album.objects.create(
            spotify_album_id="4FM5ITIOzjPOwNtDUfL0c3",
            name="Images and Words",
            artist=artist,
            release_date=None,
            spotify_url="https://open.spotify.com/album/4FM5ITIOzjPOwNtDUfL0c3",
        )

        assert str(album) == "Dream Theater - Images and Words"

    def test_get_cover_art_or_placeholder_with_cover_url(self):
        """Test get_cover_art_or_placeholder returns URL when cover_art_url is set."""
        artist = Artist.objects.create(name="Tool", country="USA")
        album = Album.objects.create(
            spotify_album_id="5l5m1hnH4punS1GQXgEi3T",
            name="Fear Inoculum",
            artist=artist,
            cover_art_url="https://i.scdn.co/image/ab67616d0000b2730b76ce6c408c9c1e3b99134f",
            spotify_url="https://open.spotify.com/album/5l5m1hnH4punS1GQXgEi3T",
        )

        assert album.get_cover_art_or_placeholder() == "https://i.scdn.co/image/ab67616d0000b2730b76ce6c408c9c1e3b99134f"

    def test_get_cover_art_or_placeholder_without_cover_url(self):
        """Test get_cover_art_or_placeholder returns placeholder when cover_art_url is None."""
        artist = Artist.objects.create(name="Mastodon", country="USA")
        album = Album.objects.create(
            spotify_album_id="0Lyr6OXxjHutNQKJXVxdJe",
            name="Leviathan",
            artist=artist,
            cover_art_url=None,
            spotify_url="https://open.spotify.com/album/0Lyr6OXxjHutNQKJXVxdJe",
        )

        assert album.get_cover_art_or_placeholder() == "/static/catalog/images/placeholder-album.svg"

    def test_get_cover_art_or_placeholder_with_empty_string(self):
        """Test get_cover_art_or_placeholder returns placeholder when cover_art_url is empty."""
        artist = Artist.objects.create(name="Gojira", country="France")
        album = Album.objects.create(
            spotify_album_id="2Kh43m04B1UkVcpcRa1Zug",
            name="From Mars to Sirius",
            artist=artist,
            cover_art_url="",
            spotify_url="https://open.spotify.com/album/2Kh43m04B1UkVcpcRa1Zug",
        )

        # Empty string is falsy, so should return placeholder
        assert album.get_cover_art_or_placeholder() == "/static/catalog/images/placeholder-album.svg"

    def test_formatted_release_date_full_date(self):
        """Test formatted_release_date with day precision (day != 1)."""
        artist = Artist.objects.create(name="Periphery", country="USA")
        album = Album.objects.create(
            spotify_album_id="5Mf7RMx4sXlprXNXZbNd9I",
            name="Periphery IV: Hail Stan",
            artist=artist,
            release_date=date(2019, 4, 5),  # Day is 5, not 1
            spotify_url="https://open.spotify.com/album/5Mf7RMx4sXlprXNXZbNd9I",
        )

        assert album.formatted_release_date() == "Apr 05, 2019"

    def test_formatted_release_date_month_precision(self):
        """Test formatted_release_date with month precision (day=1, month != 1)."""
        artist = Artist.objects.create(name="TesseracT", country="UK")
        album = Album.objects.create(
            spotify_album_id="5YcsxLIKNzpXCBmNE3DS4U",
            name="Sonder",
            artist=artist,
            release_date=date(2018, 4, 1),  # Day=1, Month=4
            spotify_url="https://open.spotify.com/album/5YcsxLIKNzpXCBmNE3DS4U",
        )

        assert album.formatted_release_date() == "April 2018"

    def test_formatted_release_date_year_precision(self):
        """Test formatted_release_date with year precision (day=1, month=1)."""
        artist = Artist.objects.create(name="Animals as Leaders", country="USA")
        album = Album.objects.create(
            spotify_album_id="6v5c8qoMZMcKgQkKrIl3EQ",
            name="The Joy of Motion",
            artist=artist,
            release_date=date(2014, 1, 1),  # Day=1, Month=1
            spotify_url="https://open.spotify.com/album/6v5c8qoMZMcKgQkKrIl3EQ",
        )

        assert album.formatted_release_date() == "2014"

    def test_formatted_release_date_no_date(self):
        """Test formatted_release_date when release_date is None."""
        artist = Artist.objects.create(name="Haken", country="UK")
        album = Album.objects.create(
            spotify_album_id="0Rqk9M4RwJWIiCBqhpLQsS",
            name="Vector",
            artist=artist,
            release_date=None,
            spotify_url="https://open.spotify.com/album/0Rqk9M4RwJWIiCBqhpLQsS",
        )

        assert album.formatted_release_date() == "Unknown"

    def test_album_ordering(self):
        """Test that albums are ordered by release_date DESC, then imported_at DESC."""
        artist = Artist.objects.create(name="Between the Buried and Me", country="USA")

        # Create albums with different release dates
        album1 = Album.objects.create(
            spotify_album_id="1" * 22,
            name="Colors",
            artist=artist,
            release_date=date(2007, 9, 18),
            spotify_url="https://open.spotify.com/album/" + "1" * 22,
        )
        album2 = Album.objects.create(
            spotify_album_id="2" * 22,
            name="Colors II",
            artist=artist,
            release_date=date(2021, 8, 20),
            spotify_url="https://open.spotify.com/album/" + "2" * 22,
        )
        album3 = Album.objects.create(
            spotify_album_id="3" * 22,
            name="The Great Misdirect",
            artist=artist,
            release_date=date(2009, 10, 27),
            spotify_url="https://open.spotify.com/album/" + "3" * 22,
        )

        # Query all albums - should be ordered newest first
        albums = list(Album.objects.all())
        assert albums[0].name == "Colors II"  # 2021
        assert albums[1].name == "The Great Misdirect"  # 2009
        assert albums[2].name == "Colors"  # 2007
