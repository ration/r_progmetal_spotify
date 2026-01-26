"""Context processors for the Album Catalog application."""

from django.conf import settings
from typing import Dict, Any


def site_settings(request) -> Dict[str, Any]:
    """
    Add site-wide settings to template context.

    Makes configuration values available in all templates without
    needing to pass them explicitly from each view.

    Returns:
        Dict[str, Any]: Dictionary with site configuration values
    """
    # Extract base Google Sheets URL (remove /export?... part)
    sheets_url = settings.GOOGLE_SHEETS_XLSX_URL
    if "/export" in sheets_url:
        sheets_base_url = sheets_url.split("/export")[0]
    else:
        sheets_base_url = sheets_url

    return {
        "GOOGLE_SHEETS_URL": sheets_base_url,
        "DISCORD_URL": "https://discord.gg/prog",
    }
