import os
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime
from typing import Optional, Set, List, Tuple, Dict

from webseed.utils.logging import get_logger
from webseed.processors.base import BaseProcessor

logger = get_logger(__name__)


class ImageProcessor(BaseProcessor):
    """Processor for extracting and downloading images from HTML content."""
    
    def __init__(
        self,
        base_url: str,
        output_path: str = os.getcwd(),
        custom_name: Optional[str] = None
    ):
        """
        Initialize the image processor.
        
        Args:
            base_url: The base URL for resolving relative image URLs
            output_path: Path to save downloaded images
            custom_name: Custom name prefix for the image directory
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.output_path = output_path
        self.custom_name = custom_name
        self.processed_hashes: Set[str] = set()
        self.save_dir = self.create_image_directory()
        
    def create_image_directory(self) -> str:
        """
        Create a directory for storing images.
        
        Returns:
            Path to the created directory
        """
        date = datetime.now().strftime("%Y-%m-%d")
        dir_name = f"{self.output_path}/images/{self.custom_name or self.domain}_images_{date}"
        os.makedirs(dir_name, exist_ok=True)
        logger.info(f"Created image directory: {dir_name}")
        return dir_name
    
    @staticmethod
    def get_file_hash(content: bytes) -> str:
        """
        Generate a hash of file content to avoid duplicates.
        
        Args:
            content: The file content bytes
            
        Returns:
            MD5 hash of the content
        """
        return hashlib.md5(content).hexdigest()
    
    def download_image(self, url: str) -> Optional[str]:
        """
        Download an image if it hasn't been downloaded already.
        
        Args:
            url: URL of the image to download
            
        Returns:
            Filename of the downloaded image, or None if download failed
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Get content hash before downloading
            content = response.content
            file_hash = self.get_file_hash(content)

            # Skip if we've already downloaded this image
            if file_hash in self.processed_hashes:
                return None

            # Generate filename from hash and original extension
            original_filename = os.path.basename(urlparse(url).path)
            extension = os.path.splitext(original_filename)[1] or '.jpg'  # Default to .jpg if no extension
            filename = f"{file_hash}{extension}"
            filepath = os.path.join(self.save_dir, filename)

            # Save the image
            with open(filepath, 'wb') as f:
                f.write(content)

            self.processed_hashes.add(file_hash)
            return filename
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    def process(self, html_content: str) -> str:
        """
        Extract and download all images from the HTML content.
        
        Args:
            html_content: HTML content to process
            
        Returns:
            Report of downloaded images
        """
        if not html_content:
            return "No HTML content to process"

        soup = BeautifulSoup(html_content, 'html.parser')
        downloaded_images = []

        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue

            # Convert relative URLs to absolute URLs
            if not src.startswith(('http://', 'https://')):
                src = urljoin(self.base_url, src)

            # Download the image
            filename = self.download_image(src)
            if filename:
                downloaded_images.append((src, filename))

        # Generate report
        if not downloaded_images:
            return f"No images downloaded from {self.base_url}"
        
        report = f"Downloaded {len(downloaded_images)} images from {self.base_url}:\n\n"
        for i, (src, filename) in enumerate(downloaded_images, 1):
            report += f"{i}. Original: {src}\n   Saved as: {filename}\n\n"
        
        report += f"All images saved to: {self.save_dir}\n"
        return report