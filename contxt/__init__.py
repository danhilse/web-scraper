"""
LLM Context Scraper: A modular tool for scraping and processing web content for LLM context.
"""

from llm_context_scraper.core.processor import ContextProcessor

class ContextScraper:
    """Main entry point for the LLM Context Scraper."""
    
    def __init__(self, config=None):
        """Initialize the scraper with optional configuration."""
        self.config = config
        
    def scrape(self, source, output_format='markdown'):
        """
        Scrape content from the specified source.
        
        Args:
            source: URL or identifier for the source to scrape
            output_format: Format to output the content in
            
        Returns:
            Processed content in the specified format
        """
        # This will be implemented with actual functionality
        pass

__version__ = '0.1.0'
