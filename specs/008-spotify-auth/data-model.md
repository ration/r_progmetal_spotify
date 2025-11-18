# Data Model: Spotify Authentication

**Feature**: 008-spotify-auth
**Date**: 2025-11-18

## Overview

This feature introduces two new models to support Spotify OAuth authentication with local user management. The User model stores profile information from Spotify along with application-specific attributes (admin flag). The SpotifyToken model stores OAuth tokens separately for security and lifecycle management.

---

## New Models

### User

**Purpose**: Represents an authenticated user in the application, sourced from Spotify OAuth but stored locally for application-specific attributes (admin status, preferences).

**Key Requirement**: "While authentication works via spotify, it should still have a local user database instance of it. Users can be marked as administrators."

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| id | Integer (PK) | Auto-increment | Primary key |
| spotify_user_id | String (255) | Unique, Not Null, Indexed | Spotify's unique user ID (from OAuth profile) |
| email | String (255) | Not Null, Indexed | User's email from Spotify profile |
| display_name | String (255) | Not Null | User's display name from Spotify profile |
| profile_picture_url | String (500) | Nullable | URL to user's Spotify profile picture |
| is_admin | Boolean | Default: False, Not Null | Administrator flag for application access control |
| created_at | DateTime | Auto-now-add, Not Null | Timestamp of first login (user creation) |
| updated_at | DateTime | Auto-now, Not Null | Timestamp of last profile update |

**Indexes**:
- `spotify_user_id` (unique) - Primary lookup during OAuth callback
- `email` - Secondary lookup for user search
- `is_admin` - Filter admin users efficiently

**Validation Rules**:
- `spotify_user_id` must be unique (enforced at database level)
- `email` must be valid email format (Django EmailField validation)
- `display_name` cannot be empty string
- `profile_picture_url` must be valid URL if provided

**Business Logic**:
- **First user bootstrap**: If `User.objects.count() == 0`, set `is_admin=True` for first user
- **Profile updates**: On each login, update `display_name`, `email`, `profile_picture_url` from Spotify if changed
- **Soft deletion** (future): Consider adding `is_active` field instead of hard deleting users

---

### SpotifyToken

**Purpose**: Stores Spotify OAuth access and refresh tokens for authenticated users. Separated from User model for security, token lifecycle management, and to support potential future multi-token scenarios.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| id | Integer (PK) | Auto-increment | Primary key |
| user | ForeignKey(User) | Not Null, Unique, ON DELETE CASCADE | One-to-one relationship with User |
| access_token | String (500) | Not Null | Spotify OAuth access token (short-lived, ~1 hour) |
| refresh_token | String (500) | Not Null | Spotify OAuth refresh token (long-lived, no expiry) |
| expires_at | DateTime | Not Null, Indexed | Timestamp when access_token expires |
| created_at | DateTime | Auto-now-add, Not Null | Timestamp of initial token issuance |
| updated_at | DateTime | Auto-now, Not Null | Timestamp of last token refresh |

**Indexes**:
- `user_id` (unique) - One token record per user
- `expires_at` - Efficient token expiry checks in middleware

**Validation Rules**:
- `expires_at` must be in the future when token is created
- `access_token` and `refresh_token` must not be empty
- Only one SpotifyToken record per User (enforced by unique constraint on user_id)

**Business Logic**:
- **Token refresh**: Update `access_token`, `refresh_token`, `expires_at` atomically when refreshing
- **Token cleanup**: Delete token on user logout or disconnect
- **Expiry check**: `expires_soon()` method returns True if `expires_at < now() + 5 minutes`
- **Security**: Tokens encrypted at rest via PostgreSQL encryption (no app-layer encryption)

**Helper Methods**:
```python
def expires_soon(self) -> bool:
    """Returns True if token expires within 5 minutes."""
    return timezone.now() + timedelta(minutes=5) >= self.expires_at

def refresh(self, new_access_token: str, new_refresh_token: str, expires_in: int) -> None:
    """Update token with refreshed values from Spotify."""
    self.access_token = new_access_token
    self.refresh_token = new_refresh_token
    self.expires_at = timezone.now() + timedelta(seconds=expires_in)
    self.save()
```

---

## Model Relationships

