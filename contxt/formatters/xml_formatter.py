from bs4 import BeautifulSoup, Tag
import xml.etree.ElementTree as ET
import xml.dom.minidom
import re
import logging
import html
from .base_formatter import BaseFormatter

logger = logging.getLogger(__name__)

class XMLFormatter(BaseFormatter):
    """
    XML formatter for web content that preserves hierarchical structure.
    """
    
    def __init__(self, include_images=False, image_map=None, simplify_structure=True, preserve_attrs=False):
        """
        Initialize the XML formatter.
        
        Args:
            include_images (bool): Whether to include image references
            image_map (dict): Mapping from image URLs to local file paths
            simplify_structure (bool): Whether to simplify HTML structure to semantic XML
            preserve_attrs (bool): Whether to preserve HTML attributes in the XML
        """
        super().__init__(include_images, image_map)
        self.simplify_structure = simplify_structure
        self.preserve_attrs = preserve_attrs
        
        # Define mapping for HTML tags to simplified XML tags
        self.tag_mapping = {
            # Headings
            'h1': 'h1',
            'h2': 'h2',
            'h3': 'h3',
            'h4': 'h4',
            'h5': 'h5',
            'h6': 'h6',
            
            # Containers
            'article': 'article',
            'section': 'section',
            'main': 'main',
            'div': 'div',
            'aside': 'aside',
            'header': 'header',
            'footer': 'footer',
            'nav': 'nav',
            
            # Content blocks
            'p': 'p',
            'blockquote': 'blockquote',
            'pre': 'pre',
            'code': 'code',
            
            # Lists
            'ul': 'ul',
            'ol': 'ol',
            'li': 'li',
            
            # Tables
            'table': 'table',
            'thead': 'thead',
            'tbody': 'tbody',
            'tfoot': 'tfoot',
            'tr': 'tr',
            'th': 'th',
            'td': 'td',
            
            # Inline elements
            'a': 'a',
            'span': 'span',
            'strong': 'strong',
            'em': 'em',
            'b': 'b',
            'i': 'i',
            'u': 'u',
            'mark': 'mark',
            
            # Media
            'img': 'img',
            'figure': 'figure',
            'figcaption': 'figcaption',
            'picture': 'picture',
            'video': 'video',
            'audio': 'audio',
            
            # Other
            'hr': 'hr',
            'br': 'br'
        }
        
        # Tags to skip (not include in output)
        self.skip_tags = {
            'script', 'style', 'noscript', 'iframe', 'svg', 'canvas', 'meta',
            'link', 'input', 'button', 'form', 'template'
        }
        
        # Important attributes to preserve
        self.important_attrs = {
            'id', 'class', 'href', 'src', 'alt', 'title', 'aria-label', 'role'
        }
    
    def format(self, scraped_data):
        """
        Format scraped data as XML with preserved hierarchy.
        
        Args:
            scraped_data (dict): Data from the scraper
            
        Returns:
            str: Formatted XML content
        """
        if not scraped_data["content"]:
            return f'<?xml version="1.0" ?>\n<error url="{self._escape_attr(scraped_data["url"])}">{self._escape_text(scraped_data["title"])}</error>'
        
        # Extract metadata
        metadata = self.extract_metadata(scraped_data)
        
        # Parse HTML if string is provided
        html_content = scraped_data["content"]
        if isinstance(html_content, str):
            soup = BeautifulSoup(html_content, "html.parser")
        elif isinstance(html_content, BeautifulSoup):
            soup = html_content
        else:
            soup = BeautifulSoup(str(html_content), "html.parser")
        
        # Create root element
        root = ET.Element("content")
        
        # Add metadata
        meta_elem = ET.SubElement(root, "metadata")
        title_elem = ET.SubElement(meta_elem, "title")
        title_elem.text = self._escape_text(metadata["title"])
        url_elem = ET.SubElement(meta_elem, "url")
        url_elem.text = self._escape_text(metadata["url"])
        
        # Add OpenGraph metadata if available
        og_metadata = metadata["og_metadata"]
        if og_metadata:
            og_elem = ET.SubElement(meta_elem, "open_graph")
            
            if "og_title" in og_metadata:
                og_title = ET.SubElement(og_elem, "title")
                og_title.text = self._escape_text(og_metadata["og_title"])
                
            if "og_description" in og_metadata:
                og_desc = ET.SubElement(og_elem, "description")
                og_desc.text = self._escape_text(og_metadata["og_description"])
                
            if "og_image" in og_metadata:
                og_image = ET.SubElement(og_elem, "image")
                og_image.text = self._escape_text(og_metadata["og_image"])
        
        # Add body element
        body = ET.SubElement(root, "body")
        
        # Process main content
        self._process_element(soup, body)
        
        # Clean up the XML structure
        self._clean_xml_structure(body)
        
        # Add images if requested
        if self.include_images and scraped_data["images"]:
            images_elem = ET.SubElement(root, "images")
            for img in scraped_data["images"]:
                image = ET.SubElement(images_elem, "image")
                
                # Check if we have a local path for this image
                if img["url"] in self.image_map:
                    path_elem = ET.SubElement(image, "path")
                    path_elem.text = self._escape_text(self.image_map[img["url"]])
                else:
                    url_elem = ET.SubElement(image, "url")
                    url_elem.text = self._escape_text(img["url"])
                
                alt_elem = ET.SubElement(image, "alt")
                alt_elem.text = self._escape_text(img["alt"])
                
                # Add dimensions if available
                if "dimensions" in img and img["dimensions"]:
                    dimensions = ET.SubElement(image, "dimensions")
                    for key, value in img["dimensions"].items():
                        dimensions.set(key, str(value))
        
        try:
            # Convert to pretty-printed XML string
            xml_str = ET.tostring(root, encoding="unicode")
            # Further escape any problematic XML characters that ElementTree might miss
            xml_str = self._clean_xml_string(xml_str)
            
            try:
                dom = xml.dom.minidom.parseString(f'<?xml version="1.0" ?>\n{xml_str}')
                return dom.toprettyxml(indent="  ")
            except Exception as e:
                logger.warning(f"XML pretty-printing failed: {e}. Using basic format.")
                return f'<?xml version="1.0" ?>\n{xml_str}'
        except Exception as e:
            logger.error(f"Error generating XML: {e}")
            # Fallback to a very simple XML structure with error info
            return f'''<?xml version="1.0" ?>
<content>
  <metadata>
    <title>{self._escape_text(metadata["title"])}</title>
    <url>{self._escape_text(metadata["url"])}</url>
  </metadata>
  <body>
    <error>Failed to generate XML: {self._escape_text(str(e))}</error>
  </body>
</content>'''
    
    def _process_element(self, element, parent_xml):
        """
        Recursively process HTML elements and add them to the XML tree.
        
        Args:
            element: BeautifulSoup element to process
            parent_xml: Parent XML element to add to
        """
        # Skip if not an element node
        if not isinstance(element, Tag):
            if element.string and element.string.strip():
                text = element.string.strip()
                # Escape text content for XML
                safe_text = self._escape_text(text)
                
                if parent_xml.text is None:
                    parent_xml.text = safe_text
                else:
                    parent_xml.text += " " + safe_text
            return
        
        # Skip unwanted tags
        if element.name in self.skip_tags:
            return
        
        # Skip empty containers with no text content
        if element.name not in ['img', 'br', 'hr'] and not element.get_text(strip=True):
            return
        
        # Map the tag name or use the original if not in mapping
        if self.simplify_structure and element.name in self.tag_mapping:
            tag_name = self.tag_mapping[element.name]
        else:
            # Ensure tag name is valid for XML
            tag_name = self._sanitize_tag_name(element.name)
        
        # Create a new XML element
        new_element = ET.SubElement(parent_xml, tag_name)
        
        # Add attributes if needed
        if self.preserve_attrs:
            for attr, value in element.attrs.items():
                # Sanitize attribute name for XML
                attr = self._sanitize_attr_name(attr)
                
                if isinstance(value, list):
                    value = ' '.join(value)
                elif not isinstance(value, str):
                    value = str(value)
                
                # Escape attribute value
                new_element.set(attr, self._escape_attr(value))
        else:
            # Only preserve important attributes
            for attr in self.important_attrs:
                if attr in element.attrs:
                    # Sanitize attribute name for XML
                    attr = self._sanitize_attr_name(attr)
                    
                    value = element.attrs[attr]
                    if isinstance(value, list):
                        value = ' '.join(value)
                    elif not isinstance(value, str):
                        value = str(value)
                    
                    # Escape attribute value
                    new_element.set(attr, self._escape_attr(value))
        
        # Process child elements
        for child in element.children:
            self._process_element(child, new_element)
    
    def _clean_xml_structure(self, element):
        """
        Clean up the XML structure by removing unnecessary nesting and empty elements.
        
        Args:
            element: XML element to clean
        """
        # Remove elements with no content
        children_to_remove = []
        for child in element:
            # Recursive cleaning of child elements
            self._clean_xml_structure(child)
            
            # Check if child is empty (no text and no children)
            if (child.tag not in ['img', 'br', 'hr'] and 
                not child.text and 
                not child.tail and 
                len(child) == 0):
                children_to_remove.append(child)
        
        # Remove the identified empty elements
        for child in children_to_remove:
            element.remove(child)
        
        # Normalize whitespace in text content
        if element.text:
            element.text = re.sub(r'\s+', ' ', element.text).strip()
        
        for child in element:
            if child.tail:
                child.tail = re.sub(r'\s+', ' ', child.tail).strip()
    
    def _escape_text(self, text):
        """
        Escape text for use in XML content.
        
        Args:
            text (str): Text to escape
            
        Returns:
            str: Escaped text
        """
        if not text:
            return ""
        
        # Use html.escape to properly handle XML entities
        return html.escape(str(text))
    
    def _escape_attr(self, text):
        """
        Escape text for use in XML attributes.
        
        Args:
            text (str): Text to escape
            
        Returns:
            str: Escaped text
        """
        if not text:
            return ""
        
        # Use html.escape with quote=True to handle quotes in attributes
        return html.escape(str(text), quote=True)
    
    def _sanitize_tag_name(self, name):
        """
        Sanitize tag names to ensure they're valid XML names.
        
        Args:
            name (str): Tag name to sanitize
            
        Returns:
            str: Sanitized tag name
        """
        # XML tags must start with a letter or underscore, not a number or symbol
        if not name:
            return "tag"
            
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # Ensure it starts with a letter or underscore
        if not re.match(r'^[a-zA-Z_]', sanitized):
            sanitized = 'tag_' + sanitized
            
        return sanitized
    
    def _sanitize_attr_name(self, name):
        """
        Sanitize attribute names to ensure they're valid XML names.
        
        Args:
            name (str): Attribute name to sanitize
            
        Returns:
            str: Sanitized attribute name
        """
        # Handle common HTML attributes that aren't valid in XML
        if name == 'class':
            return 'class_attr'
        if name == 'for':
            return 'for_attr'
            
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # Ensure it starts with a letter or underscore
        if not re.match(r'^[a-zA-Z_]', sanitized):
            sanitized = 'attr_' + sanitized
            
        return sanitized
    
    def _clean_xml_string(self, xml_str):
        """
        Additional cleaning of the XML string to handle problematic characters.
        
        Args:
            xml_str (str): XML string to clean
            
        Returns:
            str: Cleaned XML string
        """
        # Replace any control characters except for whitespace
        xml_str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_str)
        
        # Handle any invalid XML 1.0 characters
        xml_str = re.sub(r'[\uD800-\uDFFF]', '', xml_str)
        
        return xml_str

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
        return super().save_to_file(formatted_content, url, output_dir, extension="xml")
    
    def get_extension(self):
        """Get the file extension for XML."""
        return "xml"