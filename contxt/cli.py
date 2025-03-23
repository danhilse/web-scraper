import click
import sys
import os
import signal
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
from .formatters import get_formatter
from .config import load_config, save_config, update_config
from .outputs import get_output_handler

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

# Flag to track if we're exiting due to keyboard interrupt
is_exiting = False

# Custom styles for questionary
custom_style = questionary.Style([
    ('qmark', 'fg:cyan bold'),        # Question mark
    ('question', 'fg:white bold'),    # Question text
    ('answer', 'fg:green bold'),      # Answer text
    ('pointer', 'fg:cyan bold'),      # Selection pointer
    ('highlighted', 'fg:cyan bold'),  # Highlighted option
    ('selected', 'fg:green bold'),    # Selected option
])


def signal_handler(sig, frame):
    """Handle keyboard interrupt gracefully"""
    global is_exiting
    is_exiting = True
    console.print("\n[yellow]Keyboard interrupt detected. Exiting gracefully...[/yellow]")
    sys.exit(0)


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
        
        # Get the appropriate formatter for the output format
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
    
    try:
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
            # Prepare directory options
            dir_options = []
            
            # Option 1: Working directory (default)
            working_dir = os.getcwd()
            dir_options.append(questionary.Choice(
                title=f"Working directory ({working_dir})", 
                value={"type": "working", "path": working_dir}
            ))
            
            # Option 2: Saved directories from config
            saved_dirs = config["output"].get("saved_directories", [])
            for saved_dir in saved_dirs:
                expanded_path = os.path.expanduser(saved_dir["path"])
                dir_options.append(questionary.Choice(
                    title=f"{saved_dir['name']} ({expanded_path})", 
                    value={"type": "saved", "path": expanded_path, "name": saved_dir["name"]}
                ))
            
            # Option 3: Custom path
            dir_options.append(questionary.Choice(
                title="Custom path...", 
                value={"type": "custom", "path": None}
            ))
            
            # Ask user to select directory option
            dir_choice = questionary.select(
                "Select output directory:",
                choices=dir_options,
                style=custom_style
            ).ask()
            
            # Handle custom path option
            if dir_choice["type"] == "custom":
                # Default to current directory or previously selected directory
                default_dir = config["output"].get("directory") or working_dir
                
                custom_path = questionary.text(
                    "Enter output directory path:",
                    default=default_dir,
                    style=custom_style
                ).ask()
                
                custom_path = os.path.expanduser(custom_path)
                dir_choice["path"] = custom_path
                
                # Ask if user wants to save this directory for future use
                save_dir = questionary.confirm(
                    "Save this directory for future use?",
                    default=False,
                    style=custom_style
                ).ask()
                
                if save_dir:
                    dir_name = questionary.text(
                        "Enter a name for this directory:",
                        style=custom_style
                    ).ask()
                    
                    if dir_name:
                        # Add to saved directories
                        if "saved_directories" not in interactive_config["output"]:
                            interactive_config["output"]["saved_directories"] = []
                        
                        interactive_config["output"]["saved_directories"].append({
                            "name": dir_name,
                            "path": custom_path
                        })
            
            # Set the selected directory path (ensure it's a string not a dict)
            interactive_config["output"]["directory"] = dir_choice["path"]
            custom_dir = dir_choice["path"]  # Update the custom_dir variable to return
            
            # Custom naming for files
            custom_name = questionary.text(
                "Enter custom name prefix for output files (empty for default):",
                default=config["output"].get("custom_name", ""),
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
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Keyboard interrupt detected. Exiting...[/yellow]")
        sys.exit(0)
            
    return urls, custom_dir


def manage_saved_directories(config):
    """Allow user to add, edit, or remove saved directories."""
    saved_dirs = config["output"].get("saved_directories", [])
    
    console.print("\n[cyan bold]Manage Saved Directories[/cyan bold]")
    
    if not saved_dirs:
        console.print("[yellow]No saved directories found.[/yellow]")
    else:
        # List all saved directories
        console.print("\nSaved directories:")
        for i, dir_info in enumerate(saved_dirs, 1):
            console.print(f"{i}. {dir_info['name']} ({os.path.expanduser(dir_info['path'])})")
    
    # Options for directory management
    actions = [
        questionary.Choice(title="Add new directory", value="add"),
        questionary.Choice(title="Remove directory", value="remove", disabled=not saved_dirs),
        questionary.Choice(title="Back to main menu", value="back")
    ]
    
    action = questionary.select(
        "Select action:",
        choices=actions,
        style=custom_style
    ).ask()
    
    if action == "add":
        # Add new directory
        dir_path = questionary.text(
            "Enter directory path:",
            style=custom_style
        ).ask()
        
        dir_path = os.path.expanduser(dir_path)
        
        # Validate directory
        if not os.path.isdir(dir_path):
            create_dir = questionary.confirm(
                f"Directory {dir_path} does not exist. Create it?",
                style=custom_style
            ).ask()
            
            if create_dir:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    console.print(f"[red]Failed to create directory: {e}[/red]")
                    return False
            else:
                return False
        
        dir_name = questionary.text(
            "Enter a name for this directory:",
            style=custom_style
        ).ask()
        
        if dir_name:
            if "saved_directories" not in config["output"]:
                config["output"]["saved_directories"] = []
            
            config["output"]["saved_directories"].append({
                "name": dir_name,
                "path": dir_path
            })
            
            console.print(f"[green]Added directory: {dir_name} ({dir_path})[/green]")
            return True
    
    elif action == "remove":
        # Remove a directory
        if saved_dirs:
            dir_choices = [
                questionary.Choice(
                    title=f"{dir_info['name']} ({os.path.expanduser(dir_info['path'])})", 
                    value=i
                ) for i, dir_info in enumerate(saved_dirs)
            ]
            
            dir_choices.append(questionary.Choice(title="Cancel", value=None))
            
            dir_index = questionary.select(
                "Select directory to remove:",
                choices=dir_choices,
                style=custom_style
            ).ask()
            
            if dir_index is not None:
                removed = config["output"]["saved_directories"].pop(dir_index)
                console.print(f"[green]Removed directory: {removed['name']}[/green]")
                return True
    
    return False

def configuration_prompt():
    """Dedicated configuration prompt."""
    config = load_config()
    
    console.print("[cyan bold]Configure Default Settings[/cyan bold]")
    
    # Main configuration options
    config_options = [
        questionary.Choice(title="General settings", value="general"),
        questionary.Choice(title="Manage saved directories", value="directories"),
        questionary.Choice(title="Exit", value="exit")
    ]
    
    while True:
        choice = questionary.select(
            "Select configuration option:",
            choices=config_options,
            style=custom_style
        ).ask()
        
        if choice == "general":
            # Run through the interactive prompt in config mode
            interactive_prompt(config, is_config_mode=True)
            config = load_config()  # Reload config after changes
        elif choice == "directories":
            if manage_saved_directories(config):
                save_config(config)
                config = load_config()  # Reload config after changes
        elif choice == "exit":
            break


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
        
        # Determine the extension based on the selected format
        extension_map = {
            "markdown": ".md",
            "xml": ".xml", 
            "raw": ".html"
        }
        extension = extension_map.get(user_config["output"]["format"])
        
        # Create the output_handler here before it is used
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
        
        for url in urls:
            # Check if we're exiting
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
                
                # Print immediately if not combining and destination is print
                if not user_config["organization"]["single_file"] and user_config["output"]["destination"] == "print":
                    # Get output handler for printing to console
                    output_handler = get_output_handler("print", console=console)
                    output_handler.output(formatted_content, source=source_url)
            else:
                # Count as failed
                stats["failed"] += 1
                
            # Check if we're exiting after each URL
            if is_exiting:
                break
        
        # If exiting, don't continue with output
        if is_exiting:
            return
            
        # Handle output based on configuration
        if not all_content:
            console.print("[red]No content was successfully processed.[/red]")
            return
        
        # Get appropriate extension based on format
        extension_map = {
            "markdown": ".md",
            "xml": ".xml", 
            "raw": ".html"
        }
        extension = extension_map.get(user_config["output"]["format"])
        
        # Create output handler with appropriate configuration
        if user_config["output"]["destination"] == "print":
            output_handler = get_output_handler("print", console=console)
        elif user_config["output"]["destination"] == "clipboard":
            output_handler = get_output_handler("clipboard")
        else:
            # Default to console
            output_handler = get_output_handler("print", console=console)
        
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
            # Handle individual outputs (we've already handled the print case above for multiple files)
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
        
        if stats["total_images"] > 0:
            stats_table.add_row("Images processed", f"{stats['total_images']}")
            
        console.print(stats_table)
        
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        console.print("\n[yellow]Keyboard interrupt detected. Exiting...[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()