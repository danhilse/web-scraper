import logging
import os
import pyperclip
from pathlib import Path
from urllib.parse import urlparse
from .utils import sanitize_filename

logger = logging.getLogger(__name__)

class OutputHandler:
    """Base class for handling different output destinations."""
    
    def output(self, content, source=None, **kwargs):
        """
        Output formatted content.
        
        Args:
            content (str): The formatted content to output
            source (str, optional): URL or identifier for the content
            **kwargs: Additional output-specific parameters
            
        Returns:
            bool: Success status
        """
        raise NotImplementedError("Subclasses must implement output method")


class ConsoleOutputHandler(OutputHandler):
    """Handles output to console."""
    
    def __init__(self, console=None):
        """
        Initialize with optional console object.
        
        Args:
            console: Rich console object or None to use print
        """
        self.console = console
    
    def output(self, content, source=None, **kwargs):
        """Print content to console."""
        if self.console:
            if source:
                self.console.print(f"\nContent from {source}:\n")
            self.console.print(content)
        else:
            if source:
                print(f"\nContent from {source}:\n")
            print(content)
        return True

class FileOutputHandler(OutputHandler):
    """Handles output to file."""
    
    def __init__(self, directory=None, custom_name=None):
        """
        Initialize with output directory and custom name prefix.
        
        Args:
            directory (str, optional): Directory to save files
            custom_name (str, optional): Custom prefix for filenames
        """
        # Use provided directory, or fall back to current working directory
        self.directory = directory if directory is not None else os.getcwd()
        
        # Expand user directory (e.g., ~ to /home/user)
        self.directory = os.path.expanduser(self.directory)
        
        self.custom_name = custom_name
    
    def output(self, content, source=None, extension=None, title=None, **kwargs):
        """
        Save content to file.
        
        Args:
            content (str): Content to save
            source (str, optional): URL or identifier for filename
            extension (str, optional): File extension
            title (str, optional): Page title for filename
            **kwargs: Additional parameters
            
        Returns:
            str: Path to saved file or None if failed
        """
        try:
            # Ensure directory exists
            output_dir = Path(self.directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            if self.custom_name and source:
                if "://" in source:  # It's a URL
                    domain = urlparse(source).netloc
                    filename = f"{self.custom_name}_{domain}"
                else:
                    filename = f"{self.custom_name}_{source}"
            elif self.custom_name:
                filename = self.custom_name
            elif title:
                # Use the page title as the filename if available
                filename = title
            elif source:
                if "://" in source:  # It's a URL
                    parsed_url = urlparse(source)
                    domain = parsed_url.netloc
                    path = parsed_url.path.rstrip("/")
                    
                    if not path:
                        path = "index"
                    else:
                        path = path.replace("/", "_").lstrip("_")
                    
                    filename = f"{domain}_{path}"
                else:
                    filename = source
            else:
                filename = "contxt_output"
            
            # Sanitize filename
            filename = sanitize_filename(filename)
            
            # Add extension if provided
            if extension:
                if not extension.startswith('.'):
                    extension = f".{extension}"
                if not filename.endswith(extension):
                    filename += extension
            
            # Create full path and ensure uniqueness
            file_path = output_dir / filename
            counter = 1
            original_path = file_path
            while file_path.exists():
                file_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
                counter += 1
            
            # Write content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Saved content to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return None
        
class ClipboardOutputHandler(OutputHandler):
    """Handles output to clipboard."""
    
    def output(self, content, source=None, **kwargs):
        """
        Copy content to clipboard.
        
        Args:
            content (str): Content to copy
            source (str, optional): Not used, included for API consistency
            **kwargs: Additional parameters, not used
            
        Returns:
            bool: Success status
        """
        try:
            pyperclip.copy(content)
            logger.info("Copied content to clipboard")
            return True
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return False


def get_output_handler(destination, **kwargs):
    """
    Factory function to get the appropriate output handler.
    
    Args:
        destination (str): Output destination ('print', 'file', 'clipboard')
        **kwargs: Additional parameters for the specific handler
        
    Returns:
        OutputHandler: Appropriate handler instance
    """
    if destination == "print":
        # ConsoleOutputHandler uses console parameter
        return ConsoleOutputHandler(**kwargs)
    elif destination == "file":
        # FileOutputHandler only needs directory and custom_name
        handler_kwargs = {
            'directory': kwargs.get('directory'),
            'custom_name': kwargs.get('custom_name')
        }
        return FileOutputHandler(**handler_kwargs)
    elif destination == "clipboard":
        # ClipboardOutputHandler doesn't need any parameters
        return ClipboardOutputHandler()
    else:
        logger.warning(f"Unknown output destination: {destination}, using console")
        return ConsoleOutputHandler(**kwargs)