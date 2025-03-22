import time
from urllib.parse import urlparse
from collections import defaultdict
from typing import Dict, Optional

from webseed.utils.logging import get_logger
from webseed.core.config import load_config, get_config_value

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter to control request frequency to domains."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the rate limiter.
        
        Args:
            config: Configuration dictionary (if None, will load from default)
        """
        if config is None:
            config = load_config()
        
        self.default_rate = get_config_value(
            config, 'rate_limiting.requests_per_minute', 10)
        
        self.domain_rates = get_config_value(
            config, 'rate_limiting.domain_specific', {})
        
        # Track last request time per domain
        self.last_request_time: Dict[str, float] = defaultdict(float)
    
    def get_delay(self, domain: str) -> float:
        """
        Get the minimum delay for a domain in seconds.
        
        Args:
            domain: Domain name
            
        Returns:
            Minimum delay in seconds between requests
        """
        if domain in self.domain_rates:
            rate = self.domain_rates[domain]
        else:
            rate = self.default_rate
        
        # Convert requests per minute to seconds per request
        return 60.0 / rate
    
    def wait(self, url: str) -> None:
        """
        Wait the appropriate amount of time before making a request.
        
        Args:
            url: URL to request
        """
        domain = urlparse(url).netloc
        delay = self.get_delay(domain)
        
        # Calculate time to wait
        elapsed = time.time() - self.last_request_time[domain]
        wait_time = max(0, delay - elapsed)
        
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
            time.sleep(wait_time)
        
        # Update last request time
        self.last_request_time[domain] = time.time()