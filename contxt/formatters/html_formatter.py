import re
import logging
from bs4 import BeautifulSoup
import html
from .base_formatter import BaseFormatter

logger = logging.getLogger(__name__)

class HTMLFormatter(BaseFormatter):
    """
    Formatter for converting web content to clean HTML.
    This can be used in "raw" mode (minimal processing) or "html" mode (with boilerplate and CSS).
    """
    
    def __init__(self, include_images=False, image_map=None, clean_html=True, 
                 add_boilerplate=True, add_css=True):
        """
        Initialize the HTML formatter.
        
        Args:
            include_images (bool): Whether to include image references
            image_map (dict): Mapping from image URLs to local file paths
            clean_html (bool): Whether to clean up HTML (remove scripts, etc.)
            add_boilerplate (bool): Whether to add HTML boilerplate
            add_css (bool): Whether to add basic CSS
        """
        super().__init__(include_images, image_map)
        self.clean_html = clean_html
        self.add_boilerplate = add_boilerplate
        self.add_css = add_css
        
        # Define which elements are block-level for formatting
        self.block_elements = {
            'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'table', 'tr', 'td', 'th',
            'article', 'section', 'header', 'footer', 'nav',
            'aside', 'main', 'figure', 'figcaption', 'form',
            'pre', 'blockquote', 'hr'
        }
        
        # Define self-closing tags
        self.self_closing = {
            'img', 'br', 'hr', 'meta', 'input', 'link', 
            'area', 'base', 'col', 'embed', 'param', 'source', 
            'track', 'wbr'
        }
    
    def format(self, scraped_data):
        """
        Format scraped data as HTML.
        
        Args:
            scraped_data (dict): Data from the scraper
            
        Returns:
            str: Formatted HTML content
        """
        if not scraped_data["content"]:
            return f"<!-- Error fetching content from {scraped_data['url']} -->\n<h1>{scraped_data['title']}</h1>"
        
        # Extract metadata
        metadata = self.extract_metadata(scraped_data)
        
        # Get content
        content = scraped_data["content"]
        
        # Clean HTML if requested
        if self.clean_html:
            if isinstance(content, str):
                soup = BeautifulSoup(content, "html.parser")
            elif isinstance(content, BeautifulSoup):
                soup = content
            else:
                soup = BeautifulSoup(str(content), "html.parser")
            
            # Remove unwanted elements
            for element in soup.select('script, style, iframe, noscript, object, embed'):
                element.decompose()
            
            # Clean attributes except for essential ones
            for tag in soup.find_all(True):
                allowed_attrs = ['href', 'src', 'alt', 'title', 'id', 'class']
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in allowed_attrs:
                        del tag.attrs[attr]
            
            # Convert soup back to string with proper formatting
            if isinstance(soup, BeautifulSoup):
                clean_content = self._format_html(soup)
            else:
                clean_content = self._format_html(BeautifulSoup(str(soup), "html.parser"))
        else:
            # Use raw content but still format it
            if isinstance(content, BeautifulSoup):
                clean_content = self._format_html(content)
            else:
                clean_content = self._format_html(BeautifulSoup(str(content), "html.parser"))
        
        # Format result based on options
        if self.add_boilerplate:
            result = '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            result += f'  <meta charset="UTF-8">\n'
            result += f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            result += f'  <title>{html.escape(metadata["title"])}</title>\n'
            
            # Add metadata
            result += f'  <meta name="description" content="{self._get_description(metadata)}">\n'
            
            # Add OpenGraph tags
            og_metadata = metadata["og_metadata"]
            if og_metadata:
                if "og_title" in og_metadata:
                    result += f'  <meta property="og:title" content="{html.escape(og_metadata["og_title"])}">\n'
                
                if "og_description" in og_metadata:
                    result += f'  <meta property="og:description" content="{html.escape(og_metadata["og_description"])}">\n'
                
                if "og_image" in og_metadata:
                    result += f'  <meta property="og:image" content="{html.escape(og_metadata["og_image"])}">\n'
            
            # Add CSS if requested
            if self.add_css:
                result += '  <style>\n'
                result += '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }\n'
                result += '    img { max-width: 100%; height: auto; }\n'
                result += '    a { color: #0366d6; text-decoration: none; }\n'
                result += '    a:hover { text-decoration: underline; }\n'
                result += '    h1, h2, h3, h4, h5, h6 { margin-top: 1.5em; margin-bottom: 0.5em; }\n'
                result += '    p, ul, ol { margin-bottom: 1em; }\n'
                result += '    code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; }\n'
                result += '    pre { background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 3px; }\n'
                result += '    blockquote { margin: 0; padding-left: 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; }\n'
                result += '    table { border-collapse: collapse; width: 100%; }\n'
                result += '    table, th, td { border: 1px solid #dfe2e5; }\n'
                result += '    th, td { padding: 8px 12px; }\n'
                result += '    .source-link { margin-bottom: 20px; font-style: italic; }\n'
                result += '  </style>\n'
            
            result += '</head>\n<body>\n'
            
            # Add title and source link
            result += f'  <h1>{html.escape(metadata["title"])}</h1>\n'
            result += f'  <p class="source-link">Source: <a href="{html.escape(metadata["url"])}" target="_blank">{html.escape(metadata["url"])}</a></p>\n'
            
            # Add content
            result += clean_content
            
            # Add images if requested
            if self.include_images and scraped_data["images"]:
                result += '\n  <h2>Images</h2>\n  <div class="images">\n'
                
                for img in scraped_data["images"]:
                    img_url = img["url"]
                    img_alt = img["alt"]
                    
                    # Check if we have a local path for this image
                    if img_url in self.image_map:
                        local_path = self.image_map[img_url]
                        result += f'    <div class="image-container">\n'
                        result += f'      <img src="{html.escape(local_path)}" alt="{html.escape(img_alt)}"'
                        
                        # Add dimensions if available
                        if "dimensions" in img and img["dimensions"]:
                            dimensions = img["dimensions"]
                            if "width" in dimensions:
                                result += f' width="{dimensions["width"]}"'
                            if "height" in dimensions:
                                result += f' height="{dimensions["height"]}"'
                        
                        result += '>\n'
                        result += f'      <p class="image-caption">{html.escape(img_alt)}</p>\n'
                        result += f'    </div>\n'
                    else:
                        result += f'    <div class="image-container">\n'
                        result += f'      <img src="{html.escape(img_url)}" alt="{html.escape(img_alt)}">\n'
                        result += f'      <p class="image-caption">{html.escape(img_alt)}</p>\n'
                        result += f'    </div>\n'
                
                result += '  </div>\n'
            
            # Close body and html tags
            result += '</body>\n</html>'
        else:
            # Just add minimal metadata as HTML comments
            result = f"<!-- Title: {metadata['title']} -->\n"
            result += f"<!-- Source: {metadata['url']} -->\n\n"
            
            # Add the content
            result += clean_content
            
            # Add images if requested
            if self.include_images and scraped_data["images"]:
                result += '\n\n<h2>Images</h2>\n'
                
                for img in scraped_data["images"]:
                    img_url = img["url"]
                    img_alt = img["alt"]
                    
                    # Check if we have a local path for this image
                    if img_url in self.image_map:
                        local_path = self.image_map[img_url]
                        result += f'<img src="{html.escape(local_path)}" alt="{html.escape(img_alt)}" />\n'
                    else:
                        result += f'<img src="{html.escape(img_url)}" alt="{html.escape(img_alt)}" />\n'
        
        return result
    
    def _format_html(self, soup):
        """
        Custom HTML formatter that produces consistently indented, clean HTML.
        
        Args:
            soup (BeautifulSoup): BeautifulSoup object to format
            
        Returns:
            str: Formatted HTML with consistent indentation
        """
        # Find the main content if available
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find("div", {"id": "content"}) or 
            soup.find("div", {"class": "content"}) or
            soup.find("div", {"role": "main"}) or
            soup.body or
            soup
        )
        
        # Start with just the content we want to format
        # Start a fresh string for the formatted HTML
        formatted_html = []
        
        # Format the HTML recursively with proper indentation
        self._format_node(main_content, formatted_html, indent_level=0, in_pre=False)
        
        # Join all lines and return
        return "\n".join(formatted_html)
    
    def _format_node(self, node, output, indent_level=0, in_pre=False):
        """
        Recursively format an HTML node with proper indentation.
        
        Args:
            node: BeautifulSoup node to format
            output: List to append formatted lines to
            indent_level: Current indentation level
            in_pre: Whether we're inside a pre tag (no formatting)
        """
        # Skip empty and hidden elements
        if not node or not str(node).strip():
            return
            
        # Handle text nodes
        if node.name is None:  # Text node
            text = node.string
            if text and text.strip():
                # Don't indent or format text inside pre tags
                if in_pre:
                    output.append(text)
                else:
                    # Normalize whitespace in text
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        output.append(' ' * (indent_level * 2) + text)
            return
            
        # Check if we're entering a pre tag
        is_pre = node.name == 'pre'
        current_in_pre = in_pre or is_pre
        
        # Skip script, style, and similar tags
        if node.name in ['script', 'style', 'noscript', 'iframe']:
            return
            
        # Start tag
        indent = ' ' * (indent_level * 2)
        attrs = ' '.join([f'{k}="{v}"' for k, v in node.attrs.items()])
        if attrs:
            start_tag = f"{indent}<{node.name} {attrs}>"
        else:
            start_tag = f"{indent}<{node.name}>"
            
        # Handle self-closing tags
        if node.name in self.self_closing:
            output.append(start_tag)
            return
            
        # For block elements, add the start tag on its own line
        if node.name in self.block_elements and not current_in_pre:
            output.append(start_tag)
            
            # Process children with increased indentation
            for child in node.children:
                self._format_node(child, output, indent_level + 1, current_in_pre)
                
            # End tag on its own line
            output.append(f"{indent}</{node.name}>")
        else:
            # For inline elements, keep everything on one line if possible
            if node.name and not current_in_pre:
                # Check if it's just text or has complex children
                if len(list(node.children)) == 1 and node.string:
                    # Simple case with just text
                    text = re.sub(r'\s+', ' ', node.string).strip() if not current_in_pre else node.string
                    output.append(f"{start_tag}{text}</{node.name}>")
                else:
                    # Has complex children, format normally
                    output.append(start_tag)
                    for child in node.children:
                        self._format_node(child, output, indent_level + 1, current_in_pre)
                    output.append(f"{indent}</{node.name}>")
            else:
                # Handle pre tag content - preserve formatting
                if current_in_pre:
                    output.append(start_tag)
                    # Just add the content as is for pre tags
                    if node.string:
                        output.append(node.string)
                    else:
                        for child in node.children:
                            self._format_node(child, output, 0, current_in_pre)
                    output.append(f"</{node.name}>")
                else:
                    # Normal formatting
                    output.append(start_tag)
                    for child in node.children:
                        self._format_node(child, output, indent_level + 1, current_in_pre)
                    output.append(f"{indent}</{node.name}>")
    
    def _get_description(self, metadata):
        """Get a description for the HTML metadata."""
        og_metadata = metadata["og_metadata"]
        
        if og_metadata and "og_description" in og_metadata:
            return html.escape(og_metadata["og_description"])
        
        return html.escape(f"Content from {metadata['title']}")

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
        extension = "html"
        return super().save_to_file(formatted_content, url, output_dir, extension=extension)