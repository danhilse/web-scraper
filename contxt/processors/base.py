from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProcessor(ABC):
    """Base class for all content processors."""
    
    @abstractmethod
    def process(self, content: Any) -> Any:
        """
        Process the input content.
        
        Args:
            content: Input content to process
            
        Returns:
            Processed content
        """
        pass


class ProcessorPipeline:
    """Pipeline for chaining multiple processors together."""
    
    def __init__(self, processors: Optional[List[BaseProcessor]] = None):
        """
        Initialize the processor pipeline.
        
        Args:
            processors: List of processors to chain together
        """
        self.processors = processors or []
    
    def add_processor(self, processor: BaseProcessor) -> 'ProcessorPipeline':
        """
        Add a processor to the pipeline.
        
        Args:
            processor: Processor to add
            
        Returns:
            Self for method chaining
        """
        self.processors.append(processor)
        return self
    
    def process(self, content: Any) -> Any:
        """
        Process content through the entire pipeline.
        
        Args:
            content: Input content to process
            
        Returns:
            Processed content after passing through all processors
        """
        result = content
        for processor in self.processors:
            result = processor.process(result)
        return result