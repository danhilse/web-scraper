#!/usr/bin/env python3
import argparse
import os
import sys
from typing import List, Optional, Dict, Any

from contxt.core.config import load_config
from contxt.sources.web.extractor import extract_content
from contxt.outputs.base import OutputFormat
from contxt.outputs.markdown import MarkdownOutput
from contxt.outputs.tagged import TaggedOutput
from contxt.processors.image import ImageProcessor


def parse_urls(urls_input: str) -> List[str]:
    """Parse URL input which could be space-separated or a comma-separated list."""
    if ',' in urls_input:
        return [url.strip() for url in urls_input.split(',')]
    return [url.strip() for url in urls_input.split()]


def interactive_mode():
    """Run the CLI in interactive mode, asking the user for input."""
    print("Welcome to contxt CLI!")
    
    # Get URLs
    urls_input = input("Enter URLs (space or comma-separated): ")
    urls = parse_urls(urls_input)
    
    if not urls:
        print("No URLs provided. Exiting.")
        sys.exit(1)
    
    # Get custom name
    custom_name = input("Enter custom name for output (press Enter to use default): ").strip() or None
    
    # Choose scraping mode
    while True:
        mode_input = input("Choose scraping mode (b: basic, a: advanced, s: super): ").lower()
        if mode_input in ['b', 'a', 's']:
            mode = {'b': 'basic', 'a': 'advanced', 's': 'super'}[mode_input]
            break
        else:
            print("Please enter 'b' for basic, 'a' for advanced, or 's' for super mode.")
    
    # Choose output method
    while True:
        output_input = input("Choose output method (p: print to console, f: save to file): ").lower()
        if output_input in ['p', 'f']:
            output_method = 'print' if output_input == 'p' else 'file'
            break
        else:
            print("Please enter 'p' for print or 'f' for file output.")
    
    # Choose format type
    while True:
        format_input = input("Choose format type (t: tagged, m: markdown, i: images): ").lower()
        if format_input in ['t', 'm', 'i']:
            format_type = {'t': 'tagged', 'm': 'markdown', 'i': 'img'}[format_input]
            break
        else:
            print("Please enter 't' for tagged, 'm' for markdown formatting, or 'i' for image download.")
    
    # Choose output location if saving to file
    output_path = None
    if output_method == 'file':
        default_path = os.getcwd()
        path_input = input(f"Enter output path (press Enter for current directory: {default_path}): ").strip() or default_path
        output_path = path_input
    
    # Run the scraper
    run_scraper(
        urls=urls,
        mode=mode,
        output_method=output_method,
        format_type=format_type,
        custom_name=custom_name,
        output_path=output_path
    )


