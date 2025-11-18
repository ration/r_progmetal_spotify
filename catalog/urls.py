"""URL configuration for catalog app."""

from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.AlbumListView.as_view(), name="album-list"),
    path("<int:pk>/", views.AlbumDetailView.as_view(), name="album-detail"),
    path("album/<int:album_id>/cover-art/", views.album_cover_art, name="album-cover-art"),
    path("admin/sync/", views.admin_sync_page, name="admin-sync"),
    path("sync/trigger/", views.sync_trigger, name="sync-trigger"),
    path("sync/stop/", views.sync_stop, name="sync-stop"),
    path("sync/button/", views.sync_button, name="sync-button"),
    path("sync/status/", views.sync_status, name="sync-status"),
    # Authentication
    path("auth/login/", views.login_page, name="login"),
    path("auth/spotify/", views.spotify_oauth_initiate, name="oauth-initiate"),
    path("auth/callback/", views.spotify_oauth_callback, name="oauth-callback"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/profile/", views.profile_page, name="profile"),
    path("auth/disconnect/", views.disconnect_spotify, name="disconnect"),
]
