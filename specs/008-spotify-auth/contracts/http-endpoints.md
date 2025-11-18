# HTTP Endpoints Contract: Spotify Authentication

**Feature**: 008-spotify-auth
**Date**: 2025-11-18

## Overview

This document defines the HTTP API contracts for Spotify OAuth authentication endpoints. All endpoints are within the `catalog` Django app and follow RESTful conventions where applicable.

---

## Base URL

- **Development**: `http://localhost:9000/catalog/auth/`
- **Production**: `https://yourdomain.com/catalog/auth/`

---

## Endpoint 1: Login Page

**Endpoint**: `GET /catalog/auth/login/`

**Purpose**: Display login page with "Login with Spotify" button

**Authentication**: None (public endpoint)

**Request**:
```http
GET /catalog/auth/login/ HTTP/1.1
Host: localhost:9000
```

**Query Parameters**:
- `next` (optional): URL to redirect after successful login
  - Example: `/catalog/auth/login/?next=/catalog/admin/sync/`
  - Default: `/catalog/` (album list page)

**Response** (200 OK):
```http
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head><title>Login - Progressive Metal Catalog</title></head>
  <body>
    <h1>Login with Spotify</h1>
    <a href="/catalog/auth/spotify/?next=/catalog/admin/sync/" class="btn">
      Login with Spotify
    </a>
  </body>
</html>
```

**Template**: `catalog/templates/catalog/login.html`

**Context Variables**:
- `next_url`: URL to redirect after login (from `?next=` parameter)

**User Story**: US1 (Login with Spotify Account)

---

## Endpoint 2: Initiate OAuth Flow

**Endpoint**: `GET /catalog/auth/spotify/`

**Purpose**: Redirect user to Spotify authorization page to initiate OAuth flow

**Authentication**: None (public endpoint)

**Request**:
```http
GET /catalog/auth/spotify/?next=/catalog/admin/sync/ HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
```

**Query Parameters**:
- `next` (optional): URL to redirect after successful login
  - Stored in session for use after OAuth callback

**Server Logic**:
1. Generate random OAuth state parameter (32 bytes, URL-safe)
2. Store state in Django session: `request.session['oauth_state'] = state`
3. Store next URL in session: `request.session['next_url'] = next_url`
4. Build Spotify authorization URL with parameters:
   - `client_id`: From `SPOTIFY_CLIENT_ID` env var
   - `response_type`: `code`
   - `redirect_uri`: From `SPOTIFY_REDIRECT_URI` env var
   - `state`: Generated state parameter
   - `scope`: `user-read-email user-read-private`
5. Redirect to Spotify authorization URL

**Response** (302 Found):
```http
HTTP/1.1 302 Found
Location: https://accounts.spotify.com/authorize?client_id=<client_id>&response_type=code&redirect_uri=<redirect_uri>&state=<state>&scope=user-read-email+user-read-private
Set-Cookie: sessionid=abc123; HttpOnly; Secure; SameSite=Lax
```

**Error Response** (500 Internal Server Error):
```http
HTTP/1.1 500 Internal Server Error
Content-Type: text/html

<p>OAuth configuration error: SPOTIFY_CLIENT_ID not set</p>
```

**User Story**: US1 (Login with Spotify Account)

---

## Endpoint 3: OAuth Callback

**Endpoint**: `GET /catalog/auth/callback/`

**Purpose**: Handle OAuth callback from Spotify, exchange authorization code for tokens, create/update user

**Authentication**: None (public endpoint, but validates OAuth state)

**Request** (Success):
```http
GET /catalog/auth/callback/?code=AQD...&state=abc123xyz HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
```

**Request** (User Denied):
```http
GET /catalog/auth/callback/?error=access_denied&state=abc123xyz HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
```

**Query Parameters**:
- `code` (on success): Authorization code from Spotify
- `state`: OAuth state parameter (must match session state)
- `error` (on error): Error code if user denied authorization

