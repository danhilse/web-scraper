# Web Scraper

A command-line web scraper tool that extracts content from websites and saves it to a text file.

## Features

- Scrape content from a single URL or an entire sitemap
- Output all content to a single text file
- Executable file for easy use without Python installation

## Installation

1. Clone this repository:
git clone https://github.com/yourusername/web-scraper.git
Copy2. Install the required dependencies:
pip install -r requirements.txt
Copy
## Usage

To scrape a single URL:
python web_scraper.py https://example.com
Copy
To scrape an entire sitemap:
python web_scraper.py https://example.com --sitemap
Copy
## Building the Executable

To create a standalone executable:
pyinstaller web_scraper.spec
Copy
The executable will be created in the `dist` directory.

## License

This project is open source and available under the [MIT License](LICENSE).
