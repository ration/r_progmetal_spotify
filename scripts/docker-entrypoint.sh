#!/bin/bash
# Docker entrypoint script for Album Catalog application
# This script runs when the Docker container starts

set -e  # Exit on error

echo "🚀 Album Catalog - Starting application..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U progmetal > /dev/null 2>&1; do
    echo "   PostgreSQL not ready yet, waiting..."
    sleep 2
done
echo "✓ PostgreSQL is ready!"

# Run database migrations
echo "📦 Running database migrations..."
uv run python manage.py migrate --noinput

# Collect static files (if needed for production)
if [ "$DJANGO_ENV" = "production" ]; then
    echo "📁 Collecting static files..."
    uv run python manage.py collectstatic --noinput
fi

# Create superuser if credentials provided
if [ ! -z "$DJANGO_SUPERUSER_USERNAME" ] && [ ! -z "$DJANGO_SUPERUSER_PASSWORD" ] && [ ! -z "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "👤 Creating superuser..."
    uv run python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print("Superuser created successfully")
else:
    print("Superuser already exists")
END
fi

echo "✓ Application ready!"
echo ""

# Execute the main container command
exec "$@"
