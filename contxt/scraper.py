import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, urljoin
import logging
import os
import re
import shutil
import platform
import subprocess
from pathlib import Path
import tiktoken
import hashlib
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if running on Mac ARM
IS_MAC_ARM = platform.system() == 'Darwin' and platform.machine() == 'arm64'

# Optional imports for advanced scraping
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class Scraper:
    def __init__(self, mode="basic"):
        """
        Initialize the scraper with the specified mode.
        
        Args:
            mode (str): Scraping mode - "basic", "advanced", or "super"
        """
        self.mode = mode
        
        if mode in ["advanced", "super"] and not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available. Falling back to basic mode.")
            self.mode = "basic"
    
    def scrape(self, url, include_images=False):
        """
        Scrape content from the given URL.
        
        Args:
            url (str): URL to scrape
            include_images (bool): Whether to download images
            
        Returns:
            dict: Dictionary containing metadata and content
        """
        # Log the start of scraping
        logger.info(f"Scraping {url} using {self.mode} mode...")
        
        # Scrape using the appropriate mode
        if self.mode == "basic":
            result = self._scrape_basic(url, include_images)
        else:
            try:
                if self.mode == "advanced":
                    result = self._scrape_advanced(url, include_images)
                else:  # super mode
                    result = self._scrape_super(url, include_images)
            except Exception as e:
                logger.error(f"Error in {self.mode} mode: {e}")
                logger.info("Falling back to basic mode")
                result = self._scrape_basic(url, include_images)
        
        # Log completion
        if result["content"]:
            logger.info(f"Completed scraping {url} in {result.get('processing_time', 0):.2f} seconds - {result.get('token_count', 0)} tokens")
        else:
            logger.warning(f"Failed to scrape content from {url}")
        
        return result
    
    def _scrape_basic(self, url, include_images):
        """Basic scraping using requests and BeautifulSoup."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract metadata
            title = soup.title.text.strip() if soup.title else ""
            
            # Clean HTML to remove unnecessary elements
            cleaned_soup, og_metadata = self._clean_html(soup)
            
            # Extract main content - prioritize main tag first
            main_content = (
                cleaned_soup.find("main") or 
                cleaned_soup.find("article") or 
                cleaned_soup.find("div", {"id": "content"}) or 
                cleaned_soup.find("div", {"class": "content"}) or
                cleaned_soup.find("div", {"role": "main"})
            )
            
            if not main_content:
                # Fallback to body if no specific content area found
                main_content = cleaned_soup.body
            
            # Process images if requested
            images = []
            if include_images and main_content:
                images = self._extract_images(main_content, url)
                
                # Also add OpenGraph image if available
                if og_metadata.get("og_image"):
                    og_image_url = urljoin(url, og_metadata["og_image"])
                    images.append({"url": og_image_url, "alt": "OpenGraph image"})
            
            # Count tokens
            token_count = self._count_tokens(str(main_content))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "url": url,
                "title": title,
                "content": main_content,
                "images": images,
                "raw_html": str(main_content),
                "token_count": token_count,
                "og_metadata": og_metadata,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "title": f"Error: {str(e)}",
                "content": None,
                "images": [],
                "raw_html": "",
                "token_count": 0,
                "og_metadata": {},
                "processing_time": 0
            }
    
    def _create_driver(self, headless=True):
        """Create an appropriate WebDriver for the current platform."""
        driver = None
        
        # First try: Check if Chrome is installed in standard location
        chrome_paths = {
            "darwin": [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            ],
            "linux": [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/brave-browser"
            ],
            "win32": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
            ]
        }
        
        # Try to locate Chrome
        chrome_path = None
        system_platform = platform.system().lower()
        if system_platform == "darwin":
            system_platform = "darwin"  # macOS
        elif system_platform == "windows":
            system_platform = "win32"
        
        if system_platform in chrome_paths:
            for path in chrome_paths[system_platform]:
                if os.path.exists(path):
                    chrome_path = path
                    break
        
        try:
            # Special handling for Mac ARM
            if IS_MAC_ARM:
                # Try to create a Chrome driver using Safari in webdriver mode
                try:
                    logger.info("Trying Safari WebDriver for Mac ARM")
                    from selenium.webdriver.safari.options import Options as SafariOptions
                    safari_options = SafariOptions()
                    driver = webdriver.Safari(options=safari_options)
                    return driver
                except Exception as e:
                    logger.error(f"Safari WebDriver failed: {e}")
                    
                    # Try Chrome as last resort - check if installed via homebrew
                    try:
                        logger.info("Checking for ChromeDriver installed via homebrew")
                        result = subprocess.run(["which", "chromedriver"], capture_output=True, text=True)
                        chromedriver_path = result.stdout.strip()
                        
                        if chromedriver_path:
                            logger.info(f"Found ChromeDriver at {chromedriver_path}")
                            chrome_options = Options()
                            if headless:
                                chrome_options.add_argument("--headless")
                            chrome_options.add_argument("--no-sandbox")
                            
                            service = Service(executable_path=chromedriver_path)
                            driver = webdriver.Chrome(service=service, options=chrome_options)
                            return driver
                    except Exception as e:
                        logger.error(f"Failed to use homebrew ChromeDriver: {e}")
                        raise Exception("No compatible WebDriver found for Mac ARM")
            else:
                # Standard Chrome setup for non-ARM platforms
                chrome_options = Options()
                if headless:
                    chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                if chrome_path:
                    chrome_options.binary_location = chrome_path
                
                # Try to find chromedriver in PATH
                try:
                    result = subprocess.run(["which", "chromedriver"], capture_output=True, text=True)
                    chromedriver_path = result.stdout.strip()
                    
                    if chromedriver_path:
                        service = Service(executable_path=chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        # Fallback to letting Selenium find ChromeDriver
                        driver = webdriver.Chrome(options=chrome_options)
                except:
                    # Final fallback
                    driver = webdriver.Chrome(options=chrome_options)
                
                return driver
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            raise
            
        # If we get here, all attempts failed
        raise Exception("Could not create a compatible WebDriver")
    
    def _scrape_advanced(self, url, include_images):
        """Advanced scraping using Selenium for JavaScript-heavy sites - standalone version."""
        driver = None
        try:
            start_time = time.time()
            
            # Create a new browser instance
            driver = self._create_driver(headless=True)
            
            # Get the URL
            driver.get(url)
            
            # Wait for dynamic content
            time.sleep(5)
            
            # Get the page source after JS has loaded
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Extract metadata
            title = soup.title.text.strip() if soup.title else ""
            
            # Clean HTML to remove unnecessary elements
            cleaned_soup, og_metadata = self._clean_html(soup)
            
            # Extract main content - prioritize main tag first
            main_content = (
                cleaned_soup.find("main") or 
                cleaned_soup.find("article") or 
                cleaned_soup.find("div", {"id": "content"}) or 
                cleaned_soup.find("div", {"class": "content"}) or
                cleaned_soup.find("div", {"role": "main"})
            )
            
            if not main_content:
                # Fallback to body if no specific content area found
                main_content = cleaned_soup.body
            
            # Process images if requested
            images = []
            if include_images and main_content:
                images = self._extract_images(main_content, url)
                
                # Also add OpenGraph image if available
                if og_metadata.get("og_image"):
                    og_image_url = urljoin(url, og_metadata["og_image"])
                    images.append({"url": og_image_url, "alt": "OpenGraph image"})
            
            # Count tokens
            token_count = self._count_tokens(str(main_content))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "url": url,
                "title": title,
                "content": main_content,
                "images": images,
                "raw_html": str(main_content),
                "token_count": token_count,
                "og_metadata": og_metadata,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url} with Selenium: {e}")
            return {
                "url": url,
                "title": f"Error: {str(e)}",
                "content": None,
                "images": [],
                "raw_html": "",
                "token_count": 0,
                "og_metadata": {},
                "processing_time": 0
            }
        finally:
            # Always close the driver to clean up resources
            if driver:
                driver.quit()
    
    def _scrape_super(self, url, include_images):
        """Super scraping using Selenium with WebDriverWait for complex sites."""
        driver = None
        try:
            start_time = time.time()
            
            # Create a new browser instance (non-headless for super mode)
            driver = self._create_driver(headless=False)
            
            # Get the URL
            driver.get(url)
            
            # Wait for dynamic content with explicit wait
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get the page source after JS has loaded
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Extract metadata
            title = soup.title.text.strip() if soup.title else ""
            
            # Clean HTML to remove unnecessary elements
            cleaned_soup, og_metadata = self._clean_html(soup)
            
            # Extract main content - prioritize main tag first
            main_content = (
                cleaned_soup.find("main") or 
                cleaned_soup.find("article") or 
                cleaned_soup.find("div", {"id": "content"}) or 
                cleaned_soup.find("div", {"class": "content"}) or
                cleaned_soup.find("div", {"role": "main"})
            )
            
            if not main_content:
                # Fallback to body if no specific content area found
                main_content = cleaned_soup.body
            
            # Process images if requested
            images = []
            if include_images and main_content:
                images = self._extract_images(main_content, url)
                
                # Also add OpenGraph image if available
                if og_metadata.get("og_image"):
                    og_image_url = urljoin(url, og_metadata["og_image"])
                    images.append({"url": og_image_url, "alt": "OpenGraph image"})
            
            # Count tokens
            token_count = self._count_tokens(str(main_content))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "url": url,
                "title": title,
                "content": main_content,
                "images": images,
                "raw_html": str(main_content),
                "token_count": token_count,
                "og_metadata": og_metadata,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url} with Selenium: {e}")
            return {
                "url": url,
                "title": f"Error: {str(e)}",
                "content": None,
                "images": [],
                "raw_html": "",
                "token_count": 0,
                "og_metadata": {},
                "processing_time": 0
            }
        finally:
            # Always close the driver to clean up resources
            if driver:
                driver.quit()
    
    def close(self):
        """
        Dummy close method for backward compatibility.
        Since we're creating and destroying WebDriver instances per URL,
        there's no need to explicitly close anything at the class level.
        """
        pass
    
    def _extract_images(self, content, base_url):
        """Extract images from content with proper URL handling."""
        images = []
        for img in content.find_all("img"):
            if img.get("src"):
                # Convert relative URLs to absolute
                image_url = urljoin(base_url, img["src"])
                alt_text = img.get("alt", "")
                width = img.get("width", "")
                height = img.get("height", "")
                
                # Extract any image dimensions if present
                dimensions = {}
                if width:
                    dimensions["width"] = width
                if height:
                    dimensions["height"] = height
                
                images.append({
                    "url": image_url,
                    "alt": alt_text,
                    "dimensions": dimensions
                })
        
        return images
    
    def _clean_html(self, soup):
        """
        Clean HTML by removing unnecessary elements.
        
        Args:
            soup (BeautifulSoup): BeautifulSoup object to clean
            
        Returns:
            BeautifulSoup: Cleaned BeautifulSoup object
        """
        # Create a copy to avoid modifying the original
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        
        # Extract OpenGraph metadata before cleaning
        og_metadata = self._extract_og_metadata(soup_copy)
        
        # Remove script, style, and other unnecessary elements
        for element in soup_copy(["script", "style", "header", "footer", "nav", "noscript", 
                             "form", "button", "input", "iframe", "aside", "svg", 
                             "[class*='menu']", "[class*='nav']", "[class*='footer']", 
                             "[class*='header']", "[id*='menu']", "[id*='nav']", 
                             "[id*='footer']", "[id*='header']"]):
            element.decompose()
        
        # Remove comments
        for comment in soup_copy.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove most attributes except for essential ones
        for tag in soup_copy.find_all(True):
            allowed_attrs = ['href', 'src', 'alt']
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag.attrs[attr]
        
        # Process and deduplicate list items
        self._deduplicate_list_items(soup_copy)
        
        # Concatenate adjacent spans
        self._concatenate_spans(soup_copy)
        
        # Clean text content (remove SVG content, normalize whitespace)
        for tag in soup_copy.find_all(text=True):
            if tag.parent and not isinstance(tag, Comment):
                # Remove SVG content
                cleaned_text = re.sub(r'<svg.*?</svg>\s*', '', tag.string, flags=re.DOTALL) if tag.string else ""
                # Normalize whitespace
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                tag.replace_with(cleaned_text)
        
        return soup_copy, og_metadata
    
    def _extract_og_metadata(self, soup):
        """Extract OpenGraph metadata from HTML."""
        metadata = {}
        
        # Extract title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            metadata["og_title"] = og_title["content"]
        
        # Extract description
        og_description = soup.find("meta", property="og:description")
        if og_description and og_description.get("content"):
            metadata["og_description"] = og_description["content"]
        
        # Extract image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            metadata["og_image"] = og_image["content"]
        
        return metadata
    
    def _deduplicate_list_items(self, soup):
        """Deduplicate list items to avoid repetition."""
        seen_list_items = set()
        
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if text in seen_list_items:
                li.decompose()  # Remove duplicate
            else:
                seen_list_items.add(text)
    
    def _concatenate_spans(self, soup):
        """Concatenate adjacent span elements."""
        # Find all spans
        spans = soup.find_all("span")
        
        # Process spans that are adjacent siblings
        for i, span in enumerate(spans[:-1]):
            # Check if next span is a sibling
            if span.next_sibling == spans[i + 1]:
                # Concatenate the text
                spans[i + 1].string = f"{span.get_text()} {spans[i + 1].get_text()}"
                # Remove the current span
                span.decompose()
    
    def _count_tokens(self, text, model="cl100k_base"):
        """
        Count the number of tokens in the text.
        
        Args:
            text (str): Text to count tokens for
            model (str): Tokenizer model to use
            
        Returns:
            int: Number of tokens
        """
        try:
            enc = tiktoken.get_encoding(model)
            # Remove HTML tags for token counting
            text_without_tags = re.sub(r'<[^>]+>', '', text)
            return len(enc.encode(text_without_tags))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback to rough character-based estimate
            return len(text) // 4
    
    def download_images(self, images, output_dir):
        """
        Download images to the specified directory.
        
        Args:
            images (list): List of image dictionaries with url and alt keys
            output_dir (str): Output directory
            
        Returns:
            dict: Dictionary mapping original URLs to local file paths
        """
        image_map = {}
        processed_hashes = set()
        downloaded_count = 0
        duplicate_count = 0
        error_count = 0
        
        # Create a date-based images directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        domain = urlparse(images[0]["url"]).netloc if images else "unknown"
        images_dir = Path(output_dir) / "images" / f"{domain}_images_{date_str}"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading images to {images_dir}")
        
        for image in images:
            try:
                # Get the image extension from the URL
                image_url = image["url"]
                
                # Download the image
                response = requests.get(image_url, stream=True, timeout=10)
                response.raise_for_status()
                
                # Calculate content hash to avoid duplicates
                content = response.content
                file_hash = hashlib.md5(content).hexdigest()
                
                # Skip if we've already downloaded this image
                if file_hash in processed_hashes:
                    duplicate_count += 1
                    # Use the previously mapped path for this hash
                    for url, path in image_map.items():
                        if Path(path).stem.startswith(file_hash):
                            image_map[image_url] = path
                            break
                    continue
                
                # Get the image extension from the URL
                parsed_url = urlparse(image_url)
                image_path = parsed_url.path
                image_ext = os.path.splitext(image_path)[1]
                
                if not image_ext or image_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif']:
                    image_ext = ".jpg"  # Default to .jpg if no extension is found
                
                # Create a safe filename with the hash to ensure uniqueness
                image_filename = f"{file_hash}{image_ext}"
                image_filepath = images_dir / image_filename
                
                # Save the image
                with open(image_filepath, "wb") as f:
                    f.write(content)
                
                # Add to the map and processed hashes
                image_map[image_url] = str(image_filepath)
                processed_hashes.add(file_hash)
                downloaded_count += 1
                
            except Exception as e:
                logger.error(f"Error downloading image {image['url']}: {e}")
                error_count += 1
        
        logger.info(f"Images downloaded: {downloaded_count}, duplicates skipped: {duplicate_count}, errors: {error_count}")
        return image_map