import os
import yaml
from pathlib import Path

CONFIG_DIR = Path.home() / ".contxt"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "output": {
        "format": "markdown",  # markdown, xml, raw
        "destination": "print", # print, file, clipboard
        "directory": None,      # Default is current directory
        "saved_directories": [  # Saved directory paths with names
            # Example: {"name": "Documents", "path": "~/Documents/contxt_output"}
        ],
    },
    "scraping": {
        "mode": "basic",       # basic, advanced, super
        "include_images": False,
        "max_depth": 1,        # For future website crawling
        "ignore_patterns": [],  # URL patterns to ignore (e.g., "/tags/", "/category/")
        "extract_og_metadata": True,  # Extract OpenGraph metadata
    },
    "organization": {
        "by_source": True,
        "by_topic": False,
        "single_file": True,
    },
    "performance": {
        "show_processing_time": True,  # Show processing time in output
        "show_token_count": True,      # Show token count in output
    },
    "youtube": {
        "include_comments": False,
        "max_videos": 30,
        "include_description": True,
        "format_style": "complete"  # Add this new default
    },
}


def ensure_config_dir():
    """Ensure the config directory exists."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)


def load_config():
    """Load configuration from file or create with defaults if it doesn't exist."""
    ensure_config_dir()
    
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
    
    # Handle backward compatibility with old config format
    if config.get("output", {}).get("print_to_console") is not None:
        if "destination" not in config["output"]:
            config["output"]["destination"] = "print" if config["output"]["print_to_console"] else "file"
    
    # Ensure all default keys exist
    for section, values in DEFAULT_CONFIG.items():
        if section not in config:
            config[section] = {}
        for key, value in values.items():
            if key not in config[section]:
                config[section][key] = value
    
    return config


def save_config(config):
    """Save configuration to file."""
    ensure_config_dir()
    
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def update_config(section, key, value):
    """Update a specific config value."""
    config = load_config()
    if section not in config:
        config[section] = {}
    config[section][key] = value
    save_config(config)