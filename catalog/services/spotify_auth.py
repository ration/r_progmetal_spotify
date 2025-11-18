"""
Spotify OAuth 2.0 authentication service.

Handles OAuth flow, token exchange, and token refresh.
"""
from __future__ import annotations

import os
import base64
from typing import TypedDict
from datetime import timedelta

import requests
from django.utils import timezone

from catalog.models import User, SpotifyToken


class SpotifyProfile(TypedDict):
    """Spotify user profile from API."""
    id: str
    email: str
    display_name: str
    images: list[dict[str, str]]


class SpotifyTokenResponse(TypedDict):
    """Spotify token response from API."""
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshTokenExpiredError(Exception):
    """Raised when refresh token is invalid or expired."""
    pass


class SpotifyAuthService:
    """Service for Spotify OAuth operations."""

    SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
    SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
    SPOTIFY_PROFILE_URL = "https://api.spotify.com/v1/me"
    SCOPES = "user-read-email user-read-private"

    def __init__(self) -> None:
        """Initialize Spotify auth service with credentials from environment."""
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Spotify OAuth environment variables not configured")

    def generate_auth_url(self, state: str) -> str:
        """
        Generate Spotify authorization URL with state parameter.

        Args:
            state: OAuth state parameter for CSRF protection

        Returns:
            str: Full Spotify authorization URL
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': self.SCOPES,
        }
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{self.SPOTIFY_AUTH_URL}?{query_string}"

    def exchange_code_for_tokens(self, code: str) -> SpotifyTokenResponse:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Spotify OAuth callback

        Returns:
            SpotifyTokenResponse: Dict with access_token, refresh_token, expires_in

        Raises:
            requests.HTTPError: If token exchange fails
        """
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        response = requests.post(
            self.SPOTIFY_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri,
            },
            headers={
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def fetch_user_profile(self, access_token: str) -> SpotifyProfile:
        """
        Fetch user profile from Spotify API.

        Args:
            access_token: Spotify OAuth access token

        Returns:
            SpotifyProfile: Dict with user profile data (id, email, display_name, images)

        Raises:
            requests.HTTPError: If profile fetch fails
        """
        response = requests.get(
            self.SPOTIFY_PROFILE_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> SpotifyTokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Spotify OAuth refresh token

        Returns:
            SpotifyTokenResponse: Dict with new access_token, refresh_token, expires_in

        Raises:
            RefreshTokenExpiredError: If refresh token is invalid/expired
            requests.HTTPError: If refresh request fails
        """
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        response = requests.post(
            self.SPOTIFY_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            },
            headers={
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            timeout=10,
        )

        if response.status_code == 400:
            raise RefreshTokenExpiredError("Refresh token expired or invalid")

        response.raise_for_status()
        return response.json()

    def create_or_update_user(
        self,
        spotify_profile: SpotifyProfile,
        tokens: SpotifyTokenResponse
    ) -> User:
        """
        Create or update user from Spotify profile and store tokens.

        Args:
            spotify_profile: User profile data from Spotify API
            tokens: Token response from Spotify OAuth

        Returns:
            User: Created or updated User instance

        First user automatically becomes admin (bootstrap logic).
        """
        spotify_user_id = spotify_profile['id']
        email = spotify_profile['email']
        display_name = spotify_profile['display_name']
        profile_picture = (
            spotify_profile['images'][0]['url']
            if spotify_profile.get('images')
            else None
        )

        # Create or update user
        user, created = User.objects.get_or_create(
            spotify_user_id=spotify_user_id,
            defaults={
                'email': email,
                'display_name': display_name,
                'profile_picture_url': profile_picture,
            }
        )

        # First user becomes admin
        if created and User.objects.count() == 1:
            user.is_admin = True
            user.save()

        # Update profile if user already exists
        if not created:
            user.email = email
            user.display_name = display_name
            user.profile_picture_url = profile_picture
            user.save()

        # Store or update tokens
        expires_at = timezone.now() + timedelta(seconds=tokens['expires_in'])

        # Handle case where refresh_token might not be returned (already exists)
        try:
            existing_token = SpotifyToken.objects.get(user=user)
            refresh_token_value = tokens.get('refresh_token', existing_token.refresh_token)
        except SpotifyToken.DoesNotExist:
            refresh_token_value = tokens['refresh_token']

        SpotifyToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': refresh_token_value,
                'expires_at': expires_at,
            }
        )

        return user


# Global service instance
spotify_auth_service = SpotifyAuthService()
