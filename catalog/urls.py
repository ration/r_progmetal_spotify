"""URL configuration for catalog app."""

from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.AlbumListView.as_view(), name="album-list"),
]
