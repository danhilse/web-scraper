import logging

logger = logging.getLogger(__name__)

class BaseFormatter:
    """
    Base class for content formatters with common functionality.
    """
    
    def __init__(self, include_images=False, image_map=None):
        """
        Initialize the base formatter.
        
        Args:
            include_images (bool): Whether to include image references
            image_map (dict): Mapping from image URLs to local file paths
        """
        self.include_images = include_images
        self.image_map = image_map or {}
    
    def format(self, scraped_data):
        """
        Format the scraped data. To be implemented by subclasses.
        
        Args:
            scraped_data (dict): Data from the scraper
            
        Returns:
            str: Formatted content
        """
        raise NotImplementedError("Subclasses must implement the format method.")
    
    def get_extension(self):
        """
        Get the file extension for this formatter type.
        To be implemented by subclasses.
        
        Returns:
            str: File extension (without dot)
        """
        raise NotImplementedError("Subclasses must implement the get_extension method.")
    
    def extract_metadata(self, scraped_data):
        """
        Extract common metadata from scraped data.
        
        Args:
            scraped_data (dict): Scraped data
            
        Returns:
            dict: Extracted metadata
        """
        metadata = {
            "title": scraped_data.get("title", ""),
            "url": scraped_data.get("url", ""),
            "og_metadata": scraped_data.get("og_metadata", {})
        }
        
        return metadata