```
User (1) ←──────── (1) SpotifyToken
  ↓
  is_admin: Boolean
```

**Relationship Details**:
- **User ↔ SpotifyToken**: One-to-one relationship
  - A User can have at most one SpotifyToken
  - A SpotifyToken must belong to exactly one User
  - Cascade delete: When User is deleted, SpotifyToken is automatically deleted

**Rationale for Separation**:
- **Security**: Token exposure limited to specific queries, not every User query
- **Lifecycle**: Tokens can be deleted/refreshed independently of User record
- **Performance**: User queries don't load token data unnecessarily
- **Future-proof**: Supports potential multiple token types (e.g., different OAuth providers)

---

## Entity-Relationship Diagram

```
┌─────────────────────────────────────┐
│            User                     │
├─────────────────────────────────────┤
│ PK  id: Integer                     │
│ UQ  spotify_user_id: String(255)    │
│     email: String(255)              │
│     display_name: String(255)       │
│     profile_picture_url: String(500)│
│     is_admin: Boolean = False       │
│     created_at: DateTime            │
│     updated_at: DateTime            │
└─────────────────────────────────────┘
                 │
                 │ 1:1
                 ▼
┌─────────────────────────────────────┐
│         SpotifyToken                │
├─────────────────────────────────────┤
│ PK  id: Integer                     │
│ FK  user: User (UNIQUE)             │
│     access_token: String(500)       │
│     refresh_token: String(500)      │
│     expires_at: DateTime            │
│     created_at: DateTime            │
│     updated_at: DateTime            │
└─────────────────────────────────────┘
```

---

## State Transitions

### User Creation Flow

```
[No User]
    → OAuth Success
    → [Create User from Spotify profile]
    → [Create SpotifyToken with tokens]
    → [User Active]
```

### Token Refresh Flow

```
[Token Valid]
    → Middleware checks expires_at
    → expires_at < now() + 5 min
    → [Refresh via Spotify API]
    → [Update SpotifyToken record]
    → [Token Valid (refreshed)]

OR

[Token Valid]
    → Middleware checks expires_at
    → Refresh fails (refresh_token invalid)
    → [Delete SpotifyToken]
    → [Logout User]
    → [Redirect to Login]
```

### User Disconnect Flow

```
[User Authenticated]
    → User clicks "Disconnect"
    → [Delete SpotifyToken]
    → [End Django session]
    → [User logged out]
```

---

## Migration Strategy

### Migration 1: Create User Model

```python
# catalog/migrations/000X_create_user_model.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '000X_previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('spotify_user_id', models.CharField(max_length=255, unique=True, db_index=True)),
                ('email', models.EmailField(max_length=255, db_index=True)),
                ('display_name', models.CharField(max_length=255)),
                ('profile_picture_url', models.URLField(max_length=500, null=True, blank=True)),
                ('is_admin', models.BooleanField(default=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'catalog_user',
                'ordering': ['-created_at'],
            },
        ),
    ]
```

### Migration 2: Create SpotifyToken Model

```python
# catalog/migrations/000X_create_spotify_token_model.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '000X_create_user_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpotifyToken',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('user', models.OneToOneField(
                    to='catalog.User',
                    on_delete=models.CASCADE,
                    related_name='spotify_token'
                )),
                ('access_token', models.CharField(max_length=500)),
                ('refresh_token', models.CharField(max_length=500)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'catalog_spotify_token',
            },
        ),
    ]
```

### Rollback Strategy

To rollback this feature:
1. Delete SpotifyToken records: `SpotifyToken.objects.all().delete()`
2. Delete User records: `User.objects.all().delete()`
3. Run reverse migrations: `python manage.py migrate catalog <previous_migration_number>`
4. Remove OAuth views and URLs

**Data Loss Warning**: Rollback will delete all user accounts and require users to re-authenticate.

---

## Query Patterns

### Pattern 1: Create User from OAuth

```python
from catalog.models import User, SpotifyToken
from django.utils import timezone
from datetime import timedelta

# Extract from Spotify OAuth response
spotify_user_id = spotify_profile['id']
email = spotify_profile['email']
display_name = spotify_profile['display_name']
profile_picture = spotify_profile['images'][0]['url'] if spotify_profile['images'] else None

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
```

