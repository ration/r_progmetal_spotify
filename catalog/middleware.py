"""
Authentication and token refresh middleware.
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(MiddlewareMixin):
    """
    Load user from session and protect routes.

    This middleware:
    1. Loads the User object from session and attaches to request
    2. Protects non-public routes by redirecting unauthenticated users to login
    3. Skips admin paths (handled by Django's admin auth)
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

        Attaches user object to request.user if authenticated via Spotify OAuth.
        If Django admin auth has already set the user, don't overwrite it.
        """
        # Skip if user already authenticated by Django admin auth middleware
        if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
            logger.debug(f"Skipping custom auth - Django user already authenticated: {request.user}")
            return

        # Try to load Spotify OAuth user from session
        user_id = request.session.get('user_id')
        logger.debug(f"Session user_id: {user_id}, session keys: {list(request.session.keys())}")

        if user_id:
            try:
                spotify_user = User.objects.get(id=user_id)
                request.user = spotify_user  # type: ignore[assignment]
                logger.debug(f"Loaded Spotify user from session: {spotify_user}")
            except User.DoesNotExist:
                # User in session doesn't exist - clear session
                logger.warning(f"User ID {user_id} in session doesn't exist - clearing")
                if 'user_id' in request.session:
                    del request.session['user_id']
        else:
            logger.debug(f"No user_id in session, request.user is: {getattr(request, 'user', 'NOT SET')}")
        # If no Spotify user, leave request.user as set by Django auth (AnonymousUser)

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
        # Allow admin paths (handled by Django admin)
        if request.path.startswith('/admin/'):
            return None

        # Allow public paths
        if request.path in self.PUBLIC_PATHS:
            return None

        # Check if user is authenticated (either Spotify OAuth or Django admin)
        user = getattr(request, 'user', None)
        is_auth = getattr(user, 'is_authenticated', False)

        logger.debug(f"Auth check for {request.path}: user={user}, is_auth={is_auth}, user_type={type(user).__name__}")

        if not user or not is_auth:
            logger.debug(f"Redirecting unauthenticated request to login")
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
        # Skip admin paths and users without custom User model
        if request.path.startswith('/admin/'):
            return None

        if not hasattr(request, 'user') or request.user is None:
            return None

        # Skip Django admin users (they don't have Spotify tokens)
        if not isinstance(request.user, User):
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
