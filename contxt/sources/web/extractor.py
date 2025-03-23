import requests
from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from typing import Optional, Dict, Any

from webseed.utils.browser import get_webdriver
from webseed.utils.http import make_request
from webseed.utils.logging import get_logger

logger = get_logger(__name__)


def extract_content(url: str, mode: str = 'basic') -> Optional[str]:
    """
    Extract content from a URL using different extraction modes.
    
    Args:
        url: The URL to extract content from
        mode: Extraction mode - 'basic', 'advanced', or 'super'
        
    Returns:
        HTML content as a string, or None if extraction failed
    """
    try:
        if mode == 'basic':
            return extract_basic(url)
        elif mode == 'advanced':
            return extract_advanced(url)
        elif mode == 'super':
            return extract_super(url)
        else:
            logger.warning(f"Unknown extraction mode: {mode}. Using basic mode.")
            return extract_basic(url)
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return None


def extract_basic(url: str) -> Optional[str]:
    """
    Basic extraction using requests library.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        HTML content as a string, or None if extraction failed
    """
    try:
        response = make_request(url)
        if response and response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        logger.error(f"Basic extraction failed for {url}: {e}")
        return None


def extract_advanced(url: str) -> Optional[str]:
    """
    Advanced extraction using headless browser.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        HTML content as a string, or None if extraction failed
    """
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        
        driver = get_webdriver(options=chrome_options)
        driver.get(url)
        
        # Wait for dynamic content to load
        time.sleep(5)
        
        return driver.page_source
    except Exception as e:
        logger.error(f"Advanced extraction failed for {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def extract_super(url: str) -> Optional[str]:
    """
    Super extraction with full browser and explicit waits.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        HTML content as a string, or None if extraction failed
    """
    driver = None
    try:
        driver = get_webdriver(headless=False)
        driver.get(url)
        
        # Wait for body to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        return driver.page_source
    except Exception as e:
        logger.error(f"Super extraction failed for {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def parse_html_content(html_content: str, url: str, format_type: str = 'tagged') -> str:
    """
    Parse HTML content and extract meaningful content.
    
    Args:
        html_content: HTML content to parse
        url: Original URL for reference
        format_type: Output format type - 'tagged' or 'markdown'
        
    Returns:
        Parsed content in the requested format
    """
    if not html_content:
        return ""

    # Process with html2text library if available
    try:
        import html2text
        return parse_with_html2text(html_content, url, format_type)
    except ImportError:
        logger.info("html2text library not available, using fallback parser")
        return parse_with_fallback(html_content, url, format_type)


def parse_with_html2text(html_content: str, url: str, format_type: str) -> str:
    """
    Parse HTML content using html2text library.
    
    Args:
        html_content: HTML content to parse
        url: Original URL for reference
        format_type: Output format type - 'tagged' or 'markdown'
        
    Returns:
        Parsed content in the requested format
    """
    import html2text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title from multiple sources
    title = extract_title(soup)
    
    # Clean HTML before conversion
    clean_soup = clean_html_content(soup)
    
    # If format is tagged, use the fallback method
    if format_type != 'markdown':
        return parse_with_fallback(str(clean_soup), url, format_type)
    
    # Configure HTML2Text
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = False
    text_maker.ignore_images = False
    text_maker.ignore_tables = False
    text_maker.bypass_tables = False
    text_maker.protect_links = True
    text_maker.mark_code = True
    text_maker.body_width = 0  # Don't wrap text
    
    # Convert to Markdown
    markdown_content = text_maker.handle(str(clean_soup))
    
    # Clean up the markdown
    markdown_content = clean_markdown(markdown_content)
    
    # Format the output
    output = f"### [{url}]({url})\n\n"
    output += f"**Title:** {title}\n\n"
    
    # Add description if available
    og_description = soup.find("meta", property="og:description")
    if og_description:
        output += f"**Description:** {og_description['content']}\n\n"
    
    output += "# Content\n\n"
    output += markdown_content
    output += "\n\n---\n"
    
    return output


def extract_title(soup: BeautifulSoup) -> str:
    """
    Extract title from multiple possible sources.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Title string
    """
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


def clean_html_content(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Clean HTML content for better markdown conversion.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Cleaned BeautifulSoup object
    """
    # Remove unnecessary elements
    for tag in soup([
        "script", "style", "header", "footer", "noscript", 
        "form", "input", "textarea", "select", "option",
        "button", "svg", "iframe", "object", "embed", 
        "applet", "nav", "navbar"
    ]):
        tag.decompose()
    
    # Remove elements with specific IDs
    for id_name in ["layers", "cookie-banner", "ad-container", "popup", "overlay"]:
        for tag in soup.find_all(id=id_name):
            tag.decompose()
    
    # Remove elements with certain classes
    for class_name in ["advertisement", "ad", "popup", "overlay", "cookie-notice"]:
        for tag in soup.find_all(class_=class_name):
            tag.decompose()
    
    # Remove HTML comments
    from bs4 import Comment
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    return soup


def clean_markdown(markdown: str) -> str:
    """
    Clean up the generated markdown content.
    
    Args:
        markdown: Raw markdown content
        
    Returns:
        Cleaned markdown content
    """
    # Replace multiple newlines with at most two
    lines = [line for line in markdown.split("\n") if line.strip()]
    cleaned = "\n\n".join(" ".join(lines).split())
    
    # Ensure consistent spacing between sections
    import re
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned


def parse_with_fallback(html_content: str, url: str, format_type: str = 'tagged') -> str:
    """
    Parse HTML content using the fallback BeautifulSoup method.
    
    Args:
        html_content: HTML content to parse
        url: Original URL for reference
        format_type: Output format type - 'tagged' or 'markdown'
        
    Returns:
        Parsed content in the requested format
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Initialize output based on format type
    if format_type == 'markdown':
        output = f"### [{url}]({url})\n\n"
    else:
        output = f"URL: {url}\n\n"

    # Extract OpenGraph title and description
    og_title = soup.find("meta", property="og:title")
    og_description = soup.find("meta", property="og:description")

    if og_title:
        if format_type == 'markdown':
            output += f"**Title:** {og_title['content']}\n"
        else:
            output += f"Title: {og_title['content']}\n"
    if og_description:
        if format_type == 'markdown':
            output += f"**Description:** {og_description['content']}\n"
        else:
            output += f"Description: {og_description['content']}\n"

    if format_type == 'markdown':
        output += "\n# Content\n\n"
    else:
        output += "\nContent:\n\n"

    # Remove nav and footer elements
    for tag in soup.find_all(['nav', 'footer']):
        tag.decompose()

    # Find the <main> tag
    main_content = soup.find('main')

    if not main_content:
        if format_type == 'markdown':
            output += "No <main> tag found. Extracting from entire body.\n\n"
        else:
            output += "No <main> tag found. Extracting from entire body.\n"
        main_content = soup.body

    # Extract all relevant tags in order
    tags_to_extract = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'p', 'li']
    elements = [el for el in main_content.find_all(tags_to_extract)
                if not (el.name == 'p' and el.parent and el.parent.name == 'li')]

    # Track seen list items to prevent duplication
    seen_list_items = set()

    if format_type == 'markdown':
        process_markdown_format(elements, seen_list_items, output)
    else:
        process_tagged_format(elements, seen_list_items, output)

    return output


def process_markdown_format(elements, seen_list_items, output):
    """Process elements for markdown format."""
    processed_texts = []
    i = 0
    while i < len(elements):
        if elements[i].name == 'span':
            span_buffer = [elements[i].get_text(strip=True)]
            i += 1
            while i < len(elements) and elements[i].name == 'span':
                span_buffer.append(elements[i].get_text(strip=True))
                i += 1
            concatenated_span = ' '.join(span_buffer)
            processed_texts.append(('span', concatenated_span))
        else:
            text = elements[i].get_text(strip=True)
            # Remove SVG content from the beginning of the text
            text = re.sub(r'^<svg.*?</svg>\s*', '', text, flags=re.DOTALL)
            # Remove extra whitespace and newlines
            text = re.sub(r'\s+', ' ', text).strip()

            # Handle list items deduplication
            if elements[i].name == 'li':
                if text not in seen_list_items:
                    seen_list_items.add(text)
                    processed_texts.append((elements[i].name, text))
            else:
                if text:
                    processed_texts.append((elements[i].name, text))
            i += 1

    # Now, convert processed_texts to Markdown
    for tag, text in processed_texts:
        markdown_line = convert_to_markdown(tag, text)
        output += markdown_line

    # Add horizontal rule at the end
    output += "\n---\n"
    
    return output


def process_tagged_format(elements, seen_list_items, output):
    """Process elements for tagged format."""
    output_lines = []
    previous_tag = None
    span_buffer = []

    for tag in elements:
        # Get the text content
        text = tag.get_text(strip=True)

        # Remove SVG content from the beginning of the text
        text = re.sub(r'^<svg.*?</svg>\s*', '', text, flags=re.DOTALL)

        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()

        if tag.name == 'span':
            span_buffer.append(text)
        else:
            if span_buffer:
                concatenated_span = ' '.join(span_buffer)
                output_lines.append(f"span: {concatenated_span}")
                span_buffer = []

            # Handle list items deduplication
            if tag.name == 'li':
                if text not in seen_list_items:
                    seen_list_items.add(text)
                    output_lines.append(f"{tag.name}: {text}")
            else:
                if text:
                    output_lines.append(f"{tag.name}: {text}")

    # Handle any remaining spans
    if span_buffer:
        concatenated_span = ' '.join(span_buffer)
        output_lines.append(f"span: {concatenated_span}")

    # Join all lines
    output += "\n".join(output_lines)
    # Add horizontal rule at the end
    output += "\n\n---\n"
    
    return output


def convert_to_markdown(tag_name, text):
    """Convert HTML tag name and text to Markdown format."""
    if tag_name.startswith('h'):
        try:
            level = int(tag_name[1])
            return f"{'#' * level} {text}\n\n"
        except ValueError:
            return f"# {text}\n\n"  # Default to h1 if level is not found
    elif tag_name == 'p':
        return f"{text}\n\n"
    elif tag_name == 'li':
        return f"- {text}\n"
    elif tag_name == 'span':
        return f"{text}"
    else:
        return f"{text}\n\n"