from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, Any

from webseed.utils.logging import get_logger

logger = get_logger(__name__)


def get_webdriver(headless: bool = True, options: Optional[Options] = None) -> webdriver.Chrome:
    """
    Get a configured Chrome WebDriver instance.
    
    Args:
        headless: Whether to run the browser in headless mode
        options: Chrome options to use (if None, default options will be created)
        
    Returns:
        A configured WebDriver instance
    """
    if options is None:
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        raise