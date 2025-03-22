#!/usr/bin/env python3
"""
Example script showing how to use WebSeed for scraping YouTube playlists.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import webseed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webseed.cli import run_scraper


def main():
    """Run a YouTube playlist scraping example."""
    
    # Example YouTube playlist URL
    urls = [
        'https://www.youtube.com/playlist?list=PLaEJLf99gDO7mptVmIwFDM78AU-NzxLyM'
    ]
    
    # Create output directory in the examples folder
    output_path = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_path, exist_ok=True)
    
    # Run the scraper with YouTube options
    run_scraper(
        urls=urls,
        output_method='file',       # Save to file
        format_type='markdown',     # Use markdown format
        custom_name='python_tutorials',  # Custom filename prefix
        output_path=output_path,    # Where to save output
        youtube_options={
            'include_comments': True,    # Include comments
            'max_comments': 10,          # Maximum comments per video
            'split_videos': True,        # Split videos into separate files
            'max_videos': 5              # Maximum videos to process
        }
    )
    
    print(f"Scraping complete! Results saved to {output_path}/youtube/")


if __name__ == "__main__":
    main()