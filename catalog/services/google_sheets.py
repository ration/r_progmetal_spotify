"""
Google Sheets XLSX fetcher service.

This module provides functionality to fetch XLSX data from Google Sheets export URLs.
Unlike CSV exports, XLSX format preserves hyperlinks, allowing us to extract Spotify URLs.
"""

import logging
import requests
import re
from typing import List, Dict, Optional
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Service for fetching XLSX data from Google Sheets export URLs.

    XLSX format preserves hyperlinks, allowing extraction of Spotify URLs.

    Attributes:
        xlsx_url: The Google Sheets XLSX export URL
    """

    # Expected column names from the r/progmetal releases sheet
    EXPECTED_COLUMNS = {
        "Artist",
        "Album",
        "Release Date",
        "Length",
        "Genre / Subgenres",
        "Vocal Style",
        "Country / State",
        "Spotify",
    }

    def __init__(self, xlsx_url: str):
        """
        Initialize the Google Sheets service.

        Args:
            xlsx_url: Google Sheets XLSX export URL (must be publicly accessible)
        """
        self.xlsx_url = xlsx_url
        logger.info(f"Initialized GoogleSheetsService with URL: {xlsx_url}")

    def _extract_url_from_cell(self, cell) -> Optional[str]:
        """
        Extract URL from cell that might have hyperlink or HYPERLINK formula.

        Args:
            cell: openpyxl cell object

        Returns:
            URL string if found, None otherwise
        """
        # Check if cell has a hyperlink object
        if cell.hyperlink:
            return cell.hyperlink.target

        # Check if cell value is a HYPERLINK formula
        if (
            cell.value
            and isinstance(cell.value, str)
            and cell.value.startswith("=HYPERLINK")
        ):
            # Extract URL from =HYPERLINK("url", "text") formula
            match = re.search(r'=HYPERLINK\("([^"]+)"', cell.value)
            if match:
                return match.group(1)

        return None

    def _find_header_row(self, worksheet) -> int:
        """
        Find the header row in the worksheet (row with 'Artist' in first column).

        Args:
            worksheet: openpyxl worksheet object

        Returns:
            Row number (1-indexed) of the header row

        Raises:
            ValueError: If header row cannot be found
        """
        for row_idx in range(1, 20):  # Check first 20 rows
            first_cell = worksheet.cell(row=row_idx, column=1).value
            if first_cell == "Artist":
                logger.debug(f"Found header row at row {row_idx}")
                return row_idx

        raise ValueError("Could not find header row with 'Artist' column")

    def fetch_albums(self) -> List[Dict[str, str]]:
        """
        Fetch and parse album data from Google Sheets XLSX export.

        Returns:
            List of album dictionaries with normalized field names:
            - artist: Artist name
            - album: Album title
            - release_date: Release date string (e.g., "January 1")
            - genre: Genre/subgenre text
            - vocal_style: Vocal style text
            - country: Country or state
            - spotify_url: Full Spotify album URL

        Raises:
            requests.RequestException: If HTTP request fails
            ValueError: If required columns are missing or parsing fails
        """
        logger.info(f"Fetching XLSX from Google Sheets: {self.xlsx_url}")

        try:
            response = requests.get(self.xlsx_url, timeout=30)
            response.raise_for_status()

            # Load workbook from bytes
            xlsx_content = BytesIO(response.content)
            workbook = load_workbook(xlsx_content)
            worksheet = workbook.active

            # Find header row
            header_row = self._find_header_row(worksheet)

            # Get column headers
            headers = []
            col_idx = 1
            while True:
                cell_value = worksheet.cell(row=header_row, column=col_idx).value
                if cell_value is None:
                    break
                headers.append(cell_value)
                col_idx += 1

            logger.debug(f"Found {len(headers)} columns: {headers}")

            # Create column index mapping
            col_mapping = {header: idx + 1 for idx, header in enumerate(headers)}

            # Validate required columns
            missing_columns = self.EXPECTED_COLUMNS - set(headers)
            if missing_columns:
                logger.warning(
                    f"Sheet missing some expected columns: {missing_columns}. "
                    f"Available columns: {headers}"
                )

            # Parse data rows
            albums = []
            row_idx = header_row + 1
            while True:
                artist_cell = worksheet.cell(row=row_idx, column=col_mapping["Artist"])
                artist = artist_cell.value

                # Stop if we hit empty rows
                if not artist:
                    break

                album_cell = worksheet.cell(row=row_idx, column=col_mapping["Album"])
                album = album_cell.value

                # Skip rows without album name
                if not album:
                    row_idx += 1
                    continue

                # Extract Spotify URL
                spotify_cell = worksheet.cell(
                    row=row_idx, column=col_mapping["Spotify"]
                )
                spotify_url = self._extract_url_from_cell(spotify_cell)

                # Skip rows without Spotify URL
                if not spotify_url:
                    row_idx += 1
                    continue

                # Extract other fields
                normalized = {
                    "artist": str(artist).strip(),
                    "album": str(album).strip(),
                    "release_date": str(
                        worksheet.cell(
                            row=row_idx, column=col_mapping.get("Release Date", 0)
                        ).value
                        or ""
                    ).strip(),
                    "genre": str(
                        worksheet.cell(
                            row=row_idx, column=col_mapping.get("Genre / Subgenres", 0)
                        ).value
                        or ""
                    ).strip(),
                    "vocal_style": str(
                        worksheet.cell(
                            row=row_idx, column=col_mapping.get("Vocal Style", 0)
                        ).value
                        or ""
                    ).strip(),
                    "country": str(
                        worksheet.cell(
                            row=row_idx, column=col_mapping.get("Country / State", 0)
                        ).value
                        or ""
                    ).strip(),
                    "spotify_url": spotify_url,
                }

                albums.append(normalized)
                row_idx += 1

            logger.info(
                f"Successfully fetched {len(albums)} albums with Spotify URLs "
                f"from Google Sheets"
            )

            return albums

        except requests.RequestException as e:
            logger.error(f"Failed to fetch XLSX from Google Sheets: {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to parse XLSX data: {e}")
            raise

    def parse_release_date(self, date_str: str, year: int = None) -> datetime.date:
        """
        Parse release date string from Google Sheets.

        The sheet uses formats like "January 1", "May 15" without year.
        This method attempts to parse and add the year if provided.

        Args:
            date_str: Date string from CSV (e.g., "January 1")
            year: Year to use if not present in date_str (defaults to current year)

        Returns:
            datetime.date object, or None if parsing fails

        Note:
            Returns None for unparseable dates rather than raising exceptions
        """
        if not date_str:
            return None

        # Use current year if not specified
        if year is None:
            year = datetime.now().year

        try:
            # Try parsing "Month Day" format (e.g., "January 1")
            date_str_with_year = f"{date_str}, {year}"
            parsed = datetime.strptime(date_str_with_year, "%B %d, %Y")
            return parsed.date()
        except ValueError:
            try:
                # Try "Month" only format (e.g., "January")
                date_str_with_year = f"{date_str} 1, {year}"
                parsed = datetime.strptime(date_str_with_year, "%B %d, %Y")
                return parsed.date()
            except ValueError:
                logger.warning(f"Could not parse release date: {date_str}")
                return None
