# Quickstart Guide: Spotify Authentication

**Feature**: 008-spotify-auth
**Date**: 2025-11-18
**Branch**: `008-spotify-auth`

## Overview

This guide provides step-by-step instructions for implementing Spotify OAuth 2.0 authentication in the Progressive Metal Catalog application. Users will authenticate using their Spotify accounts, with local user records stored in the database including an administrator flag.

---

## Prerequisites

- Python 3.14 + Django 5.2.8 installed
- PostgreSQL running (Docker or local)
- Spotify Developer account
- Git repository at feature branch `008-spotify-auth`

---

## External Setup (Before Implementation)

### Step 1: Register Spotify Application

1. Go to https://developer.spotify.com/dashboard
2. Click "Create app"
3. Fill in application details:
   - **App name**: Progressive Metal Catalog
   - **App description**: Album catalog for r/progmetal releases
   - **Redirect URIs**:
     - Development: `http://localhost:9000/catalog/auth/callback/`
     - Production: `https://yourdomain.com/catalog/auth/callback/`
   - **APIs used**: Web API
4. Click "Save"
5. Copy **Client ID** and **Client Secret** (click "Show Client Secret")

### Step 2: Add Environment Variables

Add to `.env` file (or Docker environment):

```bash
# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID=<your_client_id_from_step_1>
SPOTIFY_CLIENT_SECRET=<your_client_secret_from_step_1>
SPOTIFY_REDIRECT_URI=http://localhost:9000/catalog/auth/callback/  # Dev
# SPOTIFY_REDIRECT_URI=https://yourdomain.com/catalog/auth/callback/  # Prod
```

---

## Implementation Steps

### Phase 1: Data Models

#### Step 1.1: Create User Model

**File**: `catalog/models.py`

Add the User model after existing models:

```python
class User(models.Model):
    """
    User authenticated via Spotify OAuth.

    Stores Spotify profile information and application-specific attributes
    like admin status.
    """
    spotify_user_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Spotify's unique user ID"
    )
    email = models.EmailField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    profile_picture_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL to Spotify profile picture"
    )
    is_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Administrator flag for application access control"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_user'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.display_name} ({self.email})"
```

#### Step 1.2: Create SpotifyToken Model

**File**: `catalog/models.py`

Add the SpotifyToken model after User:

```python
from datetime import timedelta
from django.utils import timezone

class SpotifyToken(models.Model):
    """
    Stores Spotify OAuth access and refresh tokens for authenticated users.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='spotify_token'
    )
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'catalog_spotify_token'

    def __str__(self) -> str:
        return f"Token for {self.user.display_name}"

    def expires_soon(self) -> bool:
        """Returns True if token expires within 5 minutes."""
        return timezone.now() + timedelta(minutes=5) >= self.expires_at

    def refresh(
        self,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int
    ) -> None:
        """Update token with refreshed values from Spotify."""
        self.access_token = new_access_token
        self.refresh_token = new_refresh_token
        self.expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.save()
```

#### Step 1.3: Create and Run Migrations

```bash
python manage.py makemigrations catalog
python manage.py migrate catalog
```

**Expected Output**:
```
Migrations for 'catalog':
  catalog/migrations/000X_user_and_spotify_token.py
    - Create model User
    - Create model SpotifyToken
```

---

### Phase 2: OAuth Service

#### Step 2.1: Create Spotify Auth Service

**File**: `catalog/services/spotify_auth.py` (new file)

```python
"""
Spotify OAuth 2.0 authentication service.

Handles OAuth flow, token exchange, and token refresh.
"""
import os
import secrets
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
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Spotify OAuth environment variables not configured")

    def generate_auth_url(self, state: str) -> str:
        """Generate Spotify authorization URL with state parameter."""
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
        """Exchange authorization code for access and refresh tokens."""
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
        """Fetch user profile from Spotify API."""
        response = requests.get(
            self.SPOTIFY_PROFILE_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> SpotifyTokenResponse:
        """Refresh access token using refresh token."""
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
        """Create or update user from Spotify profile and store tokens."""
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
        SpotifyToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': tokens.get('refresh_token', user.spotify_token.refresh_token),
                'expires_at': expires_at,
            }
        )

        return user


# Global service instance
spotify_auth_service = SpotifyAuthService()
```

