# Research: Spotify Authentication

**Feature**: 008-spotify-auth
**Date**: 2025-11-18

## Overview

This document captures technical decisions and research findings for implementing Spotify OAuth 2.0 authentication in the Progressive Metal Catalog Django application. Each decision includes rationale, alternatives considered, and implementation guidance.

---

## Decision 1: OAuth Library Selection

**Decision**: Use custom Django views with `requests` library instead of django-allauth

**Rationale**:
- Django-allauth adds significant complexity (40+ models, migration overhead, complex configuration)
- Spotify OAuth 2.0 flow is straightforward to implement directly (3 endpoints: initiate, callback, refresh)
- Project already uses `spotipy` for Spotify API - can leverage its OAuth utilities
- Direct control over token storage and refresh logic
- Simpler to integrate with existing Django session authentication
- Avoids dependency conflicts (django-allauth may conflict with future auth providers)

**Alternatives Considered**:
1. **django-allauth**: Full-featured social auth library
   - Rejected: Overkill for single OAuth provider, adds too many models/migrations
2. **social-auth-app-django**: More focused than allauth
   - Rejected: Still adds unnecessary abstractions for single provider
3. **authlib**: Modern OAuth library
   - Rejected: Requires ASGI for async, current project uses WSGI

**Implementation Approach**:
- Create `catalog/services/spotify_auth.py` service class
- Use `requests` library for OAuth token exchange
- Store tokens in custom `SpotifyToken` model
- Use Django's session framework for user sessions

**References**:
- Spotify OAuth 2.0 docs: https://developer.spotify.com/documentation/web-api/tutorials/code-flow
- Django authentication: https://docs.djangoproject.com/en/5.2/topics/auth/

---

## Decision 2: Token Storage Strategy

**Decision**: Store tokens in PostgreSQL database with encryption at rest, not in session storage

**Rationale**:
- Tokens persist across browser sessions (meet SC-004: session persistence)
- Database allows efficient token lookup by user ID for token refresh
- PostgreSQL encryption at rest provides security without app-layer encryption overhead
- Separates token lifecycle from Django session lifecycle
- Enables token cleanup/rotation strategies
- Supports admin view of user token status

**Alternatives Considered**:
1. **Django session storage**: Store tokens in encrypted session data
   - Rejected: Couples token lifetime to session lifetime, harder to refresh tokens, no persistence across session destruction
2. **App-layer encryption**: Encrypt tokens using `cryptography` library before storing
   - Rejected: PostgreSQL encryption at rest is sufficient, adds complexity, key management overhead
3. **Redis/cache storage**: Store tokens in Redis with TTL
   - Rejected: Adds infrastructure dependency, no durability guarantees, complicates token refresh

**Implementation Approach**:
- Create `SpotifyToken` model with foreign key to `User`
- Store `access_token`, `refresh_token`, `expires_at` fields
- Use PostgreSQL's encryption at rest (configured in Docker/production)
- Token refresh updates existing record atomically
- Delete tokens on disconnect/logout

**Security Considerations**:
- PostgreSQL connection uses SSL in production (DATABASE_URL with sslmode=require)
- Application-level access controls prevent non-admin token access
- Tokens never logged or exposed in error messages

---

## Decision 3: Session Management Approach

**Decision**: Use Django's built-in session framework with database backend

**Rationale**:
- Leverages Django's mature session handling (CSRF protection, session fixation prevention)
- Database-backed sessions persist across server restarts
- Integrates seamlessly with existing Django middleware
- Supports session expiry and cleanup
- No additional dependencies required
- Familiar Django patterns for developers

**Alternatives Considered**:
1. **JWT tokens**: Stateless authentication with JSON Web Tokens
   - Rejected: No built-in revocation (tokens valid until expiry), increases client-side complexity, overkill for server-rendered app
2. **Redis-backed sessions**: Fast session storage in Redis
   - Rejected: Adds infrastructure dependency, current scale doesn't require Redis performance
3. **Cookie-only sessions**: Store session data in signed cookies
   - Rejected: 4KB cookie size limit too small for token storage, exposes more data to client