**Server Logic** (Success Path):
1. Validate state parameter matches session: `request.session.get('oauth_state')`
2. Exchange authorization code for tokens via Spotify API:
   ```
   POST https://accounts.spotify.com/api/token
   Body: grant_type=authorization_code&code=<code>&redirect_uri=<redirect_uri>
   Auth: Basic <base64(client_id:client_secret)>
   ```
3. Fetch user profile from Spotify API:
   ```
   GET https://api.spotify.com/v1/me
   Authorization: Bearer <access_token>
   ```
4. Create or update User record (see data-model.md)
5. Create or update SpotifyToken record
6. Set user ID in Django session: `request.session['user_id'] = user.id`
7. Delete OAuth state from session: `del request.session['oauth_state']`
8. Redirect to next URL (from session) or default (`/catalog/`)

**Response** (302 Found - Success):
```http
HTTP/1.1 302 Found
Location: /catalog/admin/sync/
Set-Cookie: sessionid=abc123; HttpOnly; Secure; SameSite=Lax
```

**Response** (400 Bad Request - Invalid State):
```http
HTTP/1.1 400 Bad Request
Content-Type: text/html

<p>Invalid OAuth state parameter. Possible CSRF attack.</p>
```

**Response** (302 Found - User Denied):
```http
HTTP/1.1 302 Found
Location: /catalog/auth/login/?error=access_denied
```

**Template** (Error Page): `catalog/templates/catalog/oauth_error.html`

**Error Codes**:
- `invalid_state`: State parameter mismatch (CSRF protection)
- `access_denied`: User denied authorization
- `spotify_api_error`: Spotify API returned error
- `token_exchange_failed`: Failed to exchange code for tokens

**User Story**: US1 (Login with Spotify Account)

---

## Endpoint 4: Logout

**Endpoint**: `POST /catalog/auth/logout/`

**Purpose**: End user session, clear session data

**Authentication**: Required (must be logged in)

**Request**:
```http
POST /catalog/auth/logout/ HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
Content-Type: application/x-www-form-urlencoded

csrfmiddlewaretoken=xyz789
```

**CSRF Protection**: Required (Django CSRF token)

**Server Logic**:
1. Delete user's SpotifyToken (optional - tokens can persist for re-login)
2. Clear Django session: `request.session.flush()`
3. Redirect to login page

**Response** (302 Found):
```http
HTTP/1.1 302 Found
Location: /catalog/auth/login/
Set-Cookie: sessionid=; Max-Age=0
```

**Error Response** (403 Forbidden - CSRF):
```http
HTTP/1.1 403 Forbidden
Content-Type: text/html

<p>CSRF verification failed</p>
```

**User Story**: US1 (Login with Spotify Account)

---

## Endpoint 5: Profile Page

**Endpoint**: `GET /catalog/auth/profile/`

**Purpose**: Display user's Spotify profile information

**Authentication**: Required (must be logged in)

**Request**:
```http
GET /catalog/auth/profile/ HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
```

**Response** (200 OK):
```http
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head><title>Profile - Progressive Metal Catalog</title></head>
  <body>
    <h1>Your Profile</h1>
    <img src="https://i.scdn.co/image/..." alt="Profile Picture">
    <p>Display Name: John Doe</p>
    <p>Email: john.doe@example.com</p>
    <p>Spotify User ID: johndoe123</p>
    <form method="post" action="/catalog/auth/disconnect/">
      <button type="submit">Disconnect Spotify</button>
    </form>
  </body>
</html>
```

**Template**: `catalog/templates/catalog/profile.html`

**Context Variables**:
- `user`: User model instance with Spotify profile data
- `is_admin`: Boolean indicating if user has admin privileges

**Response** (302 Found - Not Authenticated):
```http
HTTP/1.1 302 Found
Location: /catalog/auth/login/?next=/catalog/auth/profile/
```

**User Story**: US2 (View Connected Spotify Profile)

---

## Endpoint 6: Disconnect Spotify Account

**Endpoint**: `POST /catalog/auth/disconnect/`

**Purpose**: Disconnect Spotify account, delete tokens, log out user

**Authentication**: Required (must be logged in)

**Request**:
```http
POST /catalog/auth/disconnect/ HTTP/1.1
Host: localhost:9000
Cookie: sessionid=abc123
Content-Type: application/x-www-form-urlencoded

csrfmiddlewaretoken=xyz789
```