**Type Checking**: Run `pyright catalog/services/spotify_auth.py` to verify types.

---

### Phase 3: Views

#### Step 3.1: Add OAuth Views

**File**: `catalog/views.py`

Add these views at the end of the file:

```python
import secrets
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from catalog.services.spotify_auth import (
    spotify_auth_service,
    RefreshTokenExpiredError
)
from catalog.models import User, SpotifyToken


def login_page(request: HttpRequest) -> HttpResponse:
    """Display login page with 'Login with Spotify' button."""
    next_url = request.GET.get('next', '/catalog/')
    return render(request, 'catalog/login.html', {'next_url': next_url})


def spotify_oauth_initiate(request: HttpRequest) -> HttpResponse:
    """Initiate Spotify OAuth flow."""
    # Generate and store OAuth state
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state

    # Store next URL for post-login redirect
    next_url = request.GET.get('next', '/catalog/')
    request.session['next_url'] = next_url

    # Redirect to Spotify authorization
    auth_url = spotify_auth_service.generate_auth_url(state)
    return redirect(auth_url)


def spotify_oauth_callback(request: HttpRequest) -> HttpResponse:
    """Handle Spotify OAuth callback."""
    # Handle user denial
    if 'error' in request.GET:
        error = request.GET.get('error')
        return redirect(f'/catalog/auth/login/?error={error}')

    # Validate OAuth state (CSRF protection)
    state = request.GET.get('state')
    session_state = request.session.get('oauth_state')
    if not state or state != session_state:
        return HttpResponse('Invalid OAuth state parameter', status=400)

    # Exchange code for tokens
    code = request.GET.get('code')
    try:
        tokens = spotify_auth_service.exchange_code_for_tokens(code)
        profile = spotify_auth_service.fetch_user_profile(tokens['access_token'])
        user = spotify_auth_service.create_or_update_user(profile, tokens)

        # Set user session
        request.session['user_id'] = user.id
        del request.session['oauth_state']

        # Redirect to next URL
        next_url = request.session.pop('next_url', '/catalog/')
        return redirect(next_url)

    except Exception as e:
        return HttpResponse(f'OAuth error: {str(e)}', status=500)


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out user and clear session."""
    request.session.flush()
    return redirect('/catalog/auth/login/')


def profile_page(request: HttpRequest) -> HttpResponse:
    """Display user profile page."""
    if not hasattr(request, 'user') or request.user is None:
        return redirect(f'/catalog/auth/login/?next=/catalog/auth/profile/')

    return render(request, 'catalog/profile.html', {
        'user': request.user,
        'is_admin': request.user.is_admin,
    })


@require_http_methods(["POST"])
def disconnect_spotify(request: HttpRequest) -> HttpResponse:
    """Disconnect Spotify account and delete tokens."""
    if hasattr(request, 'user') and request.user:
        SpotifyToken.objects.filter(user=request.user).delete()

    request.session.flush()
    return redirect('/catalog/auth/login/?disconnected=true')
```

---

### Phase 4: URLs

#### Step 4.1: Add Auth URLs

**File**: `catalog/urls.py`

Add auth URL patterns:

```python
urlpatterns = [
    # ... existing patterns ...

    # Authentication
    path("auth/login/", views.login_page, name="login"),
    path("auth/spotify/", views.spotify_oauth_initiate, name="oauth-initiate"),
    path("auth/callback/", views.spotify_oauth_callback, name="oauth-callback"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/profile/", views.profile_page, name="profile"),
    path("auth/disconnect/", views.disconnect_spotify, name="disconnect"),
]
```

---

### Phase 5: Middleware

#### Step 5.1: Create Authentication Middleware

**File**: `catalog/middleware.py` (new file)

