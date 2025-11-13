"""URL configuration for catalog app."""

from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.AlbumListView.as_view(), name="album-list"),
    path("<int:pk>/", views.AlbumDetailView.as_view(), name="album-detail"),
    path("album/<int:album_id>/cover-art/", views.album_cover_art, name="album-cover-art"),
    path("sync/trigger/", views.sync_trigger, name="sync-trigger"),
    path("sync/stop/", views.sync_stop, name="sync-stop"),
    path("sync/button/", views.sync_button, name="sync-button"),
    path("sync/status/", views.sync_status, name="sync-status"),
]
