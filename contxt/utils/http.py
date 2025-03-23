import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import Optional, Dict, Any

from webseed.utils.logging import get_logger
from webseed.core.rate_limiter import RateLimiter

logger = get_logger(__name__)
rate_limiter = RateLimiter()


def create_session(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: tuple = (500, 502, 504),
    timeout: int = 10
) -> requests.Session:
    """
    Create a requests session with retry capabilities.
    
    Args:
        retries: Number of retries to attempt
        backoff_factor: Backoff factor for retries
        status_forcelist: HTTP status codes to retry on
        timeout: Default request timeout in seconds
        
    Returns:
        Configured requests Session
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.timeout = timeout
    return session


def make_request(
    url: str,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
    verify: bool = True,
    session: Optional[requests.Session] = None
) -> Optional[requests.Response]:
    """
    Make an HTTP request with rate limiting and retries.
    
    Args:
        url: URL to request
        method: HTTP method to use
        headers: Request headers
        params: URL parameters
        data: Request body data
        timeout: Request timeout in seconds
        verify: Whether to verify SSL certificates
        session: Requests session to use (creates a new one if None)
        
    Returns:
        Response object or None if the request failed
    """
    if not session:
        session = create_session(timeout=timeout)
    
    if not headers:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    # Apply rate limiting
    rate_limiter.wait(url)
    
    try:
        response = session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            timeout=timeout,
            verify=verify
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None