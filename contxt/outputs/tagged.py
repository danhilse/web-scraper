from typing import List, Optional
import os

from webseed.outputs.base import BaseOutput
from webseed.utils.logging import get_logger

logger = get_logger(__name__)


class TaggedOutput(BaseOutput):
    """Output handler for tagged text format."""
    
    def save(self, content: List[str]) -> None:
        """
        Save content in tagged text format.
        
        Args:
            content: List of content strings to save
        """
        filename = self.get_filename('txt')
        
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Add metadata header
                f.write("# WebSeed Scraping Results\n")
                f.write(f"# Date: {os.path.basename(filename).split('_')[1].split('.')[0]}\n")
                f.write(f"# URL Count: {len(content)}\n")
                f.write("#" + "-" * 50 + "\n\n")
                
                # Write content
                for item in content:
                    f.write(item)
                    f.write("\n\n" + "#" + "-" * 50 + "\n\n")
            
            logger.info(f"Saved tagged output to {filename}")
        except Exception as e:
            logger.error(f"Failed to save tagged output: {e}")