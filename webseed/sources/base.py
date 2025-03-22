"""
Base class for all source handlers.
"""

from abc import ABC, abstractmethod

class SourceHandler(ABC):
    """Abstract base class for all source handlers."""
    
    def __init__(self, config=None):
        """Initialize the source handler with optional configuration."""
        self.config = config or {}
        
    @abstractmethod
    def validate_source(self, source):
        """
        Validate that the source is supported by this handler.
        
        Args:
            source: URL or identifier for the source
            
        Returns:
            bool: True if the source is supported, False otherwise
        """
        pass
        
    @abstractmethod
    def extract(self, source):
        """
        Extract content from the source.
        
        Args:
            source: URL or identifier for the source
            
        Returns:
            dict: Extracted raw content and metadata
        """
        pass
