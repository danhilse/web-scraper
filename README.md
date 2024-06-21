# Web Scraper

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Last Commit](https://img.shields.io/github/last-commit/danhilse/web-scraper)

A powerful command-line web scraper tool that extracts content from websites and saves it to organized text files.

![Web Scraper Demo](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOTZtMG91aXkyMnJ5eXo5NXB0cTk3dnA5Z3Nwa3gyZ3dldGthbTBnNSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LL6x8hTiAExvxVbe3q/giphy.gif)

## Features

- Scrape content from a single URL or an entire sitemap
- Group scraped content into separate files based on URL structure
- Output content to multiple text files, organized by website sections
- Executable file for easy use without Python installation

## Installation

1. Clone this repository:
git clone https://github.com/yourusername/web-scraper.git

2. Install the required dependencies:
pip install -r requirements.txt

## Usage

To scrape a single URL:
python web_scraper.py https://example.com

To scrape an entire sitemap:
python web_scraper.py https://example.com --sitemap

## Building the Executable

To create a standalone executable:
pyinstaller web_scraper.spec

The executable will be created in the `dist` directory.

## Project Structure

- `web_scraper.py`: Main script containing the web scraper logic
- `requirements.txt`: List of Python dependencies

## Executable

A pre-built executable is available in the `dist` folder. You can download and run it directly without needing to install Python or any dependencies.

## License

This project is open source and available under the [MIT License](LICENSE).