```python
"""
Authentication and token refresh middleware.
"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from catalog.models import User, SpotifyToken
from catalog.services.spotify_auth import (
    spotify_auth_service,
    RefreshTokenExpiredError
)


class AuthenticationMiddleware(MiddlewareMixin):
    """Load user from session and protect routes."""

    PUBLIC_PATHS = [
        '/catalog/auth/login/',
        '/catalog/auth/spotify/',
        '/catalog/auth/callback/',
    ]

    def process_request(self, request: HttpRequest) -> None:
        """Load user from session."""
        user_id = request.session.get('user_id')
        if user_id:
            try:
                request.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                request.user = None
        else:
            request.user = None

    def process_view(
        self,
        request: HttpRequest,
        view_func,
        view_args,
        view_kwargs
    ) -> HttpResponse | None:
        """Protect routes requiring authentication."""
        # Allow public paths
        if request.path in self.PUBLIC_PATHS:
            return None

        # Redirect unauthenticated users
        if not hasattr(request, 'user') or request.user is None:
            return redirect(f'/catalog/auth/login/?next={request.path}')

        return None


class TokenRefreshMiddleware(MiddlewareMixin):
    """Automatically refresh expired Spotify access tokens."""

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Check and refresh tokens if needed."""
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
```

#### Step 5.2: Register Middleware

**File**: `config/settings.py`

Add middleware to `MIDDLEWARE` list (after Django's SessionMiddleware):

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'django.contrib.sessions.middleware.SessionMiddleware',
    'catalog.middleware.AuthenticationMiddleware',  # Add this
    'catalog.middleware.TokenRefreshMiddleware',    # Add this
    # ... rest of middleware ...
]
```

---

### Phase 6: Templates

#### Step 6.1: Create Login Template

**File**: `catalog/templates/catalog/login.html` (new file)

```django
{% extends "catalog/base.html" %}

{% block title %}Login - Progressive Metal Catalog{% endblock %}

{% block content %}
<div class="w-full max-w-md mx-auto mt-16">
    <div class="card bg-base-200 shadow-xl">
        <div class="card-body">
            <h1 class="card-title text-3xl mb-4">Login</h1>

            {% if request.GET.error %}
            <div class="alert alert-error mb-4">
                {% if request.GET.error == 'access_denied' %}
                You denied authorization. Please grant access to continue.
                {% elif request.GET.error == 'token_expired' %}
                Your session expired. Please log in again.
                {% else %}
                Authentication error. Please try again.
                {% endif %}
            </div>
            {% endif %}

            {% if request.GET.disconnected %}
            <div class="alert alert-success mb-4">
                Successfully disconnected your Spotify account.
            </div>
            {% endif %}

            <p class="mb-6">
                Log in with your Spotify account to access the catalog.
            </p>

            <a
                href="{% url 'catalog:oauth-initiate' %}?next={{ next_url }}"
                class="btn btn-primary btn-lg w-full"
            >
                <svg class="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                Login with Spotify
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

#### Step 6.2: Create Profile Template

**File**: `catalog/templates/catalog/profile.html` (new file)

```django
{% extends "catalog/base.html" %}

{% block title %}Profile - Progressive Metal Catalog{% endblock %}

{% block content %}
<div class="w-full max-w-2xl mx-auto mt-8">
    <h1 class="text-4xl font-bold mb-8">Your Profile</h1>

    <div class="card bg-base-200 shadow-xl">
        <div class="card-body">
            <div class="flex items-center mb-6">
                {% if user.profile_picture_url %}
                <img
                    src="{{ user.profile_picture_url }}"
                    alt="Profile Picture"
                    class="w-24 h-24 rounded-full mr-6"
                >
                {% endif %}
                <div>
                    <h2 class="text-2xl font-bold">{{ user.display_name }}</h2>
                    {% if is_admin %}
                    <span class="badge badge-primary">Administrator</span>
                    {% endif %}
                </div>
            </div>

            <div class="space-y-4">
                <div>
                    <label class="font-semibold">Email:</label>
                    <p>{{ user.email }}</p>
                </div>

                <div>
                    <label class="font-semibold">Spotify User ID:</label>
                    <p class="font-mono text-sm">{{ user.spotify_user_id }}</p>
                </div>

                <div>
                    <label class="font-semibold">Member Since:</label>
                    <p>{{ user.created_at|date:"F j, Y" }}</p>
                </div>
            </div>

            <div class="card-actions justify-end mt-6">
                <form method="post" action="{% url 'catalog:disconnect' %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-error">
                        Disconnect Spotify
                    </button>
                </form>
            </div>
        </div>
    </div>

    <div class="mt-6">
        <a href="{% url 'catalog:album-list' %}" class="btn btn-outline">
            ← Back to Catalog
        </a>
    </div>
</div>
{% endblock %}
```

