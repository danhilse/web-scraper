# WebSeed

A modular web content scraping tool that can extract content from various sources and process it into different formats.

## Features

- Scrape content from websites with different levels of JavaScript handling
- Support for multiple sources:
  - Web pages with smart HTML-to-Markdown conversion
  - YouTube videos, playlists, and channels with transcript extraction
  - GitHub repositories and issues (coming soon)
  - Instagram profiles (coming soon)
- Multiple output formats (Markdown, tagged text, image download)
- YouTube-specific features:
  - Automatic transcript extraction
  - Optional comment collection
  - Support for individual videos, playlists, and channels
  - Split videos into separate files or combine into one document
- Configurable rate limiting to respect website policies
- Interactive CLI interface

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/webseed.git
cd webseed

# Install the package
pip install -e .
```

## Quick Start

### Command Line Interface

WebSeed provides a simple CLI that can be used to scrape content:

```bash
# Run in interactive mode (recommended for first-time users)
python -m webseed.cli --interactive

# Scrape web pages
python -m webseed.cli --urls "https://example.com https://python.org" --mode basic --output file --format markdown

# Scrape YouTube content
python -m webseed.cli --urls "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --youtube-comments --output file --format markdown

# Scrape YouTube playlist with comments and split each video into a separate file
python -m webseed.cli --urls "https://www.youtube.com/playlist?list=PLaEJLf99gDO7mptVmIwFDM78AU-NzxLyM" --youtube-comments --split-videos --max-comments 20
```

### Python API

```python
from webseed.cli import run_scraper

# Example usage for web pages
run_scraper(
    urls=['https://example.com', 'https://python.org'],
    mode='basic',          # 'basic', 'advanced', or 'super'
    output_method='file',  # 'print' or 'file'
    format_type='markdown', # 'markdown', 'tagged', or 'img'
    custom_name='my_scrape', # Custom name prefix for output
    output_path='/path/to/output' # Where to save output
)

# Example usage for YouTube content
run_scraper(
    urls=['https://www.youtube.com/watch?v=dQw4w9WgXcQ', 
          'https://www.youtube.com/playlist?list=PLaEJLf99gDO7mptVmIwFDM78AU-NzxLyM'],
    output_method='file',
    format_type='markdown',
    custom_name='youtube_content',
    youtube_options={
        'include_comments': True,
        'max_comments': 20,
        'split_videos': True,
        'max_videos': 10
    }
)
```

### Mixed Content

WebSeed automatically detects and appropriately processes different types of URLs. You can mix YouTube and web URLs in the same command:

```bash
python -m webseed.cli --urls "https://example.com https://www.youtube.com/watch?v=dQw4w9WgXcQ" --youtube-comments
```

## Scraping Modes

WebSeed supports three scraping modes:

- **Basic**: Uses the `requests` library for simple HTML content
- **Advanced**: Uses a headless browser for JavaScript-heavy sites
- **Super**: Uses a full browser with longer waits for complex sites

## Output Formats

- **Markdown**: Clean, readable Markdown format with support for:
  - Table preservation
  - Code block formatting
  - Image references
  - Link preservation
  - Smart content cleaning
- **Tagged**: Simple text format with element types as tags
- **Images**: Downloads and saves all images from the pages

## YouTube Options

WebSeed provides several options for YouTube content:

- **--youtube-comments**: Include comments in the output (default: false)
- **--max-comments**: Maximum number of comments to fetch per video (default: 30)
- **--split-videos**: Save each video to a separate file (default: false)
- **--max-videos**: Maximum number of videos to process from channels/playlists (default: 10)
- **--no-cache**: Disable caching for YouTube content (default: caching enabled)
- **--clean-cache**: Clean the YouTube cache before processing
- **--cache-dir**: Custom directory for YouTube cache

## Configuration

WebSeed can be configured via a YAML file. By default, it looks for:

1. `webseed.yaml` in the current directory
2. `config/default.yaml` in the project directory
3. `~/.webseed.yaml` in the user's home directory
4. Path specified by the `WEBSEED_CONFIG` environment variable

Example configuration:

```yaml
scraping:
  default_mode: basic
  timeout: 30

output:
  default_format: markdown
  default_path: null  # Uses current working directory

rate_limiting:
  requests_per_minute: 10
  domain_specific:
    github.com: 5
    youtube.com: 3
```

## Examples

See the `examples` directory for usage examples:

- `basic_web_scraping.py`: Simple web scraping example
- `github_repo.py`: Scraping GitHub repositories
- `youtube_playlist.py`: Extracting YouTube playlist content

## License

MIT