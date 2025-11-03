"""
Integration tests for User Story 2: Free-Text Search Across Album Data.

Tests verify:
- Search by artist name
- Search by album name
- Search by genre
- Search by vocal style
- Minimum 3 character validation
- Search query persistence in URL and refresh
"""
import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Album, Artist, Genre, VocalStyle


@pytest.fixture
def search_test_data(db):
    """
    Create diverse test data for search functionality.

    Returns a dictionary with created artists, genres, vocal styles, and albums.
    """
    # Create artists
    periphery = Artist.objects.get_or_create(
        spotify_artist_id="0G94Jw9dJwQ2NJ18X4PyhK",
        defaults={"name": "Periphery", "country": "US"}
    )[0]

    tesseract = Artist.objects.get_or_create(
        spotify_artist_id="3Gx9VvpPv6kT5R5MpS8djb",
        defaults={"name": "TesseracT", "country": "UK"}
    )[0]

    animals_as_leaders = Artist.objects.get_or_create(
        spotify_artist_id="4i2B1HCg9OnCMaVAz3c7ZQ",
        defaults={"name": "Animals as Leaders", "country": "US"}
    )[0]

    # Create genres
    djent = Genre.objects.get_or_create(
        slug="djent",
        defaults={"name": "Djent"}
    )[0]

    prog_metal = Genre.objects.get_or_create(
        slug="progressive-metal",
        defaults={"name": "Progressive Metal"}
    )[0]

    instrumental = Genre.objects.get_or_create(
        slug="instrumental",
        defaults={"name": "Instrumental"}
    )[0]

    # Create vocal styles
    clean = VocalStyle.objects.get_or_create(
        slug="clean-vocals",
        defaults={"name": "Clean Vocals"}
    )[0]

    mixed = VocalStyle.objects.get_or_create(
        slug="mixed-vocals",
        defaults={"name": "Mixed Vocals"}
    )[0]

    instrumental_vocals = VocalStyle.objects.get_or_create(
        slug="instrumental",
        defaults={"name": "Instrumental"}
    )[0]

    # Create albums
    albums = []

    # Periphery albums
    albums.append(Album.objects.create(
        spotify_album_id="periph_v_" + "0" * 13,
        name="Periphery V: Djent Is Not A Genre",
        artist=periphery,
        genre=djent,
        vocal_style=mixed,
        release_date="2023-03-10",
        spotify_url="https://open.spotify.com/album/periph_v_0000000000000"
    ))

    albums.append(Album.objects.create(
        spotify_album_id="periph_iv_" + "0" * 12,
        name="Periphery IV: Hail Stan",
        artist=periphery,
        genre=djent,
        vocal_style=mixed,
        release_date="2019-04-05",
        spotify_url="https://open.spotify.com/album/periph_iv_000000000000"
    ))

    # TesseracT albums
    albums.append(Album.objects.create(
        spotify_album_id="tess_war_" + "0" * 13,
        name="War of Being",
        artist=tesseract,
        genre=prog_metal,
        vocal_style=clean,
        release_date="2023-09-15",
        spotify_url="https://open.spotify.com/album/tess_war_0000000000000"
    ))

    # Animals as Leaders albums
    albums.append(Album.objects.create(
        spotify_album_id="aal_parrhesia_" + "0" * 9,
        name="Parrhesia",
        artist=animals_as_leaders,
        genre=instrumental,
        vocal_style=instrumental_vocals,
        release_date="2022-03-25",
        spotify_url="https://open.spotify.com/album/aal_parrhesia_000000000"
    ))

    return {
        "artists": {"periphery": periphery, "tesseract": tesseract, "aal": animals_as_leaders},
        "genres": {"djent": djent, "prog_metal": prog_metal, "instrumental": instrumental},
        "vocals": {"clean": clean, "mixed": mixed, "instrumental": instrumental_vocals},
        "albums": albums
    }


