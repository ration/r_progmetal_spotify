"""
Unit tests for genre and vocal style mapping functionality.

Tests the dynamic creation of genres and vocal styles from Google Sheets data.
"""

import pytest
from catalog.services.album_importer import AlbumImporter
from catalog.services.google_sheets import GoogleSheetsService
from catalog.models import Genre, VocalStyle


@pytest.mark.django_db
class TestGenreMapping:
    """Tests for genre mapping from Google Sheets to database."""

    @pytest.fixture
    def importer(self):
        """Create AlbumImporter instance for testing."""
        sheets_service = GoogleSheetsService("https://example.com")
        return AlbumImporter(sheets_service, spotify_client=None)

    def test_creates_new_genre_when_no_match(self, importer):
        """Test that new genres are created when they don't exist."""
        genres = importer._map_genres("Experimental Big Band")

        assert genres is not None
        assert len(genres) == 1
        assert genres[0].name == "Experimental Big Band"
        assert genres[0].slug == "experimental-big-band"

        # Verify it's in the database
        assert Genre.objects.filter(name="Experimental Big Band").exists()

    def test_finds_existing_genre_exact_match(self, importer):
        """Test that existing genres are found with exact match."""
        # Create genre first (use get_or_create in case seed data exists)
        Genre.objects.get_or_create(name="Djent", defaults={"slug": "djent"})

        # Map should find existing genre
        genres = importer._map_genres("Djent")

        assert len(genres) == 1
        assert genres[0].name == "Djent"

        # Should only have one Djent genre
        assert Genre.objects.filter(name="Djent").count() == 1

    def test_genre_matching_case_insensitive(self, importer):
        """Test that genre matching is case-insensitive."""
        # Create genre with specific case
        Genre.objects.create(name="Death Metal", slug="death-metal")

        # Should find with different case
        genres1 = importer._map_genres("death metal")
        genres2 = importer._map_genres("DEATH METAL")
        genres3 = importer._map_genres("Death Metal")

        assert len(genres1) == 1 and genres1[0].name == "Death Metal"
        assert len(genres2) == 1 and genres2[0].name == "Death Metal"
        assert len(genres3) == 1 and genres3[0].name == "Death Metal"

        # Should still only have one
        assert Genre.objects.filter(name__iexact="Death Metal").count() == 1

    def test_empty_genre_defaults_to_progressive_metal(self, importer):
        """Test that empty genre text defaults to Progressive Metal."""
        genres = importer._map_genres("")
        assert len(genres) == 1
        assert genres[0].name == "Progressive Metal"

        genres_none = importer._map_genres(None)
        assert len(genres_none) == 1
        assert genres_none[0].name == "Progressive Metal"

    def test_genre_substring_matching(self, importer):
        """Test that genres can be matched by substring."""
        # Create a known genre (use get_or_create in case seed data exists)
        Genre.objects.get_or_create(
            name="Progressive Metal", defaults={"slug": "progressive-metal"}
        )

        # Should match genres containing "Progressive Metal"
        genres = importer._map_genres("Technical Progressive Metal")
        assert len(genres) == 1
        assert genres[0].name == "Progressive Metal"

    def test_multiple_unique_genres_created(self, importer):
        """Test that multiple unique genres are created correctly."""
        genres_to_create = [
            "Djent",
            "Math Rock",
            "Post-Rock",
            "Experimental Big Band"
        ]

        created_genres = []
        for genre_text in genres_to_create:
            genres = importer._map_genres(genre_text)
            assert len(genres) == 1
            created_genres.append(genres[0])

        # All genres should be created
        assert len(created_genres) == 4
        assert all(g.name in genres_to_create for g in created_genres)

        # Each should exist in database
        for genre_name in genres_to_create:
            assert Genre.objects.filter(name=genre_name).exists()

    def test_comma_separated_multi_genre_parsing(self, importer):
        """Test that comma-separated genres are split and parsed correctly."""
        # Test case from user: "Black Metal, Mathcore" for Theophonos
        genres = importer._map_genres("Black Metal, Mathcore")

        assert len(genres) == 2
        assert genres[0].name == "Black Metal"
        assert genres[1].name == "Mathcore"

        # Verify both are in database
        assert Genre.objects.filter(name="Black Metal").exists()
        assert Genre.objects.filter(name="Mathcore").exists()

    def test_comma_separated_with_whitespace(self, importer):
        """Test that comma-separated genres handle extra whitespace."""
        genres = importer._map_genres("Avant-Garde metal,  Harsh Electronic,Djent")

        assert len(genres) == 3
        assert genres[0].name == "Avant-Garde metal"
        assert genres[1].name == "Harsh Electronic"
        assert genres[2].name == "Djent"

    def test_comma_separated_with_existing_and_new_genres(self, importer):
        """Test mixed comma-separated list with existing and new genres."""
        # Create one genre in advance
        Genre.objects.create(name="Black Metal", slug="black-metal")

        # Parse list with one existing, one new
        genres = importer._map_genres("Black Metal, Screamo")

        assert len(genres) == 2
        assert genres[0].name == "Black Metal"
        assert genres[1].name == "Screamo"

        # Should only have one Black Metal (not duplicated)
        assert Genre.objects.filter(name="Black Metal").count() == 1


