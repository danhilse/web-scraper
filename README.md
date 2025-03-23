# contxt: Web Content Collector for LLM Context

A tool for quickly creating context documents for Large Language Models from web sources.

## Features

- **Intelligent Content Extraction**:
  - Automatic boilerplate and navigation removal
  - OpenGraph metadata extraction
  - Main content identification
  - List item deduplication
  - Span concatenation
  - SVG content cleaning

- **Multiple Scraping Modes**:
  - Basic: Fast HTML scraping
  - Advanced: JavaScript support via Selenium
  - Super: Extended wait time for complex sites
  
- **Smart Image Handling**:
  - Hash-based deduplication
  - Relative URL resolution
  - Date-based organization
  - Dimension extraction
  
- **Content Metrics**:
  - Token counting for LLM context estimation
  - Processing time tracking
  
- **Flexible Output Options**:
  - **Formats**:
    - Markdown: Clean, readable format
    - XML: Structured, machine-readable format
    - Raw HTML: Cleaned HTML without boilerplate
  - **Destinations**:
    - Print to console
    - Save to file
    - Copy to clipboard
    
- **URL Management**:
  - Pattern-based URL filtering
  - Batch processing
  
- **User Experience**:
  - Interactive CLI with color-coded output
  - Detailed progress tracking
  - Timing information

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/contxt.git
cd contxt

# Install the package
pip install -e .
```

## Usage

### Basic Usage

```bash
# Interactive mode with guided prompts
contxt

# Direct mode with URL(s)
contxt https://example.com https://another-example.com

# With options
contxt https://example.com -m advanced -f markdown -o file -i

# Ignore specific URL patterns
contxt https://example.com --ignore-pattern /tags/ --ignore-pattern /categories/

# Custom naming for output files
contxt https://example.com -o file --custom-name my_project

# Advanced scraping with image downloading
contxt https://example.com -m super -i -o file
```

### Command-line Options

- **Scraping Options**:
  - `--mode, -m`: Scraping mode (`basic`, `advanced`, or `super`)
  - `--include-images, -i`: Include image references and download images when saving to file
  - `--ignore-pattern`: URL patterns to ignore (can be specified multiple times)
  - `--no-og-metadata`: Don't extract OpenGraph metadata

- **Output Options**:
  - `--format, -f`: Output format (`markdown`, `xml`, or `raw`)
  - `--output, -o`: Output destination (`print`, `file`, or `clipboard`)
  - `--directory, -d`: Output directory when saving to file
  - `--single-file, -s`: Combine all URLs into a single file
  - `--custom-name`: Custom prefix for output files

- **Performance Options**:
  - `--no-processing-time`: Don't show processing time in output
  - `--no-token-count`: Don't show token count in output

- **General Options**:
  - `--config, -c`: Configure default settings
  - `--verbose, -v`: Enable verbose logging
  - `--version`: Show version information

### Configuration

Default settings are stored in `~/.contxt/config.yaml`. You can modify them using the `--config` flag or by editing the file directly.

## Supported Input Sources

- Individual website URLs
- Multiple URLs processed in batch

## Output Options

- **Formats**:
  - Markdown: Clean, readable format with preserved formatting
  - XML: Structured format with metadata and content elements
  - Raw HTML: Cleaned HTML with unnecessary elements removed

- **Destinations**:
  - Print to console
  - Save to file
  - Copy to clipboard

- **Organization**:
  - Single file or multiple files
  - Optional image downloading to /images folder

## Token Counting

contxt provides token count estimates for the extracted content, helping you understand how much of an LLM's context window your content will use.

## License

MIT License