### Pattern 2: Store OAuth Tokens

```python
# After OAuth token exchange
expires_at = timezone.now() + timedelta(seconds=expires_in)

# Create or update token (upsert)
SpotifyToken.objects.update_or_create(
    user=user,
    defaults={
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': expires_at,
    }
)
```

### Pattern 3: Check Token Expiry (Middleware)

```python
from catalog.models import SpotifyToken
from django.utils import timezone
from datetime import timedelta

def check_and_refresh_token(user):
    try:
        token = SpotifyToken.objects.get(user=user)

        # Check if token expires within 5 minutes
        if token.expires_at < timezone.now() + timedelta(minutes=5):
            # Refresh token via Spotify API
            new_tokens = spotify_auth_service.refresh_token(token.refresh_token)
            token.refresh(
                new_access_token=new_tokens['access_token'],
                new_refresh_token=new_tokens['refresh_token'],
                expires_in=new_tokens['expires_in']
            )
    except SpotifyToken.DoesNotExist:
        # User has no token - log them out
        return False
    except RefreshTokenExpiredError:
        # Refresh failed - delete token and log out
        token.delete()
        return False

    return True
```

### Pattern 4: Get Admin Users

```python
# List all administrators
admins = User.objects.filter(is_admin=True)

# Check if user is admin
if request.user.is_admin:
    # Allow access to admin features
    pass
```

### Pattern 5: User Disconnect

```python
from catalog.models import SpotifyToken

# Delete user's token
SpotifyToken.objects.filter(user=request.user).delete()

# End Django session
logout(request)
```

---

## Database Schema SQL (PostgreSQL)

For reference, the generated SQL schema:

```sql
-- User table
CREATE TABLE catalog_user (
    id SERIAL PRIMARY KEY,
    spotify_user_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    profile_picture_url VARCHAR(500),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_catalog_user_spotify_id ON catalog_user(spotify_user_id);
CREATE INDEX idx_catalog_user_email ON catalog_user(email);
CREATE INDEX idx_catalog_user_is_admin ON catalog_user(is_admin);

-- SpotifyToken table
CREATE TABLE catalog_spotify_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES catalog_user(id) ON DELETE CASCADE,
    access_token VARCHAR(500) NOT NULL,
    refresh_token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_catalog_spotify_token_expires_at ON catalog_spotify_token(expires_at);
```

---

## Performance Considerations

### Query Optimization
- **User lookup by spotify_user_id**: Indexed unique field, O(log n) lookup
- **Token expiry checks**: Indexed expires_at field, efficient middleware checks
- **Admin filtering**: Indexed is_admin field, fast admin user queries

### Scaling Considerations (100s of users expected)
- Current schema supports 1000s of users without optimization
- Token refresh checks on every request acceptable for scale
- Consider adding caching layer if scale increases to 10,000+ users

### Database Connections
- Django connection pooling sufficient for current scale
- PostgreSQL can handle 100+ concurrent connections easily

---

## Security Considerations

### Token Security
- **Encryption at rest**: PostgreSQL encryption configured in production
- **No token logging**: Tokens excluded from logs and error messages
- **Secure transmission**: HTTPS only in production (SPOTIFY_REDIRECT_URI validation)
- **Token rotation**: Access tokens expire hourly, refresh tokens rotated on each refresh

### Access Control
- **Admin flag**: Simple boolean check prevents unauthorized access
- **CSRF protection**: Django CSRF middleware + OAuth state parameter
- **Session security**: Secure cookies, HttpOnly, SameSite=Lax

### Data Privacy
- **Minimal data**: Only store necessary Spotify profile fields
- **User control**: Users can disconnect and delete their tokens
- **GDPR considerations**: User data deletion via admin action (future feature)

---

## Summary

The data model introduces two clean, focused models:

1. **User**: Local user records sourced from Spotify with `is_admin` flag for application-specific authorization
2. **SpotifyToken**: Separate token storage for security and lifecycle management

This design satisfies the key requirement for "a local user database instance" while maintaining clean separation of concerns between user identity and authentication tokens. The `is_admin` field provides simple, effective authorization for administrative features like sync operations.
