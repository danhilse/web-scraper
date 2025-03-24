import click
import sys
import os
import signal
import logging
import time
import re
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from .scraper import Scraper
from .formatters import get_formatter
from .config import load_config
from .outputs import get_output_handler
# Import the interactive module functions
from .interactive import interactive_prompt, configuration_prompt, set_is_exiting, youtube_options_prompt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create console for rich output
console = Console()

# Flag to track if we're exiting due to keyboard interrupt
is_exiting = False

def signal_handler(sig, frame):
    """Handle keyboard interrupt gracefully"""
    global is_exiting
    is_exiting = True
    # Set the flag in interactive module as well
    set_is_exiting(True)
    console.print("\n[yellow]Keyboard interrupt detected. Exiting gracefully...[/yellow]")
    sys.exit(0)

def is_youtube_url(url):
    """Check if a URL is a YouTube URL"""
    return 'youtube.com' in url or 'youtu.be' in url

def process_url(url, config):
    """Process a single URL and return the formatted content."""
    global is_exiting
    try:
        # Check if we're exiting
        if is_exiting:
            return None
            
        # Log the start of processing
        console.print(f"Processing: {url}")
        
        # Initialize scraper with configured mode
        scraper = Scraper(
            mode=config["scraping"]["mode"],
            include_comments=config["youtube"].get("include_comments", False),
            max_videos=config["youtube"].get("max_videos", 30),
            youtube_format_style=config["youtube"].get("format_style", "complete")
        )
        
        # Scrape the URL
        scraped_data = scraper.scrape(
            url, 
            include_images=config["scraping"]["include_images"]
        )
        
        if not scraped_data["content"]:
            logger.error(f"Failed to scrape content from {url}")
            console.print(f"[red]Failed to scrape content from {url}[/red]")
            return None
        
        # Download images if requested and saving to file
        image_map = {}
        if config["scraping"]["include_images"] and config["output"]["destination"] == "file":
            output_dir = config["output"].get("directory") or os.getcwd()
            console.print(f"Downloading images from {url}...")
            image_map = scraper.download_images(scraped_data["images"], output_dir)
        
        # Close the scraper to free resources
        scraper.close()
        
        # Get the appropriate formatter for the output format
        if is_youtube_url(url):
            formatter = get_formatter(
                format_type=config["output"]["format"],
                include_images=config["scraping"]["include_images"],
                image_map=image_map,
                youtube_format_style=config["youtube"].get("format_style", "complete")
            )
        else:
            formatter = get_formatter(
                format_type=config["output"]["format"],
                include_images=config["scraping"]["include_images"],
                image_map=image_map
            )
        
        formatted_content = formatter.format(scraped_data)
        
        # Log completion
        processing_time = scraped_data.get("processing_time", 0)
        token_count = scraped_data.get("token_count", 0)
        console.print(f"[green]Completed:[/green] {url} ({processing_time:.2f}s, {token_count:,} tokens)")
        
        return formatted_content, scraped_data["url"], formatter, scraped_data
        
    except KeyboardInterrupt:
        # Handle keyboard interrupt during processing
        console.print(f"\n[yellow]Keyboard interrupt while processing {url}. Stopping...[/yellow]")
        if 'scraper' in locals():
            scraper.close()
        is_exiting = True
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        console.print(f"[red]Error processing {url}: {e}[/red]")
        return None

@click.command()
@click.argument("urls", nargs=-1, required=False)
# Scraping options
@click.option("-m", "--mode", type=click.Choice(["basic", "advanced", "super"]), help="Scraping mode")
@click.option("-i", "--include-images", is_flag=True, help="Include image references")

# YouTube options
@click.option("--include-comments", is_flag=True, help="Include YouTube comments (YouTube URLs only)")
@click.option("--max-videos", type=int, default=30, help="Maximum number of videos to process for playlists/channels")

# Output options
@click.option("-f", "--format", type=click.Choice(["markdown", "xml", "raw"]), help="Output format")
@click.option("-o", "--output", type=click.Choice(["print", "file", "clipboard"]), help="Output destination")
@click.option("-d", "--directory", type=click.Path(exists=True, file_okay=False), help="Output directory (when saving to file)")
@click.option("-s", "--single-file", is_flag=True, help="Combine all URLs into a single file")
@click.option("--custom-name", help="Custom prefix for output files")
@click.option("--youtube-format", type=click.Choice(["complete", "raw", "chapters"]), help="YouTube output format (for YouTube URLs only)")

