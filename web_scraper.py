import requests
from bs4 import BeautifulSoup, NavigableString
import xml.etree.ElementTree as ET
import argparse
import os
from urllib.parse import urlparse, urljoin
import string

def get_domain_name(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain.replace('www.', '')

def is_meaningful(text):
    cleaned_text = text.translate(str.maketrans('', '', string.punctuation)).lower()
    words = cleaned_text.split()
    if len(words) < 2:
        return False
    alphanumeric_ratio = sum(c.isalnum() for c in cleaned_text) / len(cleaned_text) if cleaned_text else 0
    return alphanumeric_ratio > 0.5

def extract_text_from_url(url, output_file):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    last_content = ""

    def write_and_print(text):
        nonlocal last_content
        if text.strip() and text.strip() != last_content and is_meaningful(text):
            print(text)
            output_file.write(text + '\n')
            last_content = text.strip()

    title = soup.title.string if soup.title else "No title found"
    write_and_print(f"Title: {title}\n")

    main_content = soup.body or soup

    for element in main_content.descendants:
        if isinstance(element, NavigableString):
            continue

        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            header_text = element.text.strip()
            if len(header_text) > 1 and not header_text.isdigit():
                write_and_print(f"\n{element.name.upper()}: {header_text}")
        elif element.name == 'p':
            write_and_print(element.text.strip())
        elif element.name == 'ul':
            items = [li.text.strip() for li in element.find_all('li', recursive=False)]
            write_and_print("Unordered List: " + ", ".join(items))
        elif element.name == 'ol':
            items = [li.text.strip() for li in element.find_all('li', recursive=False)]
            write_and_print("Ordered List: " + ", ".join(items))

def get_sitemap_urls(base_url):
    common_sitemap_paths = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap/',
        '/sitemap.php',
        '/sitemap.txt'
    ]

    for path in common_sitemap_paths:
        sitemap_url = urljoin(base_url, path)
        try:
            response = requests.get(sitemap_url)
            response.raise_for_status()  # Raise an exception for bad status codes

            if 'xml' in response.headers.get('Content-Type', '').lower():
                root = ET.fromstring(response.content)
                urls = [url.text for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                if urls:
                    print(f"Sitemap found at: {sitemap_url}")
                    return urls
        except requests.RequestException as e:
            print(f"Error accessing {sitemap_url}: {e}")
        except ET.ParseError:
            print(f"Error parsing XML from {sitemap_url}")

    print(f"No sitemap found. Scraping the provided URL: {base_url}")
    return [base_url]

def main():
    parser = argparse.ArgumentParser(description="Web scraper for text content")
    parser.add_argument("url", help="Base URL to scrape")
    parser.add_argument("--sitemap", action="store_true", help="Attempt to find and scrape sitemap")
    args = parser.parse_args()

    urls = get_sitemap_urls(args.url) if args.sitemap else [args.url]

    domain_name = get_domain_name(args.url)
    output_filename = os.path.join(os.getcwd(), f"{domain_name}_content.txt")

    with open(output_filename, 'w', encoding='utf-8') as output_file:
        for index, url in enumerate(urls, 1):
            print(f"\nScraping: {url}")
            output_file.write(f"\n\n--- Content from: {url} ---\n\n")
            extract_text_from_url(url, output_file)

    print(f"All content has been saved to {output_filename}")

if __name__ == "__main__":
    main()
