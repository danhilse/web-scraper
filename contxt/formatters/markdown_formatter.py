import re
import logging
from bs4 import BeautifulSoup, Tag, NavigableString
from .base_formatter import BaseFormatter
from urllib.parse import urljoin
import sys

logger = logging.getLogger(__name__)

class MarkdownFormatter(BaseFormatter):
    """
    Formatter for converting web content to Markdown with recursion safeguards.
    """
    
    def __init__(self, include_images=False, image_map=None, add_frontmatter=True, 
                 include_source_link=True, indent_level=0):
        """Initialize the Markdown formatter."""
        super().__init__(include_images, image_map)
        self.add_frontmatter = add_frontmatter
        self.include_source_link = include_source_link
        self.indent_level = indent_level
        
        # Track depth to prevent excessive recursion
        self.current_depth = 0
        self.max_depth = 20  # Limit recursion depth
    
    def format(self, scraped_data):
        """Format scraped data as Markdown."""
        if not scraped_data.get("content"):
            return f"# Error: {scraped_data.get('title', 'Unknown')}\n\nFailed to fetch content from {scraped_data.get('url', 'Unknown URL')}"
        
        # Extract metadata
        metadata = self.extract_metadata(scraped_data)
        
        # Build Markdown result
        result = []
        
        # Add frontmatter
        if self.add_frontmatter:
            result.append("---")
            # Fix the escaping issues with title
            escaped_title = metadata['title'].replace('"', '\\"')
            result.append(f'title: "{escaped_title}"')
            result.append(f'source: "{metadata["url"]}"')
            result.append(f'date: "{scraped_data.get("date", "")}"')
            
            # Add OpenGraph metadata if available
            og_metadata = metadata.get("og_metadata", {})
            if og_metadata:
                if "og_description" in og_metadata:
                    escaped_desc = og_metadata['og_description'].replace('"', '\\"')
                    result.append(f'description: "{escaped_desc}"')
                
            result.append("---\n")
        
        # Add title as H1
        result.append(f"# {metadata['title']}\n")
        
        # Add source link
        if self.include_source_link:
            result.append(f"Source: [{metadata['url']}]({metadata['url']})\n")
        
        # Get content as HTML string
        content_html = scraped_data.get("content_html", scraped_data.get("content", ""))
        
        # Convert HTML to Markdown using non-recursive approach
        result.append(self._html_to_markdown(content_html))
        
        # Add images if requested
        if self.include_images and scraped_data.get("images"):
            result.append("\n## Images\n")
            
            for img in scraped_data["images"]:
                img_url = img["url"]
                img_alt = img.get("alt", "") or "Image"
                
                # Check if we have a local path for this image
                if img_url in self.image_map:
                    result.append(f"![{img_alt}]({self.image_map[img_url]})")
                else:
                    result.append(f"![{img_alt}]({img_url})")
        
        return "\n".join(result)
    
    def _html_to_markdown(self, html):
        """
        Convert HTML to Markdown using a non-recursive, depth-first traversal
        approach to avoid maximum recursion depth issues while preserving document structure.
        """
        if not html:
            return ""
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return "Error parsing content."

        # Create a string buffer for the output
        markdown_output = []
        
        # Find the main content container
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find("div", {"id": "content"}) or 
            soup.find("div", {"class": "content"}) or
            soup.find("div", {"role": "main"}) or
            soup.body
        )
        
        if not main_content:
            main_content = soup
        
        # Process elements in document order to preserve hierarchy
        self._process_element_iteratively(main_content, markdown_output)
        
        # Join the output and do some post-processing for clean formatting
        raw_output = "\n".join(markdown_output)
        
        # Fix multiple consecutive newlines (more than 2)
        clean_output = re.sub(r'\n{3,}', '\n\n', raw_output)
        
        # Ensure headings have a blank line before them (except at the start of the document)
        clean_output = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', clean_output)
        
        # Return the final markdown
        return clean_output
    
    def _process_element_iteratively(self, root, output_buffer):
        """
        Process HTML elements in document order using an iterative approach.
        This preserves the document hierarchy without risking recursion issues.
        """
        # Stack for depth-first traversal
        stack = [(root, 0)]  # (element, depth)
        last_was_heading = False
        
        while stack:
            element, depth = stack.pop(0)  # Pop from the beginning for breadth-first order
            
            # Skip comment nodes
            if element.name is None and isinstance(element, NavigableString):
                # Handle text nodes
                text = element.string.strip()
                if text:
                    output_buffer.append(text)
                continue
            
            if element.name is None:
                continue
                
            # Process the current element based on its type
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                text = element.get_text(strip=True)
                # Add an extra linebreak before headings
                output_buffer.append(f"\n{'#' * level} {text}\n")
            
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    output_buffer.append(f"{text}\n\n")
            
            elif element.name == 'a':
                href = element.get('href', '')
                text = element.get_text(strip=True) or href
                output_buffer.append(f"[{text}]({href})")
            
            elif element.name == 'img':
                src = element.get('src', '')
                alt = element.get('alt', '') or "Image"
                if src:
                    output_buffer.append(f"![{alt}]({src})")
            
            elif element.name in ['strong', 'b']:
                text = element.get_text(strip=True)
                if text:
                    output_buffer.append(f"**{text}**")
            
            elif element.name in ['em', 'i']:
                text = element.get_text(strip=True)
                if text:
                    output_buffer.append(f"*{text}*")
            
            elif element.name == 'code':
                code = element.get_text()
                if '`' in code:
                    output_buffer.append(f"``{code}``")
                else:
                    output_buffer.append(f"`{code}`")
            
            elif element.name == 'pre':
                code = element.get_text()
                code_element = element.find('code')
                if code_element:
                    code = code_element.get_text()
                
                # Try to determine language
                lang = ""
                for tag in [element, code_element]:
                    if tag and tag.get('class'):
                        for cls in tag.get('class', []):
                            if cls.startswith('language-'):
                                lang = cls[9:]
                                break
                
                output_buffer.append(f"```{lang}\n{code}\n```\n\n")
                continue  # Skip adding children since we've processed the content
            
            elif element.name == 'blockquote':
                text = element.get_text(strip=True)
                lines = text.split('\n')
                quoted_lines = [f"> {line}" if line.strip() else ">" for line in lines]
                output_buffer.append('\n'.join(quoted_lines) + '\n\n')
                continue  # Skip adding children
            
            elif element.name in ['ul', 'ol']:
                is_ordered = element.name == 'ol'
                
                # Process list items
                list_items = []
                for i, li in enumerate(element.find_all('li', recursive=False)):
                    marker = f"{i+1}." if is_ordered else "-"
                    text = li.get_text(strip=True)
                    list_items.append(f"{marker} {text}")
                
                if list_items:
                    output_buffer.append('\n'.join(list_items) + '\n\n')
                continue  # Skip adding children
            
            elif element.name == 'table':
                # Process table
                table_rows = []
                
                # Process header row
                header_row = element.find('tr')
                if header_row:
                    headers = []
                    separators = []
                    
                    for th in header_row.find_all(['th', 'td']):
                        header_text = th.get_text(strip=True)
                        headers.append(header_text)
                        separators.append('-' * max(3, len(header_text)))
                    
                    if headers:
                        table_rows.append('| ' + ' | '.join(headers) + ' |')
                        table_rows.append('| ' + ' | '.join(separators) + ' |')
                
                # Process body rows
                rows = element.find_all('tr')
                for i, row in enumerate(rows):
                    if i == 0 and header_row:  # Skip header row
                        continue
                    
                    cells = []
                    for cell in row.find_all(['td', 'th']):
                        cell_text = cell.get_text(strip=True)
                        cells.append(cell_text)
                    
                    if cells:
                        table_rows.append('| ' + ' | '.join(cells) + ' |')
                
                if table_rows:
                    output_buffer.append('\n'.join(table_rows) + '\n\n')
                continue  # Skip adding children
            
            elif element.name == 'hr':
                output_buffer.append("---\n\n")
            
            elif element.name == 'br':
                output_buffer.append("\n")
            
            # Add children to the stack in reverse order
            # so they get processed in the correct order when popped
            children = list(element.children)
            
            # Skip if element has been processed in a special way above
            if element.name not in ['pre', 'blockquote', 'ul', 'ol', 'table']:
                for child in reversed(children):
                    stack.insert(0, (child, depth + 1))
    
    def save_to_file(self, formatted_content, url, output_dir=None):
        """Save formatted content to a file."""
        return super().save_to_file(formatted_content, url, output_dir, extension="md")