@pytest.mark.django_db
class TestSearchByArtistName:
    """
    Test Acceptance Scenario 1:
    Given I'm on the catalog page,
    When I type "Periphery" in the search box,
    Then I see all albums by the artist Periphery and any albums with "Periphery" in the title
    """

    def test_search_by_artist_name_returns_all_artist_albums(self, client: Client, search_test_data):
        """Test that searching for 'Periphery' returns all Periphery albums."""
        response = client.get(reverse("catalog:album-list"), {"q": "Periphery"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should find 2 Periphery albums
        assert albums.count() == 2
        for album in albums:
            assert album.artist.name == "Periphery"

    def test_search_is_case_insensitive(self, client: Client, search_test_data):
        """Test that search is case-insensitive."""
        response_lower = client.get(reverse("catalog:album-list"), {"q": "periphery"})
        response_upper = client.get(reverse("catalog:album-list"), {"q": "PERIPHERY"})
        response_mixed = client.get(reverse("catalog:album-list"), {"q": "PeRiPhErY"})

        assert response_lower.context["albums"].count() == 2
        assert response_upper.context["albums"].count() == 2
        assert response_mixed.context["albums"].count() == 2


@pytest.mark.django_db
class TestSearchByAlbumName:
    """
    Test Acceptance Scenario (additional):
    Search by album name should return matching albums
    """

    def test_search_by_partial_album_name(self, client: Client, search_test_data):
        """Test searching for part of an album name."""
        response = client.get(reverse("catalog:album-list"), {"q": "Hail Stan"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should find Periphery IV: Hail Stan
        assert albums.count() == 1
        assert "Hail Stan" in albums[0].name


@pytest.mark.django_db
class TestSearchByGenre:
    """
    Test Acceptance Scenario 2:
    Given I'm on the catalog page,
    When I type "djent" in the search box,
    Then I see all albums tagged with the Djent genre
    """

    def test_search_by_genre_name(self, client: Client, search_test_data):
        """Test searching for genre name 'djent'."""
        response = client.get(reverse("catalog:album-list"), {"q": "djent"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should find 2 Djent albums (Periphery V & IV)
        assert albums.count() == 2
        for album in albums:
            assert album.genre.slug == "djent"


@pytest.mark.django_db
class TestSearchByVocalStyle:
    """
    Test Acceptance Scenario 3:
    Given I'm on the catalog page,
    When I type "clean vocals" in the search box,
    Then I see all albums with "Clean" vocal style
    """

    def test_search_by_vocal_style(self, client: Client, search_test_data):
        """Test searching for vocal style 'clean'."""
        response = client.get(reverse("catalog:album-list"), {"q": "clean"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should find 1 album with Clean vocals (TesseracT - War of Being)
        assert albums.count() == 1
        assert albums[0].vocal_style.slug == "clean-vocals"


@pytest.mark.django_db
class TestSearchMinimumCharacters:
    """
    Test FR-008:
    System MUST ignore search queries shorter than 3 characters
    """

    def test_search_with_2_characters_ignored(self, client: Client, search_test_data):
        """Test that 2-character queries return all albums (ignored)."""
        response = client.get(reverse("catalog:album-list"), {"q": "Pe"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should return all albums (search ignored)
        assert albums.count() == 4

    def test_search_with_empty_string(self, client: Client, search_test_data):
        """Test that empty search returns all albums."""
        response = client.get(reverse("catalog:album-list"), {"q": ""})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should return all albums
        assert albums.count() == 4

    def test_search_with_exactly_3_characters_works(self, client: Client, search_test_data):
        """Test that 3-character query is processed."""
        response = client.get(reverse("catalog:album-list"), {"q": "War"})

        assert response.status_code == 200
        albums = response.context["albums"]

        # Should find "War of Being" album
        assert albums.count() == 1
        assert "War" in albums[0].name


@pytest.mark.django_db
class TestSearchQueryPersistence:
    """
    Test Acceptance Scenario 6:
    Given I've entered a search term,
    When I refresh the page,
    Then my search term remains in the search box and results remain filtered
    """

    def test_search_query_in_url_parameter(self, client: Client, search_test_data):
        """Test that search query appears in URL parameters."""
        response = client.get(reverse("catalog:album-list"), {"q": "Periphery"})

        assert response.status_code == 200
        assert response.wsgi_request.GET.get("q") == "Periphery"

    def test_search_query_in_context(self, client: Client, search_test_data):
        """Test that search query is available in template context."""
        response = client.get(reverse("catalog:album-list"), {"q": "Periphery"})

        assert response.status_code == 200
        assert "search_query" in response.context
        assert response.context["search_query"] == "Periphery"

    def test_refresh_maintains_search_results(self, client: Client, search_test_data):
        """Test that refreshing with search parameter maintains filtered results."""
        # First request
        response1 = client.get(reverse("catalog:album-list"), {"q": "Periphery"})
        albums1 = response1.context["albums"]

        # Refresh (second request with same parameters)
        response2 = client.get(reverse("catalog:album-list"), {"q": "Periphery"})
        albums2 = response2.context["albums"]

        # Results should be identical
        assert albums1.count() == albums2.count() == 2
        assert list(albums1) == list(albums2)
