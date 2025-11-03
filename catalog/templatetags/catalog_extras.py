"""
Custom template tags and filters for catalog app.
"""
from django import template
from django.http import QueryDict

register = template.Library()


@register.simple_tag
def url_replace(request, **kwargs):
    """
    Update URL query parameters while preserving existing ones.

    Usage in templates:
        <a href="?{% url_replace request page=2 %}">Page 2</a>

    Args:
        request: Django HttpRequest object with GET parameters
        **kwargs: Key-value pairs to add/update in query string

    Returns:
        str: URL-encoded query string with updated parameters
    """
    # Create a mutable copy of the current query parameters
    params = request.GET.copy()

    # Update parameters with new values
    for key, value in kwargs.items():
        if value is None:
            # Remove parameter if value is None
            params.pop(key, None)
        else:
            params[key] = value

    # Return URL-encoded query string
    return params.urlencode()
