#!/usr/bin/env python3
"""
Example script showing basic usage of WebSeed for web scraping.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import webseed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webseed.cli import run_scraper


def main():
    """Run a basic web scraping example."""
    
    # Example URLs to scrape
    urls = [
        'https://www.example.com',
        'https://www.python.org',
    ]
    
    # Create output directory in the examples folder
    output_path = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_path, exist_ok=True)
    
    # Run the scraper with example parameters
    run_scraper(
        urls=urls,
        mode='basic',           # Use basic scraping mode
        output_method='file',   # Save to file
        format_type='markdown', # Use markdown format
        custom_name='example',  # Custom filename prefix
        output_path=output_path # Where to save output
    )
    
    print(f"Scraping complete! Results saved to {output_path}")


if __name__ == "__main__":
    main()