**CSRF Protection**: Required (Django CSRF token)

**Server Logic**:
1. Delete user's SpotifyToken: `SpotifyToken.objects.filter(user=request.user).delete()`
2. Clear Django session: `request.session.flush()`
3. Redirect to login page with success message

**Response** (302 Found):
```http
HTTP/1.1 302 Found
Location: /catalog/auth/login/?disconnected=true
```

**Error Response** (403 Forbidden - CSRF):
```http
HTTP/1.1 403 Forbidden
Content-Type: text/html

<p>CSRF verification failed</p>
```

**Error Response** (302 Found - Not Authenticated):
```http
HTTP/1.1 302 Found
Location: /catalog/auth/login/
```

**User Story**: US3 (Disconnect Spotify Account)

---

## Middleware: Authentication Check

**Purpose**: Protect routes requiring authentication, redirect unauthenticated users to login

**Implementation**: Django middleware in `catalog/middleware.py`

**Logic**:
1. Check if user ID exists in session: `request.session.get('user_id')`
2. If user ID exists, load User from database: `User.objects.get(id=user_id)`
3. Attach user to request: `request.user = user`
4. If no user ID in session, set `request.user = None`
5. For protected routes (not `/auth/login/`, `/auth/callback/`):
   - If `request.user is None`, redirect to login with `?next=` parameter

**Protected Routes**:
- `/catalog/` (album list - requires authentication)
- `/catalog/admin/sync/` (admin page - requires authentication + `is_admin=True`)
- `/catalog/auth/profile/` (profile page - requires authentication)
- `/catalog/auth/logout/` (logout - requires authentication)
- `/catalog/auth/disconnect/` (disconnect - requires authentication)

**Public Routes**:
- `/catalog/auth/login/` (login page)
- `/catalog/auth/spotify/` (OAuth initiate)
- `/catalog/auth/callback/` (OAuth callback)

**User Story**: US1 (Login with Spotify Account)

---

## Middleware: Token Refresh

**Purpose**: Automatically refresh expired Spotify access tokens

**Implementation**: Django middleware in `catalog/middleware.py`

**Logic**:
1. If user is authenticated and has SpotifyToken:
2. Check if token expires soon: `token.expires_at < now() + 5 minutes`
3. If expiring, refresh via Spotify API:
   ```
   POST https://accounts.spotify.com/api/token
   Body: grant_type=refresh_token&refresh_token=<refresh_token>
   Auth: Basic <base64(client_id:client_secret)>
   ```
4. Update SpotifyToken with new access_token, refresh_token, expires_at
5. If refresh fails (refresh_token expired/invalid):
   - Delete SpotifyToken
   - Log out user
   - Redirect to login with error message

**Performance**:
- Middleware runs on every authenticated request
- Database query to fetch token: `SELECT * FROM spotify_token WHERE user_id = ?`
- Acceptable overhead for 100s of users scale

**User Story**: US4 (Automatic Token Refresh)

---

## Error Handling

### Common Error Scenarios

**1. Missing Environment Variables**
- **Trigger**: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, or `SPOTIFY_REDIRECT_URI` not set
- **Response**: 500 Internal Server Error with clear message
- **User Impact**: Cannot initiate OAuth flow

**2. Invalid OAuth State**
- **Trigger**: State parameter mismatch (CSRF attack or expired session)
- **Response**: 400 Bad Request
- **User Impact**: Must restart login flow

**3. User Denied Authorization**
- **Trigger**: User clicks "Cancel" on Spotify authorization page
- **Response**: 302 Redirect to login with `?error=access_denied`
- **User Impact**: Returned to login page with error message

**4. Token Exchange Failure**
- **Trigger**: Spotify API returns error during code-to-token exchange
- **Response**: Error page with "Authentication failed, please try again"
- **User Impact**: Must restart login flow

**5. Refresh Token Expired**
- **Trigger**: Refresh token invalid/revoked during automatic refresh
- **Response**: 302 Redirect to login with error message
- **User Impact**: Must re-authenticate with Spotify

