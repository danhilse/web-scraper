import os
import sys
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .config import load_config, save_config

# Create console for rich output
console = Console()

# Flag to track if we're exiting due to keyboard interrupt
is_exiting = False

def set_is_exiting(value):
    """Set the is_exiting flag from external modules"""
    global is_exiting
    is_exiting = value

# Custom styles for questionary
custom_style = questionary.Style([
    ('qmark', 'fg:cyan bold'),        # Question mark
    ('question', 'fg:white bold'),    # Question text
    ('answer', 'fg:green bold'),      # Answer text
    ('pointer', 'fg:cyan bold'),      # Selection pointer
    ('highlighted', 'fg:cyan bold'),  # Highlighted option
    ('selected', 'fg:green bold'),    # Selected option
])


def interactive_prompt(config, is_config_mode=False):
    """Run interactive prompt to collect configuration options.
    
    Args:
        config: The current configuration
        is_config_mode: Whether running in configuration mode
        
    Returns:
        tuple: (urls, custom_dir, interactive_config)
    """
    global is_exiting
    
    interactive_config = {
        "output": config["output"].copy(),
        "scraping": config["scraping"].copy(),
        "organization": config["organization"].copy(),
        "youtube": config.get("youtube", {}).copy() if "youtube" in config else {
            "include_comments": False,
            "max_videos": 30,
            "include_description": True
        }
    }
    
    # Header
    header_text = Text("Welcome to contxt", style="cyan bold")
    header_text.append("\nThe Web Content Collector for LLM Context", style="green")
    console.print(Panel(header_text, border_style="cyan"))
    
    # Ask for URLs (only if not in config mode)
    urls = []
    custom_dir = None
    
    try:
        if is_exiting:
            return [], None, interactive_config
            
        if not is_config_mode:
            urls_input = questionary.text(
                "Enter one or more URLs (space-separated):",
                style=custom_style
            ).ask()
            
            if is_exiting:
                return [], None, interactive_config
                
            urls = urls_input.split() if urls_input else []
            
            # Early URL type detection to customize the flow
            all_youtube = all('youtube.com' in url or 'youtu.be' in url for url in urls) if urls else False
            has_playlist = any('playlist' in url or 'list=' in url for url in urls) if urls else False
            has_channel = any(('/channel/' in url or '/c/' in url or '/@' in url) and 'youtube.com' in url for url in urls) if urls else False
            
            if all_youtube and urls:
                console.print("\n[cyan bold]YouTube Options[/cyan bold]")
                
                include_comments = questionary.confirm(
                    "Include YouTube comments?",
                    default=interactive_config["youtube"].get("include_comments", False),
                    style=custom_style
                ).ask()
                interactive_config["youtube"]["include_comments"] = include_comments
                
                if has_playlist or has_channel:
                    max_videos_str = questionary.text(
                        "Maximum videos to process from playlists/channels:",
                        default=str(interactive_config["youtube"].get("max_videos", 30)),
                        style=custom_style
                    ).ask()
                    try:
                        max_videos = int(max_videos_str)
                        if max_videos <= 0:
                            max_videos = 30
                            console.print("[yellow]Invalid value, using default of 30[/yellow]")
                    except ValueError:
                        max_videos = 30
                        console.print("[yellow]Invalid value, using default of 30[/yellow]")
                    
                    interactive_config["youtube"]["max_videos"] = max_videos
                
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
                
                if len(urls) > 1:
                    single_file = questionary.confirm(
                        "Combine all videos into a single file?",
                        default=config["organization"]["single_file"],
                        style=custom_style
                    ).ask()
                    interactive_config["organization"]["single_file"] = single_file
                
                interactive_config["output"]["format"] = "markdown"
                return urls, custom_dir, interactive_config
        
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
        console.print("\n[yellow]Keyboard interrupt detected in interactive prompt. Exiting...[/yellow]")
        is_exiting = True
        return [], None, interactive_config
            
    return urls, custom_dir, interactive_config

def youtube_options_prompt(config):
    """Prompt for YouTube-specific options."""
    youtube_config = config["youtube"]
    
    # Only show this if a YouTube URL is detected
    include_comments = questionary.confirm(
        "Include YouTube comments?",
        default=youtube_config.get("include_comments", False),
        style=custom_style
    ).ask()
    
    max_videos = questionary.text(
        "Maximum videos to process from playlists/channels:",
        default=str(youtube_config.get("max_videos", 30)),
        style=custom_style
    ).ask()
    
    try:
        max_videos = int(max_videos)
    except ValueError:
        max_videos = 30
        console.print("[yellow]Invalid number, using default of 30[/yellow]")
    
    return {
        "include_comments": include_comments,
        "max_videos": max_videos
    }


def manage_saved_directories(config):
    """Allow user to add, edit, or remove saved directories.
    
    Args:
        config: The current configuration
        
    Returns:
        bool: True if configuration was modified, False otherwise
    """
    global is_exiting
    
    if is_exiting:
        return False
        
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
    """Dedicated configuration prompt for managing global settings."""
    global is_exiting
    
    config = load_config()
    
    console.print("[cyan bold]Configure Default Settings[/cyan bold]")
    
    # Main configuration options
    config_options = [
        questionary.Choice(title="General settings", value="general"),
        questionary.Choice(title="Manage saved directories", value="directories"),
        questionary.Choice(title="Exit", value="exit")
    ]
    
    while not is_exiting:
        try:
            choice = questionary.select(
                "Select configuration option:",
                choices=config_options,
                style=custom_style
            ).ask()
            
            if is_exiting or choice is None:
                break
                
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
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Keyboard interrupt detected. Exiting configuration...[/yellow]")
            is_exiting = True
            break