#### Step 6.3: Update Base Template Navigation

**File**: `catalog/templates/catalog/base.html`

Update the navigation section to show user status:

```django
<div class="navbar-end">
    {% if request.user %}
    <div class="dropdown dropdown-end">
        <label tabindex="0" class="btn btn-ghost">
            {% if request.user.profile_picture_url %}
            <img
                src="{{ request.user.profile_picture_url }}"
                alt="Profile"
                class="w-8 h-8 rounded-full"
            >
            {% endif %}
            {{ request.user.display_name }}
        </label>
        <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-200 rounded-box w-52">
            <li><a href="{% url 'catalog:profile' %}">Profile</a></li>
            {% if request.user.is_admin %}
            <li><a href="{% url 'catalog:admin-sync' %}">Admin</a></li>
            {% endif %}
            <li>
                <form method="post" action="{% url 'catalog:logout' %}">
                    {% csrf_token %}
                    <button type="submit" class="w-full text-left">Logout</button>
                </form>
            </li>
        </ul>
    </div>
    {% else %}
    <a href="{% url 'catalog:login' %}" class="btn btn-primary">Login</a>
    {% endif %}
</div>
```

---

### Phase 7: Testing

#### Step 7.1: Manual Testing Checklist

- [ ] Navigate to `/catalog/auth/login/` and verify login page renders
- [ ] Click "Login with Spotify" and verify redirect to Spotify authorization
- [ ] Grant permission on Spotify and verify redirect back to application
- [ ] Verify user is logged in (see display name in navbar)
- [ ] Navigate to `/catalog/auth/profile/` and verify profile displays correctly
- [ ] Verify admin badge shows if first user
- [ ] Test logout functionality
- [ ] Test "Disconnect Spotify" functionality
- [ ] Verify middleware protects `/catalog/` route (redirects to login when logged out)
- [ ] Test token refresh by waiting 1 hour and making requests

#### Step 7.2: Run Type Checking

```bash
pyright catalog/models.py catalog/services/spotify_auth.py catalog/views.py catalog/middleware.py
```

**Expected**: Zero errors

#### Step 7.3: Run Linting

```bash
ruff check catalog/
ruff format catalog/
```

**Expected**: Zero errors, code formatted

---

## Deployment Notes

### Production Checklist

- [ ] Set `SPOTIFY_REDIRECT_URI=https://yourdomain.com/catalog/auth/callback/`
- [ ] Add production redirect URI to Spotify app settings
- [ ] Enable HTTPS (Nginx SSL termination)
- [ ] Set `SESSION_COOKIE_SECURE=True` in Django settings
- [ ] Configure PostgreSQL encryption at rest
- [ ] Test OAuth flow on production domain

### Environment Variables (Production)

```bash
SPOTIFY_CLIENT_ID=<production_client_id>
SPOTIFY_CLIENT_SECRET=<production_client_secret>
SPOTIFY_REDIRECT_URI=https://yourdomain.com/catalog/auth/callback/
SESSION_COOKIE_SECURE=True
DATABASE_URL=postgresql://user:pass@db:5432/progmetal?sslmode=require
```

---

## Troubleshooting

### Issue: "Invalid redirect URI"
- **Solution**: Verify redirect URI matches exactly in Spotify app settings (including trailing slash)

### Issue: "Invalid OAuth state"
- **Solution**: Clear browser cookies and try again (session expired)

### Issue: "Token refresh failed"
- **Solution**: User's refresh token expired - they must re-authenticate

### Issue: Environment variables not set
- **Solution**: Verify `.env` file exists and contains all required variables

---

## Summary

This implementation provides:
- Spotify OAuth 2.0 authentication
- Local User model with `is_admin` field
- Automatic token refresh
- Session management
- CSRF protection
- Comprehensive error handling

**Total Implementation Time**: 3-4 hours for experienced Django developer

**Next Steps**: Run `/speckit.tasks` to generate detailed task breakdown for implementation.
