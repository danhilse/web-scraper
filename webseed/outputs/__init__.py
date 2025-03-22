"""Output handlers for WebSeed."""

from webseed.outputs.base import BaseOutput, OutputFormat
from webseed.outputs.markdown import MarkdownOutput
from webseed.outputs.tagged import TaggedOutput
from webseed.outputs.youtube import YouTubeOutput

__all__ = ['BaseOutput', 'OutputFormat', 'MarkdownOutput', 'TaggedOutput', 'YouTubeOutput']