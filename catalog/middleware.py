"""
Authentication and token refresh middleware.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from catalog.models import User, SpotifyToken
from catalog.services.spotify_auth import (
    spotify_auth_service,
    RefreshTokenExpiredError
)

if TYPE_CHECKING:
    from collections.abc import Callable


class AuthenticationMiddleware(MiddlewareMixin):
    """
    Load user from session and protect routes.

    This middleware:
    1. Loads the User object from session and attaches to request
    2. Protects non-public routes by redirecting unauthenticated users to login
    """

    PUBLIC_PATHS = [
        '/catalog/auth/login/',
        '/catalog/auth/spotify/',
        '/catalog/auth/callback/',
    ]

    def process_request(self, request: HttpRequest) -> None:
        """
        Load user from session.

        Args:
            request: HTTP request object

        Attaches user object to request.user if authenticated, None otherwise.
        """
        user_id = request.session.get('user_id')
        if user_id:
            try:
                request.user = User.objects.get(id=user_id)  # type: ignore[assignment]
            except User.DoesNotExist:
                request.user = None  # type: ignore[assignment]
        else:
            request.user = None  # type: ignore[assignment]

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: tuple,
        view_kwargs: dict
    ) -> HttpResponse | None:
        """
        Protect routes requiring authentication.

        Args:
            request: HTTP request object
            view_func: View function being called
            view_args: Positional arguments for view
            view_kwargs: Keyword arguments for view

        Returns:
            HttpResponse: Redirect to login if unauthenticated on protected route
            None: Allow request to proceed
        """
        # Allow public paths
        if request.path in self.PUBLIC_PATHS:
            return None

        # Redirect unauthenticated users
        if not hasattr(request, 'user') or request.user is None:
            return redirect(f'/catalog/auth/login/?next={request.path}')

        return None


class TokenRefreshMiddleware(MiddlewareMixin):
    """
    Automatically refresh expired Spotify access tokens.

    This middleware checks if the user's access token is expiring soon (within 5 minutes)
    and automatically refreshes it using the refresh token. If refresh fails, the user
    is logged out.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """
        Check and refresh tokens if needed.

        Args:
            request: HTTP request object

        Returns:
            HttpResponse: Redirect to login if token refresh fails
            None: Allow request to proceed
        """
        if not hasattr(request, 'user') or request.user is None:
            return None

        try:
            token = SpotifyToken.objects.get(user=request.user)

            # Refresh if expiring soon
            if token.expires_soon():
                try:
                    new_tokens = spotify_auth_service.refresh_access_token(
                        token.refresh_token
                    )
                    token.refresh(
                        new_tokens['access_token'],
                        new_tokens.get('refresh_token', token.refresh_token),
                        new_tokens['expires_in']
                    )
                except RefreshTokenExpiredError:
                    # Refresh failed - log out user
                    token.delete()
                    request.session.flush()
                    return redirect('/catalog/auth/login/?error=token_expired')

        except SpotifyToken.DoesNotExist:
            # User has no token - log them out
            request.session.flush()
            return redirect('/catalog/auth/login/?error=no_token')

        return None
