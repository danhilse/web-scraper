import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_valid_url(url):
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def sanitize_filename(filename):
    """Sanitize a string to be used as a filename."""
    # Remove invalid characters
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    filename = re.sub(r'\s+', "_", filename)
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename