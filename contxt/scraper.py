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
    def __init__(self, mode="basic", include_comments=False, max_videos=30, youtube_format_style="complete"):
        """
        Initialize the scraper with the specified mode and YouTube options.
        
        Args:
            mode (str): Scraping mode - "basic", "advanced", or "super"
            include_comments (bool): Whether to include YouTube comments
            max_videos (int): Maximum number of videos to process from playlists/channels
            youtube_format_style (str): Format style for YouTube content - "raw", "complete", or "chapters"
        """
        self.mode = mode
        self.include_comments = include_comments
        self.max_videos = max_videos
        self.youtube_format_style = youtube_format_style
        
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
        
        # Check if URL is a YouTube URL
        if 'youtube.com' in url or 'youtu.be' in url:
            return self._scrape_youtube(url, include_images)
        
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
        if result["content_html"]:
            logger.info(f"Completed scraping {url} in {result.get('processing_time', 0):.2f} seconds - {result.get('token_count', 0)} tokens")
        else:
            logger.warning(f"Failed to scrape content from {url}")
        
        return result
    

    
    def _scrape_basic(self, url, include_images):
        """Basic scraping using requests and BeautifulSoup."""
        return self._scrape(
            url, 
            include_images, 
            use_selenium=False, 
            wait_time=0, 
            headless=True
        )
    
    def _scrape_advanced(self, url, include_images):
        """Advanced scraping using Selenium for JavaScript-heavy sites."""
        return self._scrape(
            url, 
            include_images, 
            use_selenium=True, 
            wait_time=5, 
            headless=True
        )
    
    def _scrape_super(self, url, include_images):
        """Super scraping using Selenium with extended wait time for complex sites."""
        return self._scrape(
            url, 
            include_images, 
            use_selenium=True, 
            wait_time=15, 
            headless=False
        )
    
    def close(self):
        """
        Dummy close method for backward compatibility.
        Since we're creating and destroying WebDriver instances per URL,
        there's no need to explicitly close anything at the class level.
        """
        pass
    
    # The following methods remain unchanged from the original implementation
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
        # Get a static list of all text nodes
        text_nodes = list(soup_copy.find_all(text=True))
        
        # Process text nodes without modifying the tree during iteration
        for tag in text_nodes:
            if tag.parent and not isinstance(tag, Comment):
                # Only process if tag has a string attribute to avoid AttributeError
                if hasattr(tag, 'string') and tag.string:
                    # Remove SVG content
                    cleaned_text = re.sub(r'<svg.*?</svg>\s*', '', tag.string, flags=re.DOTALL)
                    # Normalize whitespace
                    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                    # Replace the text content only if it changed
                    if cleaned_text != tag.string:
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
        """
        Deduplicate list items to avoid repetition.
        Uses a two-phase approach to avoid modifying the tree while iterating.
        """
        seen_list_items = set()
        items_to_remove = []
        
        # First phase: identify duplicates
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if text in seen_list_items:
                items_to_remove.append(li)  # Mark for removal
            else:
                seen_list_items.add(text)
        
        # Second phase: remove duplicates
        for li in items_to_remove:
            li.decompose()
    
    def _concatenate_spans(self, soup):
        """
        Concatenate adjacent span elements safely without recursion issues.
        Uses an iterative approach to avoid modifying the tree while iterating.
        """
        # Process each parent that might contain spans
        for parent in soup.find_all(lambda tag: tag.find('span')):
            # Get a static list of all direct children
            children = list(parent.children)
            
            # Track spans to remove after processing
            spans_to_remove = []
            
            # Process children looking for adjacent spans
            i = 0
            while i < len(children) - 1:
                current = children[i]
                next_elem = children[i + 1]
                
                # Check if both are span elements
                if current.name == 'span' and next_elem.name == 'span':
                    # Combine text content
                    current_text = current.get_text(strip=True)
                    next_text = next_elem.get_text(strip=True)
                    
                    if current_text and next_text:
                        # Update the next span's text
                        if next_elem.string:
                            next_elem.string = f"{current_text} {next_text}"
                        else:
                            next_elem.clear()
                            next_elem.append(f"{current_text} {next_text}")
                        
                        # Mark current span for removal
                        spans_to_remove.append(current)
                
                i += 1
            
            # Remove spans after processing the entire parent
            for span in spans_to_remove:
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
    
    def _scrape_youtube(self, url, include_images=False):
        """Handle YouTube-specific scraping with format style options."""
        from .youtube_handler import identify_youtube_url_type, get_transcript, get_video_info
        from .youtube_handler import get_playlist_videos, get_channel_videos
        from .youtube_handler import get_chapter_info, organize_transcript_by_chapters
        
        url_type, url_id = identify_youtube_url_type(url)
        
        if url_type == 'video':
            # Single video processing
            video_info = get_video_info(url_id, include_comments=self.include_comments)
            
            # Get transcript with timestamps (for complete and chapters format)
            transcript = get_transcript(url_id, include_timestamps=True)
            
            # Get transcript without timestamps (for raw format)
            transcript_no_times = get_transcript(url_id, include_timestamps=False)
            
            # Get chapters if format style is 'chapters'
            chapters = []
            transcript_by_chapters = None
            
            if self.youtube_format_style == "chapters":
                chapters = get_chapter_info(url_id)
                
                # Organize transcript by chapters if chapters are available
                if chapters:
                    transcript_by_chapters = organize_transcript_by_chapters(transcript, chapters)
            
            # Calculate token count (approximate)
            token_count = len((video_info.get('description', '') + transcript or '').split())
            
            return {
                'url': url,
                'title': f"{video_info['title']} - YouTube",
                'content_text': f"Title: {video_info['title']}\n\nChannel: {video_info['channel']}\n\nDescription: {video_info['description']}\n\nTranscript:\n{transcript}",
                'content_html': f"<h1>{video_info['title']}</h1><p>Channel: {video_info['channel']}</p><div>{video_info['description']}</div><h2>Transcript</h2><div>{transcript}</div>",
                'content': f"<h1>{video_info['title']}</h1><p>Channel: {video_info['channel']}</p><div>{video_info['description']}</div><h2>Transcript</h2><div>{transcript}</div>",
                'images': [],
                'token_count': token_count,
                'processing_time': 0,
                'youtube_data': {
                    'type': 'video',
                    'video_info': video_info,
                    'transcript': transcript,
                    'transcript_no_times': transcript_no_times,
                    'chapters': chapters,
                    'transcript_by_chapters': transcript_by_chapters
                }
            }
        
        elif url_type == 'playlist':
            # Process playlist - get all video IDs and their transcripts
            video_ids = get_playlist_videos(url_id, self.max_videos)
            
            if not video_ids:
                return {
                    'url': url,
                    'title': "YouTube Playlist - No Videos Found",
                    'content_text': "Could not retrieve videos from playlist.",
                    'content_html': "<p>Could not retrieve videos from playlist.</p>",
                    'content': "<p>Could not retrieve videos from playlist.</p>",
                    'images': [],
                    'token_count': 0,
                    'processing_time': 0
                }
            
            # Get playlist info and process each video
            all_videos_data = []
            combined_transcript = ""
            combined_content = ""
            total_tokens = 0
            
            for i, vid_id in enumerate(video_ids):
                try:
                    video_info = get_video_info(vid_id, include_comments=self.include_comments)
                    transcript = get_transcript(vid_id, include_timestamps=True)
                    transcript_no_times = get_transcript(vid_id, include_timestamps=False)
                    
                    video_data = {
                        'title': video_info['title'],
                        'channel': video_info.get('channel', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={vid_id}",
                        'description': video_info.get('description', ''),
                        'transcript': transcript,
                        'transcript_no_times': transcript_no_times,
                        'comments': video_info.get('comments', [])
                    }
                    
                    all_videos_data.append(video_data)
                    
                    # Add to combined content with separator
                    if i > 0:
                        combined_transcript += "\n\n" + "=" * 40 + "\n\n"
                        combined_content += "\n\n" + "=" * 40 + "\n\n"
                    
                    # Add to combined transcript
                    combined_transcript += f"Video {i+1}: {video_data['title']}\n\n{transcript}"
                    
                    # Add to combined content HTML
                    combined_content += f"<h2>Video {i+1}: {video_data['title']}</h2>\n"
                    combined_content += f"<p>Channel: {video_data['channel']}</p>\n"
                    combined_content += f"<p>URL: <a href=\"{video_data['url']}\">{video_data['url']}</a></p>\n"
                    combined_content += f"<div>{video_data['description']}</div>\n"
                    combined_content += f"<h3>Transcript:</h3>\n<div>{transcript}</div>\n"
                    
                    # Add comments if requested
                    if self.include_comments and 'comments' in video_info:
                        comment_text = "\n\nComments:\n" + "\n".join([
                            f"- {comment['author']}: {comment['text']}" 
                            for comment in video_info['comments'][:10]  # Limit to 10 comments per video
                        ])
                        combined_transcript += comment_text
                        
                        comment_html = "<h3>Comments:</h3>\n<ul>\n" + "\n".join([
                            f"<li><strong>{comment['author']}</strong>: {comment['text']}</li>" 
                            for comment in video_info['comments'][:10]
                        ]) + "</ul>\n"
                        combined_content += comment_html
                    
                    # Update token count estimate
                    total_tokens += len(transcript.split())
                    
                except Exception as e:
                    logger.error(f"Error processing video {vid_id} from playlist: {e}")
                    # Continue with next video
            
            return {
                'url': url,
                'title': f"YouTube Playlist - {len(all_videos_data)} videos",
                'content_text': combined_transcript,
                'content_html': combined_content,
                'content': combined_content,
                'images': [],
                'token_count': total_tokens,
                'processing_time': 0,
                'youtube_data': {
                    'type': 'playlist',
                    'video_ids': video_ids,
                    'videos': all_videos_data
                }
            }
        
        elif url_type == 'channel':
            # Process channel - get recent video IDs and their transcripts
            video_ids = get_channel_videos(url_id, self.max_videos)
            
            if not video_ids:
                return {
                    'url': url,
                    'title': "YouTube Channel - No Videos Found",
                    'content_text': "Could not retrieve videos from channel.",
                    'content_html': "<p>Could not retrieve videos from channel.</p>",
                    'content': "<p>Could not retrieve videos from channel.</p>",
                    'images': [],
                    'token_count': 0,
                    'processing_time': 0
                }
            
            # Get channel info and process each video (similar to playlist code)
            all_videos_data = []
            combined_transcript = ""
            combined_content = ""
            total_tokens = 0
            
            for i, vid_id in enumerate(video_ids):
                try:
                    video_info = get_video_info(vid_id, include_comments=self.include_comments)
                    transcript = get_transcript(vid_id, include_timestamps=True)
                    transcript_no_times = get_transcript(vid_id, include_timestamps=False)
                    
                    video_data = {
                        'title': video_info['title'],
                        'channel': video_info.get('channel', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={vid_id}",
                        'description': video_info.get('description', ''),
                        'transcript': transcript,
                        'transcript_no_times': transcript_no_times,
                        'comments': video_info.get('comments', [])
                    }
                    
                    all_videos_data.append(video_data)
                    
                    # Add to combined content with separator
                    if i > 0:
                        combined_transcript += "\n\n" + "=" * 40 + "\n\n"
                        combined_content += "\n\n" + "=" * 40 + "\n\n"
                    
                    # Add to combined transcript
                    combined_transcript += f"Video {i+1}: {video_data['title']}\n\n{transcript}"
                    
                    # Add to combined content HTML
                    combined_content += f"<h2>Video {i+1}: {video_data['title']}</h2>\n"
                    combined_content += f"<p>Channel: {video_data['channel']}</p>\n"
                    combined_content += f"<p>URL: <a href=\"{video_data['url']}\">{video_data['url']}</a></p>\n"
                    combined_content += f"<div>{video_data['description']}</div>\n"
                    combined_content += f"<h3>Transcript:</h3>\n<div>{transcript}</div>\n"
                    
                    # Add comments if requested
                    if self.include_comments and 'comments' in video_info:
                        comment_text = "\n\nComments:\n" + "\n".join([
                            f"- {comment['author']}: {comment['text']}" 
                            for comment in video_info['comments'][:10]  # Limit to 10 comments per video
                        ])
                        combined_transcript += comment_text
                        
                        comment_html = "<h3>Comments:</h3>\n<ul>\n" + "\n".join([
                            f"<li><strong>{comment['author']}</strong>: {comment['text']}</li>" 
                            for comment in video_info['comments'][:10]
                        ]) + "</ul>\n"
                        combined_content += comment_html
                    
                    # Update token count estimate
                    total_tokens += len(transcript.split())
                    
                except Exception as e:
                    logger.error(f"Error processing video {vid_id} from channel: {e}")
                    # Continue with next video
            
            channel_name = all_videos_data[0]['channel'] if all_videos_data else 'Unknown'
            
            return {
                'url': url,
                'title': f"YouTube Channel - {channel_name} ({len(all_videos_data)} videos)",
                'content_text': combined_transcript,
                'content_html': combined_content,
                'content': combined_content,
                'images': [],
                'token_count': total_tokens,
                'processing_time': 0,
                'youtube_data': {
                    'type': 'channel',
                    'video_ids': video_ids,
                    'videos': all_videos_data
                }
            }
            
        else:
            return {
                'url': url,
                'title': "Invalid YouTube URL",
                'content_text': "Could not identify valid YouTube URL type.",
                'content_html': "<p>Could not identify valid YouTube URL type.</p>",
                'content': "<p>Could not identify valid YouTube URL type.</p>",
                'images': [],
                'token_count': 0,
                'processing_time': 0
            }