**Implementation Approach**:
- Use Django's default session middleware (already configured)
- Store user ID in session after successful OAuth
- Check session authentication in view middleware
- Clear session on logout
- Set `SESSION_COOKIE_SECURE=True` in production (HTTPS only)
- Configure session expiry to match Spotify refresh token lifetime

**Django Settings**:
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Database-backed
SESSION_COOKIE_SECURE = True  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
```

---

## Decision 4: Admin Permission Model

**Decision**: Use simple boolean `is_admin` field on User model, not Django's permission system

**Rationale**:
- Single permission level needed ("admin" vs. "regular user")
- Django's built-in permission system is overkill (30+ default permissions per model)
- Simplifies queries (single field check vs. permission lookups)
- Clearer intent in code: `if user.is_admin:` vs. `if user.has_perm('catalog.admin_sync'):`
- Easier to explain to non-technical stakeholders
- Future-proof: can migrate to Django permissions if granular permissions needed later

**Alternatives Considered**:
1. **Django Permission System**: Built-in groups and permissions
   - Rejected: Over-engineered for binary admin/non-admin distinction, adds complexity
2. **Django Groups**: Single "Administrators" group
   - Rejected: Requires group assignment logic, extra DB queries, still overkill for one permission level
3. **Separate AdminUser model**: Subclass or separate table for admins
   - Rejected: Complicates queries, unnecessary normalization for binary flag

**Implementation Approach**:
- Add `is_admin = models.BooleanField(default=False)` to User model
- First user to register becomes admin automatically (bootstrap logic)
- Admin users can promote other users in future admin panel (out of scope for this feature)
- Check `request.user.is_admin` in views requiring admin access
- Add `@require_admin` decorator for admin-only views

**Admin Bootstrap**:
```python
# In user creation logic
if User.objects.count() == 0:
    user.is_admin = True  # First user is admin
```

---

## Decision 5: Token Refresh Strategy

**Decision**: Use middleware-based token refresh on every request

**Rationale**:
- Transparent to user (meets SC-006: token refresh transparent)
- Catches token expiry before API calls fail
- Simple implementation (single middleware class)
- No background task infrastructure needed
- Handles edge cases (user inactive for hours then returns)
- Works with Django's synchronous WSGI architecture

**Alternatives Considered**:
1. **Background task (Celery)**: Periodic token refresh task
   - Rejected: Adds infrastructure (Redis/RabbitMQ), refreshes tokens unnecessarily, complicates deployment
2. **On-demand refresh**: Refresh only when Spotify API call fails
   - Rejected: Leads to user-visible errors, complicates error handling in multiple places
3. **Client-side refresh**: JavaScript checks token expiry and triggers refresh
   - Rejected: Requires exposing token expiry to client, adds client-side complexity, doesn't work for server-rendered pages

**Implementation Approach**:
- Create `TokenRefreshMiddleware` in `catalog/middleware.py`
- Check if user has SpotifyToken with expires_at < now + 5 minutes
- If expiring soon, refresh using refresh_token before view executes
- Update SpotifyToken record with new tokens
- Log out user if refresh fails (refresh token expired/revoked)

**Middleware Logic**:
```python
class TokenRefreshMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            token = SpotifyToken.objects.filter(user=request.user).first()
            if token and token.expires_soon():
                try:
                    spotify_auth_service.refresh_token(token)
                except RefreshTokenExpired:
                    logout(request)
                    return redirect('catalog:login')
        return self.get_response(request)
```

**Performance Consideration**:
- Database query on every authenticated request (acceptable overhead for 100s of users)
- Can add caching if scale increases (check token expiry from cache)

---

## Decision 6: CSRF Protection Implementation

**Decision**: Use Django's built-in CSRF protection with state parameter validation

**Rationale**:
- Django CSRF middleware already configured and battle-tested
- OAuth state parameter provides additional protection against CSRF attacks on OAuth flow
- Meets FR-011: validate OAuth state parameter
- No additional libraries needed
- Standard Django pattern familiar to developers

**Alternatives Considered**:
1. **Manual CSRF token validation**: Custom middleware
   - Rejected: Reinventing Django's CSRF wheel, error-prone
2. **JWT state tokens**: Cryptographically signed state parameters
   - Rejected: Overkill for state validation, Django session-based state is sufficient
3. **No state parameter**: Rely only on Django CSRF
   - Rejected: Violates OAuth security best practices, fails FR-011

**Implementation Approach**:
- Generate random state string, store in Django session before OAuth redirect
- Pass state parameter to Spotify authorization URL
- Validate state parameter in OAuth callback matches session state
- Clear state from session after validation
- Use `@csrf_exempt` on callback view (state parameter provides CSRF protection for OAuth flow)

**State Validation Logic**:
```python
# In OAuth initiate view
state = secrets.token_urlsafe(32)
request.session['oauth_state'] = state
redirect_url = f"https://accounts.spotify.com/authorize?state={state}..."

