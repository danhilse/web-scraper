from .markdown_formatter import MarkdownFormatter
from .xml_formatter import XMLFormatter
from .html_formatter import HTMLFormatter
from .youtube_formatter import YouTubeFormatter

def get_formatter(format_type="markdown", include_images=False, image_map=None, youtube_format_style="complete"):
    """
    Factory function to get the appropriate formatter for the output format.
    
    Args:
        format_type (str): The format type ('markdown', 'xml', 'raw', or 'youtube')
        include_images (bool): Whether to include images
        image_map (dict): Mapping of image URLs to local file paths
        youtube_format_style (str): Style for YouTube formatter ('complete', 'raw', 'chapters')
        
    Returns:
        BaseFormatter: The formatter instance
    """
    if format_type == "markdown":
        return MarkdownFormatter(include_images=include_images, image_map=image_map)
    elif format_type == "xml":
        return XMLFormatter(include_images=include_images, image_map=image_map)
    elif format_type == "raw":
        return HTMLFormatter(include_images=include_images, image_map=image_map)
    elif format_type == "youtube":
        return YouTubeFormatter(format_style=youtube_format_style, include_images=include_images, image_map=image_map)
    else:
        # Default to markdown
        return MarkdownFormatter(include_images=include_images, image_map=image_map)