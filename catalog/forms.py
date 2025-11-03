"""
Forms for catalog filtering and search functionality.
"""
from django import forms


class SearchForm(forms.Form):
    """
    Form for free-text search across album catalog.

    Validates that search queries are at least 3 characters long.
    """
    query = forms.CharField(
        min_length=3,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full",
            "placeholder": "Search albums, artists, genres...",
            "type": "search",
            "name": "q",
            "id": "search-input"
        })
    )

    def clean_query(self):
        """
        Clean and validate search query.

        Returns empty string if query is less than 3 characters.
        """
        query = self.cleaned_data.get("query", "").strip()
        if len(query) < 3:
            return ""  # Ignore queries shorter than 3 characters
        return query