# In OAuth callback view
if request.GET.get('state') != request.session.get('oauth_state'):
    return HttpResponse('Invalid state parameter', status=400)
del request.session['oauth_state']
```

---

## Decision 7: HTTPS Configuration for OAuth Callbacks

**Decision**: Require HTTPS in production, allow HTTP in development via environment variable

**Rationale**:
- Spotify requires HTTPS for OAuth redirect URIs in production
- Local development uses HTTP (localhost exception in Spotify app settings)
- Environment-based configuration supports both dev and prod
- Nginx/Docker handles SSL termination in production
- Prevents accidental HTTP usage in production

**Alternatives Considered**:
1. **Self-signed certificates in development**: HTTPS everywhere
   - Rejected: Adds development setup complexity, browser warnings, certificate management
2. **ngrok/localtunnel for development**: HTTPS tunneling
   - Rejected: Requires third-party service, network dependency, complicates local development
3. **Always require HTTPS**: No HTTP support
   - Rejected: Breaks local development workflow, forces developers to use production-like SSL setup

**Implementation Approach**:
- Add `SPOTIFY_REDIRECT_URI` to environment variables
- Development: `SPOTIFY_REDIRECT_URI=http://localhost:9000/catalog/auth/callback/`
- Production: `SPOTIFY_REDIRECT_URI=https://yourdomain.com/catalog/auth/callback/`
- Nginx/Docker Compose handles SSL termination in production
- Add settings validation: warn if `SPOTIFY_REDIRECT_URI` uses HTTP in production

**Django Settings**:
```python
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Validate HTTPS in production
if not DEBUG and SPOTIFY_REDIRECT_URI.startswith('http://'):
    warnings.warn('SPOTIFY_REDIRECT_URI should use HTTPS in production')
```

**Spotify App Settings**:
- Register both redirect URIs in Spotify Developer Dashboard:
  - Development: `http://localhost:9000/catalog/auth/callback/`
  - Production: `https://yourdomain.com/catalog/auth/callback/`

---

## Implementation Dependencies

### Python Packages (add to pyproject.toml)
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "requests>=2.32.0",  # HTTP library for OAuth token exchange
]
```

**Note**: No additional packages needed - `requests` likely already a dependency of spotipy

### Environment Variables
```bash
# Required
SPOTIFY_CLIENT_ID=<your_spotify_client_id>
SPOTIFY_CLIENT_SECRET=<your_spotify_client_secret>
SPOTIFY_REDIRECT_URI=http://localhost:9000/catalog/auth/callback/  # Dev
# SPOTIFY_REDIRECT_URI=https://yourdomain.com/catalog/auth/callback/  # Prod

# Optional - defaults shown
# SESSION_COOKIE_SECURE=False  # True in production
# SESSION_ENGINE=django.contrib.sessions.backends.db
```

### External Setup
1. Register application at https://developer.spotify.com/dashboard
2. Add redirect URIs to Spotify app settings (dev + prod)
3. Copy Client ID and Client Secret to environment
4. Configure HTTPS in production (Nginx SSL termination)

---

## Summary

These seven decisions provide a complete technical foundation for implementing Spotify OAuth authentication:

1. **Custom OAuth implementation** (no django-allauth) for simplicity
2. **Database token storage** with PostgreSQL encryption for persistence
3. **Django session management** for familiarity and security
4. **Boolean `is_admin` field** for simple authorization
5. **Middleware token refresh** for transparent user experience
6. **Django CSRF + OAuth state** for comprehensive protection
7. **Environment-based HTTPS** for dev/prod flexibility

This approach minimizes external dependencies, leverages Django's built-in features, and provides a clear path to implementation with strong security guarantees.
