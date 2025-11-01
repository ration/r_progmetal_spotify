# Test Data

This directory contains test fixtures for unit and integration tests.

## Files

### `progmetal_releases_2025.xlsx`

Snapshot of the r/progmetal 2025 releases spreadsheet in XLSX format.

- **Source**: https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/edit?gid=803985331
- **Format**: XLSX (preserves Spotify hyperlinks)
- **Albums**: 2,556 entries
- **Updated**: 2025-11-01

This file is used for testing:
- Google Sheets XLSX parser
- Spotify URL extraction
- Album import pipeline
- Data validation

## Updating Test Data

To update the test data with latest spreadsheet content:

```bash
curl -L "https://docs.google.com/spreadsheets/d/1fQFg52uaojpRCz29EzSHVpsX5SYVJ2VN8IuKs9XA5W8/export?format=xlsx&gid=803985331" \
  -o tests/testdata/progmetal_releases_2025.xlsx
```
