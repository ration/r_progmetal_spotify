"""
Django management command for importing albums from Google Sheets and Spotify.

Usage:
    python manage.py import_albums [--limit N] [--sync]
"""

import os
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Album, SyncRecord
from catalog.services.google_sheets import GoogleSheetsService
from catalog.services.spotify_client import SpotifyClient
from catalog.services.album_importer import AlbumImporter


class Command(BaseCommand):
    help = "Import albums from Google Sheets and enrich with Spotify metadata"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of albums to import (useful for testing)",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Sync mode: update existing albums instead of skipping them",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        sync_mode = options["sync"]

        self.stdout.write(self.style.MIGRATE_HEADING("Album Import Starting"))
        self.stdout.write("")

        # Validate required environment variables
        spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
        spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        sheets_url = os.getenv("GOOGLE_SHEETS_XLSX_URL")

        if not spotify_client_id or not spotify_client_secret:
            raise CommandError(
                "Spotify credentials not found. Please set SPOTIFY_CLIENT_ID "
                "and SPOTIFY_CLIENT_SECRET environment variables."
            )

        if not sheets_url:
            raise CommandError(
                "Google Sheets URL not found. Please set GOOGLE_SHEETS_XLSX_URL "
                "environment variable."
            )

        # Initialize services
        self.stdout.write("Initializing services...")
        try:
            sheets_service = GoogleSheetsService(sheets_url)
            spotify_client = SpotifyClient(spotify_client_id, spotify_client_secret)
            importer = AlbumImporter(sheets_service, spotify_client)
        except Exception as e:
            raise CommandError(f"Failed to initialize services: {e}")

        self.stdout.write(self.style.SUCCESS("✓ Services initialized"))
        self.stdout.write("")

        # Run import
        mode_text = "sync" if sync_mode else "import"
        if limit:
            self.stdout.write(f"Starting {mode_text} (limit: {limit} albums)...")
        else:
            self.stdout.write(f"Starting {mode_text} (all albums)...")

        try:
            if sync_mode:
                created, updated, skipped = importer.sync_albums()
            else:
                created, updated, skipped = importer.import_albums(
                    limit=limit, skip_existing=True
                )

            # Get total album count for sync record
            total_albums = Album.objects.count()

            # Create sync record to track this import operation
            SyncRecord.objects.create(
                albums_created=created,
                albums_updated=updated,
                albums_skipped=skipped,
                total_albums_in_catalog=total_albums,
                success=True,
            )

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Import Results:"))
            self.stdout.write(f"  {self.style.SUCCESS('Created:')} {created}")
            self.stdout.write(f"  {self.style.WARNING('Updated:')} {updated}")
            self.stdout.write(f"  {self.style.NOTICE('Skipped:')} {skipped}")
            self.stdout.write(f"  Total albums in catalog: {total_albums}")
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✓ Album import complete"))

        except Exception as e:
            # Record failed sync
            try:
                SyncRecord.objects.create(
                    albums_created=0,
                    albums_updated=0,
                    albums_skipped=0,
                    total_albums_in_catalog=Album.objects.count(),
                    success=False,
                    error_message=str(e),
                )
            except Exception:
                pass  # Don't fail if we can't record the failure

            raise CommandError(f"Import failed: {e}")
