import html2text
from bs4 import BeautifulSoup, Comment
from typing import Dict, Any, Optional

from webseed.processors.base import BaseProcessor
from webseed.utils.logging import get_logger

logger = get_logger(__name__)


class MarkdownProcessor(BaseProcessor):
    """Processor for converting HTML content to Markdown."""
    
    def __init__(
        self,
        include_links: bool = True,
        include_images: bool = True,
        handle_tables: bool = True,
        protect_links: bool = True,
        mark_code: bool = True
    ):
        """
        Initialize the Markdown processor with configuration options.
        
        Args:
            include_links: Whether to include links in the markdown output
            include_images: Whether to include images in the markdown output
            handle_tables: Whether to handle tables properly in markdown
            protect_links: Whether to protect links from line breaks
            mark_code: Whether to mark code blocks
        """
        self.include_links = include_links
        self.include_images = include_images
        self.handle_tables = handle_tables
        self.protect_links = protect_links
        self.mark_code = mark_code
    
    def clean_html(self, html: str) -> str:
        """
        Clean HTML content before conversion to markdown.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned HTML content
        """
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unnecessary elements
        for element in soup([
            "script", "style", "header", "footer", "noscript",
            "form", "input", "textarea", "select", "option",
            "button", "svg", "iframe", "object", "embed",
            "applet", "nav", "navbar"
        ]):
            element.decompose()
        
        # Remove specific IDs
        for id_name in ["layers", "cookie-banner", "ad-container", "popup", "overlay"]:
            for tag in soup.find_all(id=id_name):
                tag.decompose()
        
        # Remove elements with certain classes
        for class_name in ["advertisement", "ad", "popup", "overlay", "cookie-notice"]:
            for tag in soup.find_all(class_=class_name):
                tag.decompose()
        
        # Remove unnecessary attributes but keep href and src
        for tag in soup.find_all(True):
            if tag.name not in ["a", "img"]:
                tag.attrs = {}
            else:
                allowed_attrs = ["href", "src", "alt"]
                tag.attrs = {key: value for key, value in tag.attrs.items() 
                             if key in allowed_attrs}
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        return str(soup)
    
    def extract_title(self, html: str) -> str:
        """
        Extract the title from HTML content.
        
        Args:
            html: HTML content
            
        Returns:
            Title string
        """
        if not html:
            return "No title"
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to get the title from the title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # Try to get the title from h1
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.get_text():
            return h1_tag.get_text().strip()
        
        # Try to get the title from og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        
        return "No title"
    
    def process(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process HTML content and convert it to Markdown.
        
        Args:
            content: Dictionary containing HTML content and URL
            
        Returns:
            Dictionary with processed markdown content
        """
        html = content.get("html", "")
        url = content.get("url", "")
        
        if not html:
            logger.warning(f"No HTML content provided for {url}")
            return {
                "title": "No content",
                "url": url,
                "markdown_content": ""
            }
        
        # Extract title before cleaning
        title = content.get("title") or self.extract_title(html)
        
        # Clean HTML
        cleaned_html = self.clean_html(html)
        
        # Configure HTML2Text
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = not self.include_links
        text_maker.ignore_images = not self.include_images
        text_maker.ignore_tables = not self.handle_tables
        text_maker.bypass_tables = not self.handle_tables
        text_maker.protect_links = self.protect_links
        text_maker.mark_code = self.mark_code
        text_maker.body_width = 0  # Don't wrap text
        
        # Convert to Markdown
        markdown_content = text_maker.handle(cleaned_html)
        
        # Post-processing: Remove excessive newlines
        markdown_content = self._clean_markdown(markdown_content)
        
        return {
            "title": title,
            "url": url,
            "markdown_content": markdown_content
        }
    
    def _clean_markdown(self, markdown: str) -> str:
        """
        Clean up the generated markdown content.
        
        Args:
            markdown: Raw markdown content
            
        Returns:
            Cleaned markdown content
        """
        # Replace multiple newlines with at most two
        cleaned = "\n".join([line for line in markdown.split("\n") if line.strip()])
        
        # Ensure consistent spacing between sections
        import re
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned


class HtmlTextExtractor(BaseProcessor):
    """Extract main text content from HTML."""
    
    def __init__(self, main_content_selectors: Optional[list] = None):
        """
        Initialize the HTML text extractor.
        
        Args:
            main_content_selectors: List of CSS selectors for main content areas
        """
        self.main_content_selectors = main_content_selectors or [
            "main", "article", "#content", ".content", "#main", ".main"
        ]
    
    def process(self, html: str) -> str:
        """
        Extract main text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text content
        """
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script, style, and other unnecessary elements
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()
        
        # Try to find main content area
        main_content = None
        for selector in self.main_content_selectors:
            if selector.startswith('#'):
                main_content = soup.find(id=selector[1:])
            elif selector.startswith('.'):
                main_content = soup.find(class_=selector[1:])
            else:
                main_content = soup.find(selector)
            
            if main_content:
                break
        
        # If no main content area found, use body
        if not main_content:
            main_content = soup.body
        
        # If still nothing, return empty string
        if not main_content:
            return ""
        
        # Extract text
        text = main_content.get_text(separator=" ", strip=True)
        
        # Clean up text
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text