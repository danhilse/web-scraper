"""
Formatters package for contxt.
"""
import logging
from typing import Dict, Type, Optional
from .base_formatter import BaseFormatter
from .markdown_formatter import MarkdownFormatter
from .xml_formatter import XMLFormatter
from .html_formatter import HTMLFormatter

__all__ = ["get_formatter", "BaseFormatter", "MarkdownFormatter", "XMLFormatter", "HTMLFormatter"]

logger = logging.getLogger(__name__)

# Formatter registry
FORMATTERS: Dict[str, Type[BaseFormatter]] = {
    "markdown": MarkdownFormatter,
    "xml": XMLFormatter,
    "raw": HTMLFormatter,  # "raw" format is handled by the HTML formatter with minimal processing
    "html": HTMLFormatter,  # Alternative name for the same formatter
}

def get_formatter(format_type, include_images=False, image_map=None):
    """Get the appropriate formatter based on the format type."""
    if format_type == "markdown":
        from .markdown_formatter import MarkdownFormatter
        return MarkdownFormatter(include_images, image_map)
    elif format_type == "xml":
        from .xml_formatter import XMLFormatter
        return XMLFormatter(include_images, image_map)
    elif format_type == "raw":
        from .html_formatter import HTMLFormatter
        return HTMLFormatter(include_images, image_map, clean_html=True, 
                           add_boilerplate=False, add_css=False)
    elif format_type == "youtube":
        from .youtube_formatter import YouTubeFormatter
        return YouTubeFormatter(include_images, image_map)
    else:
        # Default to markdown for unknown types
        from .markdown_formatter import MarkdownFormatter
        return MarkdownFormatter(include_images, image_map)