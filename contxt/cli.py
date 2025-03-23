import click
import sys
import os
from pathlib import Path
import logging
import time
import questionary
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from .scraper import Scraper
from .formatter import Formatter
from .config import load_config, save_config, update_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create console for rich output
console = Console()

# Global state for interactive mode
interactive_config = {}

# Custom styles for questionary
custom_style = questionary.Style([
    ('qmark', 'fg:cyan bold'),        # Question mark
    ('question', 'fg:white bold'),    # Question text
    ('answer', 'fg:green bold'),      # Answer text
    ('pointer', 'fg:cyan bold'),      # Selection pointer
    ('highlighted', 'fg:cyan bold'),  # Highlighted option
    ('selected', 'fg:green bold'),    # Selected option
])


def process_url(url, config):
    """Process a single URL and return the formatted content."""
    try:
        # Log the start of processing
        console.print(f"Processing: {url}")
        
        # Initialize scraper with configured mode
        scraper = Scraper(mode=config["scraping"]["mode"])
        
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
        
        # Format the scraped data
        formatter = Formatter(
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
        
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        console.print(f"[red]Error processing {url}: {e}[/red]")
        return None


def interactive_prompt(config, is_config_mode=False):
    """Run interactive prompt to collect configuration options."""
    global interactive_config
    interactive_config = {
        "output": config["output"].copy(),
        "scraping": config["scraping"].copy(),
        "organization": config["organization"].copy(),
    }
    
    # Header
    header_text = Text("Welcome to contxt", style="cyan bold")
    header_text.append("\nThe Web Content Collector for LLM Context", style="green")
    console.print(Panel(header_text, border_style="cyan"))
    
    # Ask for URLs (only if not in config mode)
    urls = []
    custom_dir = None
    
    if not is_config_mode:
        urls_input = questionary.text(
            "Enter one or more URLs (space-separated):",
            style=custom_style
        ).ask()
        
        urls = urls_input.split() if urls_input else []
    
    # Scraping mode
    console.print("\n[cyan bold]Scraping Mode[/cyan bold]")
    mode_descriptions = {
        "basic": "Basic (HTML only, fastest)",
        "advanced": "Advanced (JavaScript support, slower)",
        "super": "Super (Extended wait for complex sites, slowest)"
    }
    mode_choices = [
        questionary.Choice(title=mode_descriptions[mode], value=mode) 
        for mode in ["basic", "advanced", "super"]
    ]
    
    mode_choice = questionary.select(
        "Select scraping mode:",
        choices=mode_choices,
        default=config["scraping"]["mode"],
        style=custom_style
    ).ask()
    
    interactive_config["scraping"]["mode"] = mode_choice
    
    # Include images
    include_images = questionary.confirm(
        "Include images?",
        default=config["scraping"]["include_images"],
        style=custom_style
    ).ask()
    
    interactive_config["scraping"]["include_images"] = include_images
    
    # Output format
    console.print("\n[cyan bold]Output Format[/cyan bold]")
    format_descriptions = {
        "markdown": "Markdown (clean, readable)",
        "xml": "XML (structured, machine-readable)",
        "raw": "Raw HTML (cleaned, without boilerplate)"
    }
    format_choices = [
        questionary.Choice(title=format_descriptions[fmt], value=fmt) 
        for fmt in ["markdown", "xml", "raw"]
    ]
    
    format_choice = questionary.select(
        "Select output format:",
        choices=format_choices,
        default=config["output"]["format"],
        style=custom_style
    ).ask()
    
    interactive_config["output"]["format"] = format_choice
    
    # Output destination
    console.print("\n[cyan bold]Output Destination[/cyan bold]")
    destination_descriptions = {
        "print": "Print to console",
        "file": "Save to file",
        "clipboard": "Copy to clipboard"
    }
    destination_choices = [
        questionary.Choice(title=destination_descriptions[dest], value=dest) 
        for dest in ["print", "file", "clipboard"]
    ]
    
    destination_choice = questionary.select(
        "Select output destination:",
        choices=destination_choices,
        default=config["output"]["destination"],
        style=custom_style
    ).ask()
    
    interactive_config["output"]["destination"] = destination_choice
    
    # Custom directory for file output
    if destination_choice == "file":
        default_dir = config["output"].get("directory", os.getcwd())
        
        custom_dir = questionary.text(
            "Enter output directory path:",
            default=default_dir,
            style=custom_style
        ).ask()
        
        custom_dir = os.path.expanduser(custom_dir)
        interactive_config["output"]["directory"] = custom_dir
        
        # Custom naming for files
        custom_name = questionary.text(
            "Enter custom name prefix for output files (empty for default):",
            default="",
            style=custom_style
        ).ask()
        
        if custom_name:
            interactive_config["output"]["custom_name"] = custom_name
    
    # Organization (only if multiple URLs and not in config mode)
    if not is_config_mode and len(urls) > 1:
        single_file = questionary.confirm(
            "Combine all URLs into a single file?",
            default=config["organization"]["single_file"],
            style=custom_style
        ).ask()
        
        interactive_config["organization"]["single_file"] = single_file
    
    # Save configuration if in config mode
    if is_config_mode:
        save_config(interactive_config)
        console.print("\n[green bold]Configuration has been updated![/green bold]")
        console.print("These settings will be used as defaults for future runs.")
        
    return urls, custom_dir


def configuration_prompt():
    """Dedicated configuration prompt."""
    config = load_config()
    
    console.print("[cyan bold]Configure Default Settings[/cyan bold]")
    
    # Run through the interactive prompt in config mode
    interactive_prompt(config, is_config_mode=True)


@click.command()
@click.argument("urls", nargs=-1, required=False)
# Scraping options
@click.option("-m", "--mode", type=click.Choice(["basic", "advanced", "super"]), help="Scraping mode")
@click.option("-i", "--include-images", is_flag=True, help="Include image references")

# Output options
@click.option("-f", "--format", type=click.Choice(["markdown", "xml", "raw"]), help="Output format")
@click.option("-o", "--output", type=click.Choice(["print", "file", "clipboard"]), help="Output destination")
@click.option("-d", "--directory", type=click.Path(exists=True, file_okay=False), help="Output directory (when saving to file)")
@click.option("-s", "--single-file", is_flag=True, help="Combine all URLs into a single file")
@click.option("--custom-name", help="Custom prefix for output files")

# General options
@click.option("-c", "--config", is_flag=True, help="Configure default settings")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--version", is_flag=True, help="Show version information")
def main(urls, mode, format, include_images, 
         output, directory, single_file, custom_name, 
         config, verbose, version):
    """
    Web Content Collector for LLM Context.
    
    If URLS are provided, processes them directly with the specified options.
    If no URLS are provided, runs in interactive mode.
    """
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
        # Interactive mode
        urls, directory = interactive_prompt(user_config)
        
        # Use interactive config
        user_config = interactive_config
    
    if not urls:
        urls = ["https://www.ableton.com/en/live/all-new-features/"]
        console.print("[yellow]No URLs provided. Set to example page.[/yellow]")
        # console.print("[yellow]No URLs provided. Exiting.[/yellow]")
        # sys.exit(1)
    
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
        "total_images": 0
    }
    
    for url in urls:
        result = process_url(url, user_config)
        
        if result:
            formatted_content, source_url, formatter, scraped_data = result
            all_content.append((formatted_content, source_url, formatter, scraped_data))
            
            # Update stats
            stats["successful"] += 1
            stats["total_tokens"] += scraped_data.get("token_count", 0)
            stats["total_time"] += scraped_data.get("processing_time", 0)
            stats["total_images"] += len(scraped_data.get("images", []))
            
            # Print immediately if not combining and destination is print
            if not user_config["organization"]["single_file"] and user_config["output"]["destination"] == "print":
                console.print("\n" + "=" * 40 + "\n")
                console.print(f"[cyan bold]Content from {source_url}:[/cyan bold]")
                console.print("\n" + "=" * 40 + "\n")
                console.print(formatted_content)
        else:
            # Count as failed
            stats["failed"] += 1
    
    # Handle output based on configuration
    if not all_content:
        console.print("[red]No content was successfully processed.[/red]")
        return
    
    if user_config["organization"]["single_file"]:
        # Combine all content into a single output
        combined = "\n\n" + "=" * 50 + "\n\n".join([content for content, _, _, _ in all_content])
        
        if user_config["output"]["destination"] == "print":
            console.print(combined)
        elif user_config["output"]["destination"] == "file":
            # Save to file
            output_dir = user_config["output"].get("directory") or None
            
            # Generate file name with custom prefix if provided
            if user_config["output"].get("custom_name"):
                custom_prefix = user_config["output"]["custom_name"]
                file_name = f"{custom_prefix}_combined"
            else:
                file_name = "combined_" + "_".join([url.split("//")[-1].split("/")[0] for url in urls[:3]])
            
            file_path = all_content[0][2].save_to_file(
                combined,
                file_name,
                output_dir
            )
            console.print(f"[green bold]Combined content saved to:[/green bold] {file_path}")
        elif user_config["output"]["destination"] == "clipboard":
            # Copy to clipboard
            success = all_content[0][2].copy_to_clipboard(combined)
            if success:
                console.print("[green bold]Combined content copied to clipboard.[/green bold]")
            else:
                console.print("[red]Failed to copy content to clipboard.[/red]")
    else:
        # Handle individual files
        if user_config["output"]["destination"] == "file":
            output_dir = user_config["output"].get("directory") or None
            for content, url, formatter, _ in all_content:
                # Use custom name prefix if provided
                if user_config["output"].get("custom_name"):
                    custom_prefix = user_config["output"]["custom_name"]
                    domain = urlparse(url).netloc
                    file_name = f"{custom_prefix}_{domain}"
                    file_path = formatter.save_to_file(content, file_name, output_dir)
                else:
                    file_path = formatter.save_to_file(content, url, output_dir)
                console.print(f"[green bold]Content from {url} saved to:[/green bold] {file_path}")
        elif user_config["output"]["destination"] == "clipboard" and len(all_content) == 1:
            # Copy to clipboard (only for single URL when not combining)
            success = all_content[0][2].copy_to_clipboard(all_content[0][0])
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
    
    if stats["total_images"] > 0:
        stats_table.add_row("Images processed", f"{stats['total_images']}")
        
    console.print(stats_table)


if __name__ == "__main__":
    main()