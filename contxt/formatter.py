from bs4 import BeautifulSoup
import re
import os
from pathlib import Path
from urllib.parse import urlparse
import markdownify
import xml.etree.ElementTree as ET
import xml.dom.minidom
import pyperclip
import logging

logger = logging.getLogger(__name__)

class Formatter:
    def __init__(self, format_type="markdown", include_images=False, image_map=None):
        """
        Initialize the formatter.
        
        Args:
            format_type (str): Output format type ("markdown", "xml", or "raw")
            include_images (bool): Whether to include image references
            image_map (dict): Mapping from image URLs to local file paths
        """
        self.format_type = format_type
        self.include_images = include_images
        self.image_map = image_map or {}
    
    def format(self, scraped_data):
        """
        Format the scraped data into the selected format.
        
        Args:
            scraped_data (dict): Data from the scraper
            
        Returns:
            str: Formatted content
        """
        if self.format_type == "markdown":
            return self._format_markdown(scraped_data)
        elif self.format_type == "xml":
            return self._format_xml(scraped_data)
        elif self.format_type == "raw":
            return self._format_raw(scraped_data)
        else:
            raise ValueError(f"Unsupported format type: {self.format_type}")
    
    def _format_markdown(self, scraped_data):
        """Format content as Markdown."""
        if not scraped_data["content"]:
            return f"# Error fetching content from {scraped_data['url']}\n\n{scraped_data['title']}"
        
        # Convert HTML to Markdown
        md = markdownify.markdownify(str(scraped_data["content"]), heading_style="ATX")
        
        # Clean up the markdown
        md = self._clean_markdown(md)
        
        # Add metadata
        result = f"# {scraped_data['title']}\n\n"
        result += f"Source: {scraped_data['url']}\n\n"
        
        # Add OpenGraph metadata if available
        og_metadata = scraped_data.get("og_metadata", {})
        if og_metadata:
            if "og_title" in og_metadata and og_metadata["og_title"] != scraped_data["title"]:
                result += f"**OpenGraph Title:** {og_metadata['og_title']}\n\n"
                
            if "og_description" in og_metadata:
                result += f"**Description:** {og_metadata['og_description']}\n\n"
        
        # Add processing information
        result += f"Estimated token count: {scraped_data.get('token_count', 'Unknown')}\n"
        if scraped_data.get("processing_time"):
            result += f"Processing time: {scraped_data['processing_time']:.2f} seconds\n\n"
        else:
            result += "\n"
            
        # Add separator
        result += "---\n\n"
        
        # Add content
        result += md
        
        # Add images if requested
        if self.include_images and scraped_data["images"]:
            result += "\n\n## Images\n\n"
            
            for img in scraped_data["images"]:
                img_url = img["url"]
                img_alt = img["alt"]
                
                # Check if we have a local path for this image
                if img_url in self.image_map:
                    local_path = self.image_map[img_url]
                    result += f"![{img_alt}]({local_path})"
                    
                    # Add dimensions if available
                    if "dimensions" in img and img["dimensions"]:
                        dimensions = img["dimensions"]
                        if "width" in dimensions and "height" in dimensions:
                            result += f" (Width: {dimensions['width']}, Height: {dimensions['height']})"
                    
                    result += "\n\n"
                else:
                    result += f"![{img_alt}]({img_url})\n\n"
        
        return result
    
    def _format_xml(self, scraped_data):
        """Format content as XML."""
        if not scraped_data["content"]:
            return f'<error url="{scraped_data["url"]}">{scraped_data["title"]}</error>'
        
        # Create root element
        root = ET.Element("content")
        
        # Add metadata
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "title").text = scraped_data["title"]
        ET.SubElement(metadata, "url").text = scraped_data["url"]
        ET.SubElement(metadata, "token_count").text = str(scraped_data.get("token_count", 0))
        
        # Process the content
        soup = BeautifulSoup(str(scraped_data["content"]), "html.parser")
        
        # Add body
        body = ET.SubElement(root, "body")
        
        # Process headings
        for i in range(1, 7):
            for heading in soup.find_all(f"h{i}"):
                h = ET.SubElement(body, f"h{i}")
                h.text = heading.get_text().strip()
        
        # Process paragraphs
        for p in soup.find_all("p"):
            para = ET.SubElement(body, "p")
            para.text = p.get_text().strip()
        
        # Process lists
        for ul in soup.find_all("ul"):
            list_elem = ET.SubElement(body, "ul")
            for li in ul.find_all("li"):
                item = ET.SubElement(list_elem, "li")
                item.text = li.get_text().strip()
        
        # Process ordered lists
        for ol in soup.find_all("ol"):
            list_elem = ET.SubElement(body, "ol")
            for li in ol.find_all("li"):
                item = ET.SubElement(list_elem, "li")
                item.text = li.get_text().strip()
        
        # Add images if requested
        if self.include_images and scraped_data["images"]:
            images = ET.SubElement(root, "images")
            for img in scraped_data["images"]:
                image = ET.SubElement(images, "image")
                
                # Check if we have a local path for this image
                if img["url"] in self.image_map:
                    ET.SubElement(image, "path").text = self.image_map[img["url"]]
                else:
                    ET.SubElement(image, "url").text = img["url"]
                
                ET.SubElement(image, "alt").text = img["alt"]
        
        # Convert to pretty-printed XML string
        xml_str = ET.tostring(root, encoding="unicode")
        dom = xml.dom.minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")
    
    def _format_raw(self, scraped_data):
        """Format content as clean HTML."""
        if not scraped_data["content"]:
            return f"<!-- Error fetching content from {scraped_data['url']} -->\n<h1>{scraped_data['title']}</h1>"
        
        # Add metadata as HTML comments
        result = f"<!-- Title: {scraped_data['title']} -->\n"
        result += f"<!-- Source: {scraped_data['url']} -->\n"
        result += f"<!-- Estimated token count: {scraped_data.get('token_count', 'Unknown')} -->\n\n"
        
        # Add the raw HTML content
        result += scraped_data["raw_html"]
        
        # Add images if requested
        if self.include_images and scraped_data["images"]:
            result += "\n\n<h2>Images</h2>\n\n"
            for img in scraped_data["images"]:
                img_url = img["url"]
                img_alt = img["alt"]
                
                # Check if we have a local path for this image
                if img_url in self.image_map:
                    local_path = self.image_map[img_url]
                    result += f'<img src="{local_path}" alt="{img_alt}" />\n'
                else:
                    result += f'<img src="{img_url}" alt="{img_alt}" />\n'
        
        return result
    
    def _clean_markdown(self, md):
        """Clean up markdown output."""
        # Remove excessive newlines
        md = re.sub(r'\n{3,}', '\n\n', md)
        
        # Fix list formatting
        md = re.sub(r'(\n\s*[-*]\s+)', r'\n* ', md)
        
        # Make relative URLs absolute for the original domain
        # (This would need more context from the original URL)
        
        return md
    
    def save_to_file(self, formatted_content, url, output_dir=None):
        """
        Save formatted content to a file.
        
        Args:
            formatted_content (str): Formatted content to save
            url (str): Source URL
            output_dir (str, optional): Output directory
            
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
        
        # Add extension based on format type
        if self.format_type == "markdown":
            filename += ".md"
        elif self.format_type == "xml":
            filename += ".xml"
        else:
            filename += ".html"
        
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
            return True
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return False