# General options
@click.option("-c", "--config", is_flag=True, help="Configure default settings")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--version", is_flag=True, help="Show version information")
def main(urls, mode, format, include_images, include_comments, max_videos,
         output, directory, single_file, custom_name, youtube_format,
         config, verbose, version):
    """
    Web Content Collector for LLM Context.
    
    If URLS are provided, processes them directly with the specified options.
    If no URLS are provided, runs in interactive mode.
    """
    # Register signal handler for keyboard interrupt
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Show version and exit if requested
        if version:
            from . import __version__
            console.print(f"contxt version {__version__}")
            return
        
        # Set up verbose logging if requested
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Load configuration
        user_config = load_config()
        
        # Ensure output destination exists in config (backward compatibility)
        if "destination" not in user_config["output"]:
            user_config["output"]["destination"] = "print" if user_config["output"].get("print_to_console", False) else "file"
        
        # Ensure YouTube config section exists
        if "youtube" not in user_config:
            user_config["youtube"] = {
                "include_comments": False,
                "max_videos": 30,
                "include_description": True
            }
        
        # If config flag is set, just run configuration and exit
        if config:
            configuration_prompt()
            return
        
        # Override config with command-line options
        # Scraping options
        if mode:
            user_config["scraping"]["mode"] = mode
        if include_images is not None:
            user_config["scraping"]["include_images"] = include_images
            
        # YouTube options
        if include_comments is not None:
            user_config["youtube"]["include_comments"] = include_comments
        if max_videos is not None:
            user_config["youtube"]["max_videos"] = max_videos
        if youtube_format is not None:
            user_config["youtube"]["format_style"] = youtube_format
            
        # Output options
        if format:
            user_config["output"]["format"] = format
        if output:
            user_config["output"]["destination"] = output
        if directory:
            user_config["output"]["directory"] = directory
        if single_file is not None:
            user_config["organization"]["single_file"] = single_file
        if custom_name:
            user_config["output"]["custom_name"] = custom_name
        
        # Determine whether to run in interactive or direct mode
        if not urls:
            # Interactive mode - no URLs provided
            urls, directory, interactive_config = interactive_prompt(user_config)
            
            # Check if any URLs are YouTube URLs and prompt for YouTube options
            has_youtube_urls = any(is_youtube_url(url) for url in urls)
            if has_youtube_urls:
                youtube_options = youtube_options_prompt(user_config)
                interactive_config["youtube"] = youtube_options
            
            # Use interactive config
            user_config = interactive_config
        else:
            # URLs provided as command line arguments
            # Only prompt for YouTube options if needed
            has_youtube_urls = any(is_youtube_url(url) for url in urls)
            if has_youtube_urls:
                console.print("\n[cyan bold]YouTube Options[/cyan bold]")
                youtube_options = youtube_options_prompt(user_config)
                user_config["youtube"] = youtube_options
        
        if not urls:
            urls = ["https://www.ableton.com/en/live/all-new-features/"]
            console.print("[yellow]No URLs provided. Set to example page.[/yellow]")
        
        # Process URLs with simplified progress display
        console.print("\n[cyan bold]Processing URLs...[/cyan bold]")
        
        # Process each URL
        all_content = []
        stats = {
            "total": len(urls),
            "successful": 0,
            "failed": 0,
            "total_tokens": 0,
            "total_time": 0,
            "total_images": 0,
            "youtube_videos": 0
        }
        
        # Determine the extension based on the selected format
        extension_map = {
            "markdown": ".md",
            "xml": ".xml", 
            "raw": ".html"
        }
        extension = extension_map.get(user_config["output"]["format"])
        
        # Create the output_handler based on destination
        if user_config["output"]["destination"] == "print":
            output_handler = get_output_handler("print", console=console)
        elif user_config["output"]["destination"] == "file":
            output_handler = get_output_handler(
                "file",
                directory=user_config["output"].get("directory"),
                custom_name=user_config["output"].get("custom_name")
            )
        elif user_config["output"]["destination"] == "clipboard":
            output_handler = get_output_handler("clipboard")
        else:
            output_handler = get_output_handler("print", console=console)
        
        # Process URLs
        for url in urls:
            if is_exiting:
                break
                
            result = process_url(url, user_config)
            
            if result:
                formatted_content, source_url, formatter, scraped_data = result
                all_content.append((formatted_content, source_url, formatter, scraped_data))
                
                # Update stats
                stats["successful"] += 1
                stats["total_tokens"] += scraped_data.get("token_count", 0)
                stats["total_time"] += scraped_data.get("processing_time", 0)
                stats["total_images"] += len(scraped_data.get("images", []))
                
                # Count YouTube videos if applicable
                if scraped_data.get("youtube_data") is not None:
                    if scraped_data["youtube_data"].get("type") == "video":
                        stats["youtube_videos"] += 1
                    elif scraped_data["youtube_data"].get("type") in ["playlist", "channel"]:
                        stats["youtube_videos"] += len(scraped_data["youtube_data"].get("video_ids", []))
                
                # Print immediately if not combining and destination is print
                if not user_config["organization"]["single_file"] and user_config["output"]["destination"] == "print":
                    output_handler.output(formatted_content, source=source_url)
            else:
                # Count as failed
                stats["failed"] += 1
            
            if is_exiting:
                break
        
        # If exiting or no content, don't continue with output
        if is_exiting or not all_content:
            if not all_content:
                console.print("[red]No content was successfully processed.[/red]")
            return
            
        # Handle output based on configuration
        if user_config["organization"]["single_file"] and len(all_content) > 1:
            # Combine all content into a single output
            combined = "\n\n" + "=" * 50 + "\n\n".join([content for content, _, _, _ in all_content])
            
            if user_config["output"]["destination"] == "print":
                output_handler.output(combined)
            elif user_config["output"]["destination"] == "file":
                # Create a combined filename
                if user_config["output"].get("custom_name"):
                    source_name = f"{user_config['output']['custom_name']}_combined"
                else:
                    # Try to use the title of the first document if available
                    first_scraped_data = all_content[0][3] if all_content else {}
                    first_title = first_scraped_data.get("title")
                    if first_title:
                        source_name = f"{first_title}_plus_{len(all_content)-1}_more"
                    else:
                        source_name = "combined_" + "_".join([
                            urlparse(url).netloc for url in [item[1] for item in all_content][:3]
                        ])
                file_path = output_handler.output(
                    combined, 
                    source=source_name, 
                    extension=extension,
                    title=source_name
                )
                if file_path:
                    console.print(f"[green bold]Combined content saved to:[/green bold] {file_path}")
            elif user_config["output"]["destination"] == "clipboard":
                success = output_handler.output(combined)
                if success:
                    console.print("[green bold]Combined content copied to clipboard.[/green bold]")
                else:
                    console.print("[red]Failed to copy content to clipboard.[/red]")
        elif not user_config["organization"]["single_file"] or len(all_content) == 1:
            # Handle individual outputs
            if user_config["output"]["destination"] == "print" and len(all_content) == 1:
                # Single file print case
                output_handler.output(all_content[0][0], source=all_content[0][1])
            elif user_config["output"]["destination"] == "file":
                # Save each file individually
                for content, url, _, _ in all_content:
                    file_path = output_handler.output(content, source=url, extension=extension)
                    if file_path:
                        console.print(f"[green bold]Content from {url} saved to:[/green bold] {file_path}")
            elif user_config["output"]["destination"] == "clipboard" and len(all_content) == 1:
                # Copy to clipboard (only for single URL)
                success = output_handler.output(all_content[0][0])
                if success:
                    console.print(f"[green bold]Content from {all_content[0][1]} copied to clipboard.[/green bold]")
                else:
                    console.print("[red]Failed to copy content to clipboard.[/red]")
            elif user_config["output"]["destination"] == "clipboard" and len(all_content) > 1:
                console.print("[yellow]Multiple URLs processed but clipboard can only hold one. Nothing copied.[/yellow]")
                console.print("[yellow]Use --single-file option to combine all content for clipboard.[/yellow]")
        
        # Print summary statistics
        console.print("\n[cyan bold]Processing Summary[/cyan bold]")
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="green")
        stats_table.add_column("Value", style="cyan")
        
        stats_table.add_row("URLs processed", f"{stats['total']}")
        stats_table.add_row("Successful", f"{stats['successful']}")
        
        if stats["failed"] > 0:
            stats_table.add_row("Failed", f"[red]{stats['failed']}[/red]")
        else:
            stats_table.add_row("Failed", "0")
            
        stats_table.add_row("Total tokens", f"{stats['total_tokens']:,}")
        stats_table.add_row("Total processing time", f"{stats['total_time']:.2f} seconds")
        
        if stats["youtube_videos"] > 0:
            stats_table.add_row("YouTube videos processed", f"{stats['youtube_videos']}")
            
        if stats["total_images"] > 0:
            stats_table.add_row("Images processed", f"{stats['total_images']}")
            
        console.print(stats_table)
        
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        console.print("\n[yellow]Keyboard interrupt detected. Exiting...[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()