def run_scraper(
    urls: List[str],
    mode: str = 'basic',
    output_method: str = 'file',
    format_type: str = 'markdown',
    custom_name: Optional[str] = None,
    output_path: Optional[str] = None,
    ignore_subfolder: Optional[str] = None,
    youtube_options: Optional[Dict[str, Any]] = None
):
    """Run the scraper with the specified parameters."""
    # Filter URLs to ignore those containing the specified subfolder
    if ignore_subfolder:
        filtered_urls = [url for url in urls if f"/{ignore_subfolder}/" not in url]
    else:
        filtered_urls = urls
    
    # Load configuration
    config = load_config()
    
    # Set default YouTube options if not provided
    if youtube_options is None:
        youtube_options = {
            'include_comments': False,
            'max_comments': 30,
            'split_videos': False,
            'max_videos': 10
        }
    
    # Separate YouTube URLs from regular web URLs
    from contxt.sources.youtube.source import is_youtube_url
    youtube_urls = [url for url in filtered_urls if is_youtube_url(url)]
    web_urls = [url for url in filtered_urls if not is_youtube_url(url)]
    
    # Process YouTube URLs
    youtube_results = []
    if youtube_urls:
        from contxt.sources.youtube.source import process_youtube_url, format_youtube_content_as_markdown, format_youtube_content_as_tagged
        
        # Configure cache if needed
        if 'cache_dir' in youtube_options and youtube_options['cache_dir']:
            from contxt.sources.youtube.cache import TranscriptCache
            cache = TranscriptCache(youtube_options['cache_dir'])
            
        # Clean cache if requested
        if youtube_options.get('clean_cache', False):
            from contxt.sources.youtube.cache import get_cache
            cache = get_cache()
            removed_count = cache.clean_old_cache()
            print(f"Cleaned YouTube cache: {removed_count} files removed")
        
        for url in youtube_urls:
            print(f"Processing YouTube content: {url}")
            content = process_youtube_url(
                url,
                include_comments=youtube_options['include_comments'],
                max_comments=youtube_options['max_comments'],
                max_videos=youtube_options['max_videos'],
                use_cache=youtube_options.get('use_cache', True)
            )
            
            if content:
                youtube_results.append(content)
    
    # Process regular web URLs
    web_results = []
    for url in web_urls:
        print(f"Scraping: {url}")
        content = extract_content(url, mode)
        
        if content:
            if format_type == 'img':
                # Process images
                processor = ImageProcessor(
                    base_url=url,
                    output_path=output_path or os.getcwd(),
                    custom_name=custom_name
                )
                result = processor.process(content)
            else:
                # Process text content
                output_format = OutputFormat.from_string(format_type)
                result = output_format.format(content, url)
            
            web_results.append(result)
    
    # Handle output for YouTube content
    if youtube_results:
        from contxt.sources.youtube.source import format_youtube_content_as_markdown, format_youtube_content_as_tagged
        
        if output_method == 'print':
            for result in youtube_results:
                if format_type == 'markdown':
                    print(format_youtube_content_as_markdown(result))
                else:
                    print(format_youtube_content_as_tagged(result))
        else:  # Save to file
            from contxt.outputs.youtube import YouTubeOutput
            
            save_path = output_path or os.getcwd()
            output_handler = YouTubeOutput(
                save_path, 
                custom_name,
                split_videos=youtube_options['split_videos']
            )
            output_handler.save(youtube_results)
    
    # Handle output for web content
    if web_results:
        if output_method == 'print':
            for result in web_results:
                print(result)
        else:  # Save to file
            save_path = output_path or os.getcwd()
            os.makedirs(save_path, exist_ok=True)
            
            if format_type == 'markdown':
                output_handler = MarkdownOutput(save_path, custom_name)
                output_handler.save(web_results)
            elif format_type == 'tagged':
                output_handler = TaggedOutput(save_path, custom_name)
                output_handler.save(web_results)
            # For image output, the ImageProcessor already handles saving


def main():
    parser = argparse.ArgumentParser(description='contxt - Context builder from web content')
    
    # Basic options
    parser.add_argument('--urls', help='Space-separated list of URLs to scrape')
    parser.add_argument('--mode', choices=['basic', 'advanced', 'super'], default='basic',
                       help='Scraping mode: basic, advanced, or super')
    parser.add_argument('--output', choices=['print', 'file'], default='file',
                       help='Output method: print to console or save to file')
    parser.add_argument('--format', choices=['tagged', 'markdown', 'img'], default='markdown',
                       help='Output format: tagged, markdown, or images')
    parser.add_argument('--name', help='Custom name for output files')
    parser.add_argument('--path', help='Output path for saving files')
    parser.add_argument('--ignore', help='Subfolder to ignore in URLs')
    parser.add_argument('--interactive', action='store_true', 
                       help='Run in interactive mode, prompting for options')
    
    # YouTube specific options
    youtube_group = parser.add_argument_group('YouTube options')
    youtube_group.add_argument('--youtube-comments', action='store_true',
                              help='Include YouTube comments')
    youtube_group.add_argument('--max-comments', type=int, default=30,
                              help='Maximum number of comments to collect')
    youtube_group.add_argument('--split-videos', action='store_true',
                              help='Split videos into separate files')
    youtube_group.add_argument('--max-videos', type=int, default=10,
                              help='Maximum videos to collect from channels')
    youtube_group.add_argument('--no-cache', action='store_true',
                              help='Disable caching for YouTube content')
    youtube_group.add_argument('--clean-cache', action='store_true',
                              help='Clean the YouTube cache before processing')
    youtube_group.add_argument('--cache-dir', type=str,
                              help='Custom directory for YouTube cache')
    
    args = parser.parse_args()
    
    youtube_options = {
        'include_comments': args.youtube_comments,
        'max_comments': args.max_comments,
        'split_videos': args.split_videos,
        'max_videos': args.max_videos,
        'use_cache': not args.no_cache,
        'clean_cache': args.clean_cache,
        'cache_dir': args.cache_dir
    }
    
    if args.interactive:
        interactive_mode()
    elif args.urls:
        run_scraper(
            urls=parse_urls(args.urls),
            mode=args.mode,
            output_method=args.output,
            format_type=args.format,
            custom_name=args.name,
            output_path=args.path,
            ignore_subfolder=args.ignore,
            youtube_options=youtube_options
        )
    else:
        interactive_mode()


if __name__ == "__main__":
    main()