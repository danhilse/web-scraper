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

def get_formatter(format_type: str, **kwargs) -> Optional[BaseFormatter]:
    """
    Get a formatter by type.
    
    Args:
        format_type (str): The formatter type (markdown, xml, raw, html)
        **kwargs: Additional arguments to pass to the formatter constructor
        
    Returns:
        BaseFormatter: A formatter instance
        
    Raises:
        ValueError: If the format type is not supported
    """
    format_type = format_type.lower()
    formatter_class = FORMATTERS.get(format_type)
    
    if not formatter_class:
        logger.error(f"Unsupported format type: {format_type}")
        raise ValueError(f"Unsupported format type: {format_type}")
    
    # Configure formatter based on type
    if format_type == "raw":
        # For raw format, set HTML formatter options to minimize processing
        kwargs.update({
            "clean_html": True,
            "add_boilerplate": False,
            "add_css": False
        })
    
    # Create and return formatter instance
    return formatter_class(**kwargs)