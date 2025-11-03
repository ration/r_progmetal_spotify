"""
Integration tests for User Story 1: Navigate Large Catalog with Pagination.

Tests verify:
- Basic pagination with 50 items per page
- Pagination with fewer items than page size
- Page navigation and URL updates
- Browser refresh maintaining page state
"""
import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Album, Artist, Genre, VocalStyle


@pytest.fixture
def sample_artist(db):
    """Create or get a sample artist for testing."""
    artist, _ = Artist.objects.get_or_create(
        spotify_artist_id="1234567890123456789012",
        defaults={
            "name": "Test Artist",
            "country": "US",
        }
    )
    return artist


@pytest.fixture
def sample_genre(db):
    """Get or create a sample genre for testing."""
    genre, _ = Genre.objects.get_or_create(
        slug="progressive-metal",
        defaults={"name": "Progressive Metal"}
    )
    return genre


@pytest.fixture
def sample_vocal_style(db):
    """Get or create a sample vocal style for testing."""
    vocal, _ = VocalStyle.objects.get_or_create(
        slug="clean-vocals",
        defaults={"name": "Clean Vocals"}
    )
    return vocal


@pytest.fixture
def create_albums(db, sample_artist, sample_genre, sample_vocal_style):
    """
    Create test albums for pagination testing.

    Returns a function that creates N albums with sequential names.
    """
    def _create_albums(count: int):
        albums = []
        for i in range(count):
            album = Album.objects.create(
                spotify_album_id=f"test_album_{i:03d}_" + "0" * 10,
                name=f"Test Album {i+1}",
                artist=sample_artist,
                genre=sample_genre,
                vocal_style=sample_vocal_style,
                release_date="2025-01-01",
                spotify_url=f"https://open.spotify.com/album/test_album_{i:03d}_0000000000"
            )
            albums.append(album)
        return albums
    return _create_albums


@pytest.mark.django_db
class TestBasicPagination:
    """
    Test Acceptance Scenario 1:
    Given the catalog contains 175 albums,
    When I visit the catalog page,
    Then I see exactly 50 albums displayed with page navigation showing "Page 1 of 4"
    """

    def test_first_page_displays_50_albums(self, client: Client, create_albums):
        """Test that first page shows exactly 50 albums when catalog has 175+ albums."""
        # Create 175 albums
        create_albums(175)

        # Visit catalog page
        response = client.get(reverse("catalog:album-list"))

        assert response.status_code == 200
        assert len(response.context["page_obj"].object_list) == 50
        assert response.context["page_obj"].number == 1
        assert response.context["page_obj"].paginator.num_pages == 4
        assert response.context["is_paginated"] is True

    def test_pagination_controls_present_with_175_albums(self, client: Client, create_albums):
        """Test that pagination controls show 'Page 1 of 4' with 175 albums."""
        create_albums(175)

        response = client.get(reverse("catalog:album-list"))

        assert response.status_code == 200
        page_obj = response.context["page_obj"]
        assert page_obj.number == 1
        assert page_obj.paginator.num_pages == 4
        # Verify pagination info
        assert page_obj.start_index() == 1
        assert page_obj.end_index() == 50
        assert page_obj.paginator.count == 175


@pytest.mark.django_db
class TestPaginationWithFewerItems:
    """
    Test Acceptance Scenario 3:
    Given the catalog contains 30 albums (less than page size),
    When I visit the catalog page,
    Then I see all 30 albums with no pagination controls displayed
    """

    def test_no_pagination_with_30_albums(self, client: Client, create_albums):
        """Test that pagination controls are hidden when total albums < page size."""
        create_albums(30)

        response = client.get(reverse("catalog:album-list"))

        assert response.status_code == 200
        assert len(response.context["page_obj"].object_list) == 30
        assert response.context["page_obj"].paginator.num_pages == 1
        assert response.context["is_paginated"] is False


@pytest.mark.django_db
class TestPageNavigation:
    """
    Test Acceptance Scenario 2:
    Given I'm on page 1 of the catalog,
    When I click "Next" or "Page 2",
    Then I see albums 51-100 and the URL updates to reflect the current page
    """

    def test_navigate_to_page_2(self, client: Client, create_albums):
        """Test navigation to second page shows albums 51-100."""
        create_albums(175)

        # Navigate to page 2
        response = client.get(reverse("catalog:album-list"), {"page": 2})

        assert response.status_code == 200
        page_obj = response.context["page_obj"]
        assert page_obj.number == 2
        assert len(page_obj.object_list) == 50
        assert page_obj.start_index() == 51
        assert page_obj.end_index() == 100

    def test_url_contains_page_parameter(self, client: Client, create_albums):
        """Test that page URL contains ?page=N parameter."""
        create_albums(175)

        response = client.get(reverse("catalog:album-list"), {"page": 2})

        assert response.status_code == 200
        assert response.wsgi_request.GET.get("page") == "2"


@pytest.mark.django_db
class TestPageStatePersistence:
    """
    Test Acceptance Scenario 4:
    Given I'm viewing page 2 of the catalog,
    When I refresh the browser,
    Then I remain on page 2 with the same albums displayed
    """

    def test_refresh_maintains_page_state(self, client: Client, create_albums):
        """Test that refreshing page 2 maintains the page state."""
        create_albums(175)

        # Visit page 2
        response1 = client.get(reverse("catalog:album-list"), {"page": 2})
        page_obj1 = response1.context["page_obj"]

        # Refresh (visit same URL again)
        response2 = client.get(reverse("catalog:album-list"), {"page": 2})
        page_obj2 = response2.context["page_obj"]

        # Verify same page displayed
        assert page_obj1.number == page_obj2.number == 2
        assert page_obj1.start_index() == page_obj2.start_index() == 51
        assert page_obj1.end_index() == page_obj2.end_index() == 100
