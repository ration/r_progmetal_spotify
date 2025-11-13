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


def classify_and_handle_error(error: Exception) -> tuple[bool, str]:
    """
    Classify error and determine if sync should continue.

    Args:
        error: Exception that occurred during sync

    Returns:
        Tuple of (should_continue: bool, error_message: str)
        - should_continue: True if sync can continue to next tab, False if must abort
        - error_message: Human-readable error description

    Examples:
        >>> classify_and_handle_error(ConnectionError("Network down"))
        (False, "Connection error: Cannot reach external services...")
        >>> classify_and_handle_error(ValueError("Missing column"))
        (True, "Data format error in tab: Missing column")
    """
    import requests
    from catalog.services.google_sheets import TabProcessingError, CriticalSyncError

    # Critical errors - abort entire sync
    if isinstance(error, CriticalSyncError):
        return False, f"Critical sync error: {str(error)}"

    if isinstance(error, requests.exceptions.ConnectionError):
        return False, f"Connection error: Cannot reach external services. {str(error)}"

    if isinstance(error, OSError):
        return False, f"File I/O error: Cannot read Excel file. {str(error)}"

    if isinstance(error, MemoryError):
        return False, f"Memory error: System out of memory. {str(error)}"

    # Recoverable errors - skip this tab, continue with others
    if isinstance(error, TabProcessingError):
        return True, f"Tab processing error: {str(error)}"

    if isinstance(error, (ValueError, KeyError, IndexError)):
        return True, f"Data format error in tab: {str(error)}"

    if isinstance(error, requests.exceptions.Timeout):
        return True, f"Request timeout for tab: {str(error)}"

    # Default - treat as recoverable but log
    logger.warning(f"Unclassified error treated as recoverable: {type(error).__name__}")
    return True, f"Unexpected error in tab: {str(error)}"


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

            sheets_service = GoogleSheetsService(xlsx_url=sheets_url)

            # JIT mode: Don't initialize Spotify client during sync
            # Cover art and metadata will be loaded on-demand when albums are viewed
            spotify_client = None

            importer = AlbumImporter(sheets_service, spotify_client)

            # Fetch workbook and enumerate tabs
            import requests
            from io import BytesIO
            from openpyxl import load_workbook

            logger.info(f"Fetching XLSX from Google Sheets: {sheets_url}")
            response = requests.get(sheets_url, timeout=30)
            response.raise_for_status()

            # Load workbook once
            xlsx_content = BytesIO(response.content)
            workbook = load_workbook(xlsx_content)

            # Enumerate, filter, and sort tabs
            all_tabs = sheets_service.enumerate_tabs(workbook)
            prog_metal_tabs = sheets_service.filter_tabs(all_tabs)
            sorted_tabs = sheets_service.sort_tabs_chronologically(prog_metal_tabs)

            logger.info(
                f"Found {len(sorted_tabs)} prog-metal tabs to process: "
                f"{', '.join(t.name for t in sorted_tabs)}"
            )

            # Initialize counters for all tabs
            created_count = 0
            updated_count = 0
            skipped_count = 0
            failed_count = 0
            failed_albums = []
            total_albums_processed = 0

            # Track tab-level results
            tab_results = []

            # Process each tab
            for tab_index, tab_metadata in enumerate(sorted_tabs, start=1):
                # Check for cancellation request before processing each tab
                sync_op.refresh_from_db()
                if sync_op.status == "cancelled":
                    logger.info(f"Sync {sync_op_id} was cancelled by user")
                    break

                try:
                    # Update current_tab field
                    sync_op.current_tab = tab_metadata.name
                    sync_op.stage_message = (
                        f"Tab {tab_index}/{len(sorted_tabs)}: {tab_metadata.name} - "
                        f"Fetching albums..."
                    )
                    sync_op.save(update_fields=["current_tab", "stage_message"])

                    logger.info(
                        f"Processing tab {tab_index}/{len(sorted_tabs)}: {tab_metadata.name}"
                    )

                    # Fetch albums from this specific tab (pass tab year for release date parsing)
                    sheet_data = sheets_service.fetch_albums_from_tab(
                        workbook, tab_metadata.name, tab_metadata.year
                    )

                    logger.info(
                        f"Tab '{tab_metadata.name}': Retrieved {len(sheet_data)} albums"
                    )

                    # Update total albums if first tab
                    if tab_index == 1:
                        sync_op.total_albums = len(sheet_data)
                        sync_op.save(update_fields=["total_albums"])

                    # Process albums from this tab
                    sync_op.stage = "processing"
                    tab_created = 0
                    tab_skipped = 0

                    for album_idx, sheets_data in enumerate(sheet_data, start=1):
                        try:
                            # Extract Spotify album ID from URL
                            from catalog.services.album_cache import extract_spotify_album_id

                            album_id = extract_spotify_album_id(
                                sheets_data["spotify_url"]
                            )
                            if not album_id:
                                logger.warning(
                                    f"Could not extract Spotify ID from URL: "
                                    f"{sheets_data.get('spotify_url', 'N/A')}"
                                )
                                skipped_count += 1
                                tab_skipped += 1
                                continue

                            # Check if album already exists - skip if it does (duplicate detection across tabs)
                            if Album.objects.filter(spotify_album_id=album_id).exists():
                                logger.debug(
                                    f"Album {album_id} already exists in database, skipping (cross-tab duplicate)"
                                )
                                skipped_count += 1
                                tab_skipped += 1
                                continue

                            # JIT mode: Skip Spotify API calls during sync
                            # Cover art and metadata will be loaded on-demand when albums are viewed
                            spotify_metadata = None

                            logger.debug(
                                f"Importing album {album_id} in JIT mode (no Spotify API call)"
                            )

                            # Import the album using the importer's private method
                            # Pass None for spotify_metadata and the album_id explicitly
                            created = importer._import_single_album(
                                sheets_data, spotify_metadata, album_id
                            )

                            if created:
                                created_count += 1
                                tab_created += 1
                            else:
                                # This should rarely happen since we checked existence above
                                updated_count += 1

                            total_albums_processed += 1

                            # Update progress every 5 albums within a tab
                            if album_idx % 5 == 0 or album_idx == len(sheet_data):
                                sync_op.albums_processed = total_albums_processed
                                sync_op.stage_message = (
                                    f"Tab {tab_index}/{len(sorted_tabs)}: {tab_metadata.name} - "
                                    f"Processing album {album_idx}/{len(sheet_data)}"
                                )
                                sync_op.save(
                                    update_fields=["albums_processed", "stage_message"]
                                )

                        except Exception as e:
                            logger.error(
                                f"Error importing album {album_idx} from tab '{tab_metadata.name}': {e}"
                            )
                            failed_count += 1
                            album_name = sheets_data.get("album", "Unknown")
                            failed_albums.append(f"{album_name}: {str(e)[:50]}")
                            skipped_count += 1

                    # Log tab completion and record success
                    logger.info(
                        f"Tab '{tab_metadata.name}' complete: "
                        f"{tab_created} created, {tab_skipped} skipped"
                    )

                    tab_results.append({
                        'name': tab_metadata.name,
                        'success': True,
                        'created': tab_created,
                        'skipped': tab_skipped,
                        'error': None
                    })

                except Exception as tab_error:
                    # Classify error to determine if we should continue
                    should_continue, error_msg = classify_and_handle_error(tab_error)

                    logger.error(
                        f"Error processing tab '{tab_metadata.name}': {error_msg}"
                    )

                    # Record tab failure
                    tab_results.append({
                        'name': tab_metadata.name,
                        'success': False,
                        'created': 0,
                        'skipped': 0,
                        'error': error_msg
                    })

                    if not should_continue:
                        # Critical error - stop processing remaining tabs
                        logger.critical(
                            f"Critical error in tab '{tab_metadata.name}' - aborting sync"
                        )
                        break
                    else:
                        # Recoverable error - continue to next tab
                        logger.info(
                            f"Skipping tab '{tab_metadata.name}' due to recoverable error, "
                            f"continuing with remaining tabs"
                        )
                        continue

            # Clear current_tab after all tabs processed
            sync_op.current_tab = ""
            sync_op.save(update_fields=["current_tab"])

            # Close workbook to release resources
            workbook.close()

            # Finalizing
            sync_op.stage = "finalizing"
            sync_op.stage_message = "Finalizing synchronization..."
            sync_op.save(update_fields=["stage", "stage_message"])

            # Check if sync was cancelled during processing
            sync_op.refresh_from_db()
            if sync_op.status == "cancelled":
                sync_op.completed_at = timezone.now()
                sync_op.stage_message = "Sync cancelled by user"
                sync_op.save(update_fields=["completed_at", "stage_message"])

                # Create SyncRecord for cancelled sync
                SyncRecord.objects.create(
                    albums_created=created_count,
                    albums_updated=updated_count,
                    albums_skipped=skipped_count,
                    total_albums_in_catalog=Album.objects.count(),
                    success=False,
                    error_message=f"Sync cancelled by user after processing {len(tab_results)} tabs",
                )

                logger.info(
                    f"Sync {sync_op_id} cancelled: {len(tab_results)} tabs processed before cancellation, "
                    f"{created_count} created, {updated_count} updated"
                )
                return

            # Analyze tab results
            successful_tabs = [r for r in tab_results if r['success']]
            failed_tabs = [r for r in tab_results if not r['success']]

            # Determine success status based on tab and album failures
            success_count = created_count + updated_count
            total_processed = total_albums_processed
            is_partial_failure = (failed_count > 0 and success_count > 0) or len(failed_tabs) > 0

            # Build detailed error message for failed tabs
            tab_error_summary = ""
            if failed_tabs:
                failed_tab_names = ', '.join(
                    f"{r['name']} ({r['error'][:50]}...)" if len(r['error']) > 50 else f"{r['name']} ({r['error']})"
                    for r in failed_tabs[:3]  # Show first 3 failed tabs
                )
                if len(failed_tabs) > 3:
                    failed_tab_names += f" and {len(failed_tabs) - 3} more"
                tab_error_summary = f"Failed tabs: {failed_tab_names}. "

            # Create SyncRecord for historical log (aggregated across all tabs)
            SyncRecord.objects.create(
                albums_created=created_count,
                albums_updated=updated_count,
                albums_skipped=skipped_count,
                total_albums_in_catalog=Album.objects.count(),
                success=(failed_count == 0 and len(failed_tabs) == 0),
                error_message=(
                    f"{tab_error_summary}"
                    f"Partial failure: {failed_count} albums failed, "
                    f"{len(successful_tabs)}/{len(tab_results)} tabs succeeded"
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
                    f"Warning: {len(successful_tabs)}/{len(tab_results)} tabs processed successfully. "
                    f"{tab_error_summary}"
                    f"{success_count} albums imported, {failed_count} albums failed."
                )
                sync_op.stage_message = "Sync completed with warnings"
            else:
                sync_op.stage_message = (
                    f"Sync complete! Processed {len(sorted_tabs)} tabs, imported {created_count} new albums"
                )

            sync_op.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "stage_message",
                    "error_message",
                ]
            )

            # Log detailed tab results
            logger.info(
                f"Sync {sync_op_id} completed: {len(tab_results)} tabs processed "
                f"({len(successful_tabs)} successful, {len(failed_tabs)} failed)"
            )
            for tab_result in tab_results:
                if tab_result['success']:
                    logger.info(
                        f"  ✓ {tab_result['name']}: {tab_result['created']} created, "
                        f"{tab_result['skipped']} skipped"
                    )
                else:
                    logger.error(f"  ✗ {tab_result['name']}: {tab_result['error']}")

            logger.info(
                f"Total albums: {created_count} created, {updated_count} updated, "
                f"{skipped_count} skipped, {failed_count} failed"
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
