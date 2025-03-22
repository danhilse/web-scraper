import os
import yaml
from typing import Dict, Any, Optional

from webseed.utils.logging import get_logger

logger = get_logger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'scraping': {
        'default_mode': 'basic',
        'timeout': 30,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    },
    'output': {
        'default_format': 'markdown',
        'default_path': os.getcwd(),
    },
    'rate_limiting': {
        'requests_per_minute': 10,
        'domain_specific': {
            'github.com': 5,
            'youtube.com': 3,
        }
    },
    'logging': {
        'level': 'INFO',
        'file': None,
    }
}


def find_config_file() -> Optional[str]:
    """
    Find the configuration file in standard locations.
    
    Returns:
        Path to config file if found, None otherwise
    """
    # Check in current directory
    if os.path.exists('webseed.yaml'):
        return 'webseed.yaml'
    
    if os.path.exists('webseed.yml'):
        return 'webseed.yml'
    
    # Check in config subdirectory
    if os.path.exists('config/default.yaml'):
        return 'config/default.yaml'
    
    # Check in user home directory
    home_dir = os.path.expanduser('~')
    if os.path.exists(os.path.join(home_dir, '.webseed.yaml')):
        return os.path.join(home_dir, '.webseed.yaml')
    
    # Check in environment variable
    env_config = os.environ.get('WEBSEED_CONFIG')
    if env_config and os.path.exists(env_config):
        return env_config
    
    return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file, falling back to defaults.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    if not config_path:
        config_path = find_config_file()
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                
            if user_config:
                # Recursively merge user config into default config
                deep_merge(config, user_config)
            
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration file {config_path}: {e}")
    else:
        logger.info("Using default configuration")
    
    return config


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary with values to override
        
    Returns:
        Merged dictionary
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    
    return base


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a value from the configuration using a dot-separated path.
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated path to the value (e.g., 'scraping.timeout')
        default: Default value if path not found
        
    Returns:
        Value from the configuration or default
    """
    keys = key_path.split('.')
    result = config
    
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    
    return result