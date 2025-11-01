"""
Tests for database configuration.

Verifies that database connection and configuration work correctly
for both SQLite (tests) and PostgreSQL (development/production).
"""

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import override_settings


class TestDatabaseConfiguration:
    """Tests for database configuration and connectivity."""

    @pytest.mark.django_db
    def test_database_connection(self):
        """Test that database connection is established successfully."""
        # This will fail if database connection cannot be made
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        assert result == (1,), "Database query should return expected result"
        cursor.close()

    def test_sqlite_used_for_tests(self):
        """Verify that SQLite is used for running tests (not PostgreSQL)."""
        db_engine = settings.DATABASES['default']['ENGINE']

        # Tests should always use SQLite for speed and isolation
        assert db_engine == 'django.db.backends.sqlite3', \
            f"Tests should use SQLite, but using: {db_engine}"

    def test_in_memory_database_for_tests(self):
        """Verify that in-memory database is used for tests."""
        db_name = settings.DATABASES['default']['NAME']

        # pytest-django uses a shared memory database URI format
        # Both ':memory:' and 'file:memorydb_*' are valid in-memory databases
        assert ':memory:' in db_name or 'memorydb' in db_name, \
            f"Tests should use in-memory database, but using: {db_name}"

    def test_database_settings_structure(self):
        """Verify database settings have required keys."""
        db_config = settings.DATABASES['default']

        required_keys = ['ENGINE', 'NAME']
        for key in required_keys:
            assert key in db_config, f"Database config missing required key: {key}"

    @pytest.mark.django_db
    def test_database_migrations_applied(self):
        """Verify that Django migrations have been applied."""
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # If plan is empty, all migrations are applied
        assert len(plan) == 0, \
            "There are unapplied migrations. Run 'python manage.py migrate'"

    @pytest.mark.django_db
    def test_can_create_and_query_records(self):
        """Test basic database operations work correctly."""
        from catalog.models import Genre

        # Create a test genre
        test_genre = Genre.objects.create(
            name="Test Progressive Metal",
            slug="test-progressive-metal"
        )

        # Verify it was created
        assert test_genre.id is not None
        assert test_genre.name == "Test Progressive Metal"

        # Query it back
        retrieved = Genre.objects.get(slug="test-progressive-metal")
        assert retrieved.id == test_genre.id
        assert retrieved.name == test_genre.name

    @pytest.mark.django_db
    def test_database_supports_transactions(self):
        """Verify that database supports transactions (atomic operations)."""
        from django.db import transaction
        from catalog.models import Genre

        initial_count = Genre.objects.count()

        try:
            with transaction.atomic():
                Genre.objects.create(
                    name="Transaction Test Genre",
                    slug="transaction-test"
                )
                # Force a constraint violation to rollback
                raise Exception("Intentional rollback")
        except Exception:
            pass

        # Count should be unchanged due to rollback
        final_count = Genre.objects.count()
        assert final_count == initial_count, \
            "Transaction rollback should restore database state"
