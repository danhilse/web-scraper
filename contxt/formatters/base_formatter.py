import logging
import re
from pathlib import Path
from urllib.parse import urlparse
import pyperclip

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
    
    def save_to_file(self, formatted_content, url, output_dir=None, extension=None):
        """
        Save formatted content to a file.
        
        Args:
            formatted_content (str): Formatted content to save
            url (str): Source URL
            output_dir (str, optional): Output directory
            extension (str, optional): File extension to use
            
        Returns:
            str: Path to the saved file
        """
        # Create a filename based on the URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path.rstrip("/")
        
        if not path:
            path = "index"
        else:
            path = path.replace("/", "_").lstrip("_")
        
        filename = f"{domain}_{path}"
        
        # Clean up filename and limit length
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = filename[:100]  # Limit filename length
        
        # Add extension if provided
        if extension:
            if not extension.startswith('.'):
                extension = f".{extension}"
            filename += extension
        
        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.cwd()
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save the file
        file_path = output_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        
        logger.info(f"Saved formatted content to {file_path}")
        return str(file_path)
    
    def copy_to_clipboard(self, formatted_content):
        """
        Copy formatted content to clipboard.
        
        Args:
            formatted_content (str): Formatted content to copy
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            pyperclip.copy(formatted_content)
            logger.info("Copied formatted content to clipboard")
            return True
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return False
    
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