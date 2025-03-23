from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Any, Dict
import os
from datetime import datetime

from webseed.utils.logging import get_logger

logger = get_logger(__name__)


class OutputFormat(Enum):
    """Enumeration of supported output formats."""
    MARKDOWN = 'markdown'
    TAGGED = 'tagged'
    IMG = 'img'
    
    @classmethod
    def from_string(cls, format_str: str) -> 'OutputFormat':
        """
        Convert a string to an OutputFormat enum.
        
        Args:
            format_str: String representation of the format
            
        Returns:
            Corresponding OutputFormat enum value
        """
        format_str = format_str.lower()
        if format_str == 'markdown':
            return cls.MARKDOWN
        elif format_str == 'tagged':
            return cls.TAGGED
        elif format_str == 'img':
            return cls.IMG
        else:
            raise ValueError(f"Unknown format: {format_str}")
    
    def format(self, content: str, url: str) -> str:
        """
        Format content based on the selected format.
        
        Args:
            content: Content to format
            url: URL source of the content
            
        Returns:
            Formatted content
        """
        from webseed.sources.web.extractor import parse_html_content
        
        if self == OutputFormat.MARKDOWN:
            return parse_html_content(content, url, 'markdown')
        elif self == OutputFormat.TAGGED:
            return parse_html_content(content, url, 'tagged')
        else:
            # For image output, this is handled by the ImageProcessor
            return content


class BaseOutput(ABC):
    """Base class for all output handlers."""
    
    def __init__(self, output_path: str, custom_name: Optional[str] = None):
        """
        Initialize the output handler.
        
        Args:
            output_path: Directory to save output to
            custom_name: Custom name for the output file
        """
        self.output_path = output_path
        self.custom_name = custom_name
    
    @abstractmethod
    def save(self, content: List[str]) -> None:
        """
        Save content to the output destination.
        
        Args:
            content: List of content to save
        """
        pass
    
    def get_filename(self, extension: str) -> str:
        """
        Generate a filename for the output.
        
        Args:
            extension: File extension (e.g., 'md', 'txt')
            
        Returns:
            Full file path
        """
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{self.custom_name or 'webseed'}_{date}.{extension}"
        return os.path.join(self.output_path, filename)