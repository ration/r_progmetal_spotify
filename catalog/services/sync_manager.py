"""
Synchronization manager for coordinating album catalog sync operations.

This module handles the orchestration of sync operations, including:
- Creating and managing SyncOperation records
- Running sync in background threads
- Progress tracking and status updates
- Error handling and recovery
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages synchronization operations for the album catalog.

    Handles background thread execution, progress tracking, and status updates
    for sync operations triggered from the web UI.
    """

    def __init__(self) -> None:
        """Initialize the SyncManager."""
        pass

    @staticmethod
    def start_sync(sync_op_id: int) -> None:
        """
        Start a synchronization operation in a background daemon thread.

        Args:
            sync_op_id: ID of the SyncOperation to execute

        Note:
            This method spawns a daemon thread and returns immediately.
            The actual sync runs in the background.
        """
        thread = threading.Thread(
            target=SyncManager.run_sync,
            args=(sync_op_id,),
            daemon=True,
            name=f"sync-{sync_op_id}",
        )
        thread.start()
        logger.info(f"Started sync thread for SyncOperation {sync_op_id}")

    @staticmethod
    def run_sync(sync_op_id: int) -> None:
        """
        Execute the actual synchronization operation.

        This method runs in a background thread and:
        1. Updates SyncOperation status to 'running'
        2. Calls existing AlbumImporter logic
        3. Tracks progress and updates status
        4. Creates SyncRecord on completion
        5. Handles errors and sets failed status

        Args:
            sync_op_id: ID of the SyncOperation to execute
        """
        from catalog.models import Album, SyncOperation, SyncRecord
        from catalog.services.album_importer import AlbumImporter
        from catalog.services.google_sheets import GoogleSheetsService
        from catalog.services.spotify_client import SpotifyClient

        try:
            # Get the sync operation
            sync_op = SyncOperation.objects.get(id=sync_op_id)

            # Update status to running
            sync_op.status = "running"
            sync_op.stage = "fetching"
            sync_op.stage_message = "Fetching albums from Google Sheets..."
            sync_op.save(update_fields=["status", "stage", "stage_message"])

            # Initialize services
            import os

            sheets_url = os.getenv("GOOGLE_SHEETS_XLSX_URL", "")
            spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
            spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")

            sheets_service = GoogleSheetsService(xlsx_url=sheets_url)
            spotify_client = SpotifyClient(
                client_id=spotify_client_id, client_secret=spotify_client_secret
            )
            importer = AlbumImporter(sheets_service, spotify_client)

            # Fetch data from Google Sheets
            sheet_data = sheets_service.fetch_albums()
            sync_op.total_albums = len(sheet_data)
            sync_op.stage = "processing"
            sync_op.stage_message = f"Processing {len(sheet_data)} albums..."
            sync_op.save(update_fields=["total_albums", "stage", "stage_message"])

            # Import albums with progress tracking
            created_count = 0
            updated_count = 0
            skipped_count = 0
            failed_count = 0
            failed_albums = []

            for idx, sheets_data in enumerate(sheet_data, start=1):
                try:
                    # Extract Spotify album ID from URL
                    album_id = spotify_client.extract_album_id(
                        sheets_data["spotify_url"]
                    )
                    if not album_id:
                        logger.warning(
                            f"Could not extract Spotify ID from URL: "
                            f"{sheets_data.get('spotify_url', 'N/A')}"
                        )
                        skipped_count += 1
                        continue

                    # Check if album already exists - skip if it does
                    if Album.objects.filter(spotify_album_id=album_id).exists():
                        logger.debug(
                            f"Album {album_id} already exists in database, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Fetch metadata from Spotify
                    spotify_metadata = spotify_client.get_album_metadata(album_id)
                    if not spotify_metadata:
                        logger.warning(f"Could not fetch metadata for album {album_id}")
                        skipped_count += 1
                        continue

                    # Import the album using the importer's private method
                    created = importer._import_single_album(
                        sheets_data, spotify_metadata
                    )

                    if created:
                        created_count += 1
                    else:
                        # This should rarely happen since we checked existence above
                        updated_count += 1

                    # Update progress every 5 albums
                    if idx % 5 == 0 or idx == len(sheet_data):
                        sync_op.albums_processed = idx
                        sync_op.stage_message = (
                            f"Syncing album {idx} of {len(sheet_data)}..."
                        )
                        sync_op.save(
                            update_fields=["albums_processed", "stage_message"]
                        )

                except Exception as e:
                    logger.error(f"Error importing album {idx}: {e}")
                    failed_count += 1
                    album_name = sheets_data.get("album", "Unknown")
                    failed_albums.append(f"{album_name}: {str(e)[:50]}")
                    skipped_count += 1

            # Finalizing
            sync_op.stage = "finalizing"
            sync_op.stage_message = "Finalizing synchronization..."
            sync_op.save(update_fields=["stage", "stage_message"])

            # Determine success status based on failure rate
            success_count = created_count + updated_count
            total_processed = sync_op.albums_processed
            is_partial_failure = failed_count > 0 and success_count > 0

            # Create SyncRecord for historical log
            SyncRecord.objects.create(
                albums_created=created_count,
                albums_updated=updated_count,
                albums_skipped=skipped_count,
                total_albums_in_catalog=Album.objects.count(),
                success=(failed_count == 0),
                error_message=(
                    f"Partial failure: {failed_count} albums failed"
                    if is_partial_failure
                    else None
                ),
            )

            # Mark sync complete
            sync_op.status = "completed"
            sync_op.completed_at = timezone.now()

            if is_partial_failure:
                # Partial success - store warning info in error_message
                sync_op.error_message = (
                    f"Warning: {success_count} of {total_processed} albums synced successfully. "
                    f"{failed_count} albums failed."
                )
                sync_op.stage_message = "Sync completed with warnings"
            else:
                sync_op.stage_message = (
                    f"Sync complete! Updated {sync_op.albums_processed} albums"
                )

            sync_op.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "stage_message",
                    "error_message",
                ]
            )

            logger.info(
                f"Sync {sync_op_id} completed: {created_count} created, "
                f"{updated_count} updated, {skipped_count} skipped, {failed_count} failed"
            )

        except Exception as e:
            logger.exception(f"Sync {sync_op_id} failed: {e}")

            # Determine user-friendly error message based on exception type
            import requests

            if isinstance(e, requests.exceptions.ConnectionError):
                user_message = (
                    "Unable to reach external services. Please check your internet connection "
                    "and verify that Google Sheets and Spotify are accessible."
                )
            elif isinstance(e, requests.exceptions.Timeout):
                user_message = (
                    "Request timed out while fetching data. The external services may be slow "
                    "or unavailable. Please try again later."
                )
            elif isinstance(e, requests.exceptions.HTTPError):
                user_message = (
                    f"HTTP error occurred while fetching data: {e.response.status_code}. "
                    "The external service may be temporarily unavailable."
                )
            elif isinstance(e, ValueError) and "header row" in str(e).lower():
                user_message = (
                    "Google Sheets configuration error: Unable to find the expected data structure. "
                    "Please verify the GOOGLE_SHEETS_XLSX_URL is correct and the sheet format hasn't changed."
                )
            elif isinstance(e, ValueError) and "column" in str(e).lower():
                user_message = (
                    "Google Sheets configuration error: Missing expected columns in the spreadsheet. "
                    "Please verify the sheet contains all required columns (Artist, Album, Spotify, etc.)."
                )
            else:
                user_message = f"Synchronization failed: {str(e)}"

            try:
                sync_op = SyncOperation.objects.get(id=sync_op_id)
                sync_op.status = "failed"
                sync_op.completed_at = timezone.now()
                sync_op.error_message = user_message
                sync_op.save(update_fields=["status", "completed_at", "error_message"])

                # Create SyncRecord for failed sync
                SyncRecord.objects.create(
                    albums_created=0,
                    albums_updated=0,
                    albums_skipped=0,
                    total_albums_in_catalog=Album.objects.count(),
                    success=False,
                    error_message=user_message,
                )
            except Exception as save_error:
                logger.exception(
                    f"Failed to save error status for sync {sync_op_id}: {save_error}"
                )