@pytest.mark.django_db
class TestVocalStyleMapping:
    """Tests for vocal style mapping from Google Sheets to database."""

    @pytest.fixture
    def importer(self):
        """Create AlbumImporter instance for testing."""
        sheets_service = GoogleSheetsService("https://example.com")
        return AlbumImporter(sheets_service, spotify_client=None)

    def test_creates_new_vocal_style_when_no_match(self, importer):
        """Test that new vocal styles are created when they don't exist."""
        vocal_style = importer._map_vocal_style("Operatic Vocals")

        assert vocal_style is not None
        assert vocal_style.name == "Operatic Vocals"
        assert vocal_style.slug == "operatic-vocals"

        # Verify it's in the database
        assert VocalStyle.objects.filter(name="Operatic Vocals").exists()

    def test_fuzzy_matching_for_clean_vocals(self, importer):
        """Test that 'Clean' variations map to Clean Vocals."""
        vocal_style = importer._map_vocal_style("clean")
        assert vocal_style.name == "Clean Vocals"

        vocal_style2 = importer._map_vocal_style("Clean singing")
        assert vocal_style2.name == "Clean Vocals"

    def test_fuzzy_matching_for_harsh_vocals(self, importer):
        """Test that harsh variations map to Harsh Vocals."""
        vocal_style = importer._map_vocal_style("harsh")
        assert vocal_style.name == "Harsh Vocals"

        vocal_style2 = importer._map_vocal_style("screaming")
        assert vocal_style2.name == "Harsh Vocals"

        vocal_style3 = importer._map_vocal_style("growls")
        assert vocal_style3.name == "Harsh Vocals"

    def test_fuzzy_matching_for_mixed_vocals(self, importer):
        """Test that 'Mixed' variations map to Mixed Vocals."""
        vocal_style = importer._map_vocal_style("mixed")
        assert vocal_style.name == "Mixed Vocals (Clean & Harsh)"

        vocal_style2 = importer._map_vocal_style("Mixed vocals")
        assert vocal_style2.name == "Mixed Vocals (Clean & Harsh)"

    def test_fuzzy_matching_for_instrumental(self, importer):
        """Test that instrumental variations map correctly."""
        vocal_style = importer._map_vocal_style("instrumental")
        assert vocal_style.name == "Instrumental (No Vocals)"

        vocal_style2 = importer._map_vocal_style("No vocals")
        assert vocal_style2.name == "Instrumental (No Vocals)"

    def test_empty_vocal_style_defaults_to_mixed(self, importer):
        """Test that empty vocal style defaults to Mixed Vocals."""
        vocal_style = importer._map_vocal_style("")
        assert vocal_style.name == "Mixed Vocals (Clean & Harsh)"

        vocal_style_none = importer._map_vocal_style(None)
        assert vocal_style_none.name == "Mixed Vocals (Clean & Harsh)"

    def test_unique_vocal_style_created_when_no_fuzzy_match(self, importer):
        """Test that unique vocal styles are created when fuzzy matching fails."""
        vocal_style = importer._map_vocal_style("Throat Singing")

        assert vocal_style.name == "Throat Singing"
        assert vocal_style.slug == "throat-singing"
        assert VocalStyle.objects.filter(name="Throat Singing").exists()