**6. Network/Spotify API Unavailable**
- **Trigger**: Spotify API timeout or 5xx error
- **Response**: Error page with "Spotify service unavailable"
- **User Impact**: Temporary inability to authenticate

---

## Security Considerations

### CSRF Protection
- **OAuth State Parameter**: Prevents CSRF on OAuth flow (validates state matches session)
- **Django CSRF Token**: Required for POST endpoints (logout, disconnect)
- **SameSite Cookies**: `SameSite=Lax` prevents CSRF via external sites

### Token Security
- **HTTPS Only**: `SPOTIFY_REDIRECT_URI` must use HTTPS in production
- **Secure Cookies**: `Secure` flag on session cookies in production
- **HttpOnly Cookies**: Prevents JavaScript access to session cookies
- **Token Encryption**: PostgreSQL encryption at rest for token storage

### Rate Limiting
- **OAuth Flow**: Spotify rate limits authorization requests (no app-level rate limiting needed)
- **API Calls**: Middleware token refresh limited by Spotify API rate limits
- **Future Enhancement**: Consider rate limiting login attempts (e.g., max 5 per minute per IP)

---

## Integration with Existing Features

### Album Catalog Integration
- **Album List** (`/catalog/`): Requires authentication, shows user's display name in navbar
- **Album Detail** (`/catalog/<id>/`): Requires authentication
- **Admin Sync** (`/catalog/admin/sync/`): Requires authentication + `is_admin=True`

### Navigation Bar
- **Logged Out**: Show "Login with Spotify" link
- **Logged In**: Show user's display name/profile picture, "Profile" link, "Logout" button

---

## Testing Scenarios

### Contract Test Cases

**Test 1: Login Page Renders**
```python
def test_login_page_renders():
    response = client.get('/catalog/auth/login/')
    assert response.status_code == 200
    assert 'Login with Spotify' in response.content.decode()
```

**Test 2: OAuth Flow Initiates**
```python
def test_oauth_flow_initiates():
    response = client.get('/catalog/auth/spotify/')
    assert response.status_code == 302
    assert 'accounts.spotify.com/authorize' in response['Location']
    assert 'client_id' in response['Location']
    assert 'state' in response['Location']
```

**Test 3: OAuth Callback with Invalid State**
```python
def test_oauth_callback_invalid_state():
    response = client.get('/catalog/auth/callback/?code=abc&state=invalid')
    assert response.status_code == 400
    assert 'Invalid state' in response.content.decode()
```

**Test 4: Logout Clears Session**
```python
def test_logout_clears_session():
    # Login first
    client.force_login(user)

    # Logout
    response = client.post('/catalog/auth/logout/')
    assert response.status_code == 302
    assert response['Location'] == '/catalog/auth/login/'

    # Session cleared
    assert 'user_id' not in client.session
```

**Test 5: Protected Route Redirects Unauthenticated**
```python
def test_protected_route_redirects():
    response = client.get('/catalog/')
    assert response.status_code == 302
    assert '/catalog/auth/login/' in response['Location']
    assert 'next=' in response['Location']
```

**Test 6: Disconnect Deletes Token**
```python
def test_disconnect_deletes_token():
    # Login and create token
    client.force_login(user)
    token = SpotifyToken.objects.create(user=user, ...)

    # Disconnect
    response = client.post('/catalog/auth/disconnect/')
    assert response.status_code == 302

    # Token deleted
    assert not SpotifyToken.objects.filter(user=user).exists()
```

---

## Summary

This contract defines 6 HTTP endpoints for Spotify OAuth authentication:

1. **GET /auth/login/**: Display login page
2. **GET /auth/spotify/**: Initiate OAuth flow
3. **GET /auth/callback/**: Handle OAuth callback
4. **POST /auth/logout/**: End session
5. **GET /auth/profile/**: View profile
6. **POST /auth/disconnect/**: Disconnect account

Plus 2 middleware components for authentication checks and token refresh. All endpoints follow RESTful conventions, include comprehensive error handling, and implement strong security measures (CSRF, HTTPS, secure cookies).
