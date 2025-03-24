import logging
from .base_formatter import BaseFormatter

logger = logging.getLogger(__name__)

class YouTubeFormatter(BaseFormatter):
    """Formatter for YouTube content with specialized output formats."""
    
    def __init__(self, format_style="complete", **kwargs):
        """
        Initialize the YouTube formatter.
        
        Args:
            format_style (str): The style of formatting to use:
                - "raw": Basic transcript without timecodes and minimal metadata (.txt format)
                - "complete": Full metadata and transcript (default, .md format)
                - "chapters": Transcript organized by chapters if available (.md format)
            **kwargs: Additional kwargs passed to BaseFormatter
        """
        super().__init__(**kwargs)
        self.format_style = format_style
    
    def format(self, scraped_data):
        """Format YouTube scraped data based on the selected format style."""
        if not scraped_data.get("youtube_data"):
            return f"# Error: Not YouTube Content\n\nThe provided content is not from YouTube."
        
        # Extract YouTube-specific data
        youtube_data = scraped_data.get("youtube_data", {})
        content_type = youtube_data.get("type", "unknown")
        
        # Select format function based on style
        if self.format_style == "raw":
            format_func = self._format_raw
        elif self.format_style == "chapters":
            format_func = self._format_chapters
        else:  # Default to complete
            format_func = self._format_complete
        
        # Process based on content type
        if content_type == "video":
            return format_func(youtube_data, scraped_data["url"])
        elif content_type == "playlist":
            return self._format_playlist(youtube_data, scraped_data["url"], format_func)
        elif content_type == "channel":
            return self._format_channel(youtube_data, scraped_data["url"], format_func)
        else:
            return f"# Error: Unknown YouTube Content Type\n\nCould not identify the YouTube content type."
    
    def _format_raw(self, video_data, url):
        """Format a single video in raw format (txt)."""
        # For standalone videos
        if "video_info" in video_data:
            video_info = video_data.get("video_info", {})
            
            # Prioritize transcript_no_times if available, otherwise strip timestamps
            if video_data.get("transcript_no_times"):
                transcript = video_data.get("transcript_no_times")
            else:
                transcript = video_data.get("transcript", "No transcript available")
                # Strip timestamps if they exist
                if "[" in transcript and "]" in transcript:
                    transcript_lines = []
                    for line in transcript.split("\n"):
                        if "[" in line and "]" in line:
                            # Find the closing bracket and take everything after it
                            closing_bracket_index = line.find("]")
                            if closing_bracket_index != -1 and closing_bracket_index + 1 < len(line):
                                transcript_lines.append(line[closing_bracket_index + 1:].lstrip())
                            else:
                                transcript_lines.append(line)
                    transcript = "\n".join(transcript_lines)
            
            # Build raw output
            output = []
            
            # Title and minimal metadata
            output.append(f"Title: {video_info.get('title', 'Unknown Video')}")
            output.append(f"Channel: {video_info.get('channel', 'Unknown')}")
            output.append(f"URL: {url}")
            output.append("")
            
            # Transcript without formatting
            output.append("Transcript:")
            output.append(transcript if transcript and transcript != "No transcript available" else "No transcript available for this video.")
            
            return "\n".join(output)
        
        # For videos from playlists or channels
        else:
            return self._format_video_raw(video_data, video_data.get("url", url))
    
    def _format_video_raw(self, video, url):
        """Format an individual video from a playlist/channel in raw format."""
        output = []
        
        # Title and minimal metadata
        output.append(f"Title: {video.get('title', 'Unknown Video')}")
        output.append(f"Channel: {video.get('channel', 'Unknown')}")
        output.append(f"URL: {url}")
        output.append("")
        
        # Prioritize transcript_no_times if available
        if "transcript_no_times" in video and video["transcript_no_times"]:
            transcript = video["transcript_no_times"]
        else:
            # Otherwise, use transcript with timestamps and strip them
            transcript = video.get('transcript', '')
            if transcript:
                transcript_lines = []
                for line in transcript.split("\n"):
                    if line.startswith("[") and "]" in line:
                        # Strip timestamp
                        transcript_lines.append(line.split("] ", 1)[1] if "] " in line else line)
                    else:
                        transcript_lines.append(line)
                transcript = "\n".join(transcript_lines)
        
        if transcript:
            output.append("Transcript:")
            output.append(transcript)
        else:
            output.append("No transcript available for this video.")
        
        return "\n".join(output)
    
    def _format_complete(self, video_data, url):
        """Format a single video in complete format (md)."""
        # For standalone videos
        if "video_info" in video_data:
            video_info = video_data.get("video_info", {})
            transcript = video_data.get("transcript", "No transcript available")
            
            # Build markdown output
            output = []
            
            # Title and metadata
            output.append(f"# {video_info.get('title', 'Unknown Video')}")
            output.append(f"Channel: **{video_info.get('channel', 'Unknown')}**")
            output.append(f"URL: [{url}]({url})")
            output.append("")
            
            # Description
            if video_info.get('description'):
                output.append("## Description")
                output.append(video_info['description'])
                output.append("")
            
            # Transcript with timestamp formatting
            output.append("## Transcript")
            if transcript and transcript != "No transcript available":
                # Preserve timestamp format if present
                output.append("```")
                output.append(transcript)
                output.append("```")
            else:
                output.append("*No transcript available for this video.*")
            
            output.append("")
            
            # Comments if available
            if 'comments' in video_info and video_info['comments']:
                output.append("## Top Comments")
                
                for comment in video_info['comments'][:10]:  # Limit to top 10 comments
                    output.append(f"**{comment.get('author', 'Anonymous')}**: {comment.get('text', '')}")
                    output.append("")
            
            return "\n".join(output)
        
        # For videos from playlists or channels
        else:
            return self._format_video_complete(video_data, video_data.get("url", url))
    
    def _format_video_complete(self, video, url):
        """Format an individual video from a playlist/channel in complete format."""
        output = []
        
        # Title and metadata
        output.append(f"## {video.get('title', 'Unknown Video')}")
        output.append(f"Channel: **{video.get('channel', 'Unknown')}**")
        output.append(f"URL: [{url}]({url})")
        output.append("")
        
        # Description (if available)
        if video.get('description'):
            output.append("### Description")
            output.append(video['description'])
            output.append("")
        
        # Transcript with timestamp formatting
        output.append("### Transcript")
        transcript = video.get('transcript', '')
        if transcript:
            output.append("```")
            output.append(transcript)
            output.append("```")
        else:
            output.append("*No transcript available for this video.*")
        
        output.append("")
        
        # Comments if available
        if 'comments' in video and video['comments']:
            output.append("### Top Comments")
            
            for comment in video['comments'][:5]:  # Limit to top 5 comments per video
                output.append(f"**{comment.get('author', 'Anonymous')}**: {comment.get('text', '')}")
                output.append("")
        
        return "\n".join(output)
    
    def _format_chapters(self, video_data, url):
        """Format a single video with chapters (md)."""
        # Only works for standalone videos
        if "video_info" in video_data:
            video_info = video_data.get("video_info", {})
            transcript = video_data.get("transcript", "No transcript available")
            chapters = video_data.get("chapters", [])
            
            # Build markdown output
            output = []
            
            # Title and metadata
            output.append(f"# {video_info.get('title', 'Unknown Video')}")
            output.append(f"Channel: **{video_info.get('channel', 'Unknown')}**")
            output.append(f"URL: [{url}]({url})")
            output.append("")
            
            # Description
            if video_info.get('description'):
                output.append("## Description")
                output.append(video_info['description'])
                output.append("")
            
            # Chapter-organized transcript
            output.append("# Transcript")
            
            if chapters and transcript and transcript != "No transcript available":
                # Organize transcript by chapters
                if video_data.get("transcript_by_chapters"):
                    output.append(video_data.get("transcript_by_chapters"))
                else:
                    # Fallback if transcript wasn't pre-organized by chapters
                    from .youtube_handler import organize_transcript_by_chapters
                    chapter_transcript = organize_transcript_by_chapters(transcript, chapters)
                    output.append(chapter_transcript)
            elif transcript and transcript != "No transcript available":
                # No chapters available, use regular transcript without timestamps
                transcript_lines = []
                for line in transcript.split("\n"):
                    if line.startswith("[") and "]" in line:
                        # Strip timestamp
                        transcript_lines.append(line.split("] ", 1)[1] if "] " in line else line)
                    else:
                        transcript_lines.append(line)
                
                output.append("## Full Transcript")
                output.append("\n".join(transcript_lines))
            else:
                output.append("*No transcript available for this video.*")
            
            output.append("")
            
            return "\n".join(output)
        
        # For videos in playlists or channels, use complete format (chapters format doesn't apply)
        else:
            logger.warning("Chapter format only available for individual videos. Using complete format.")
            return self._format_video_complete(video_data, video_data.get("url", url))
    
    def _format_playlist(self, playlist_data, url, format_func):
        """Format a YouTube playlist using the specified format function."""
        videos = playlist_data.get("videos", [])
        
        if not videos:
            return f"# YouTube Playlist\n\nURL: [{url}]({url})\n\n*No videos found in this playlist.*" \
                if self.format_style != "raw" else f"YouTube Playlist\nURL: {url}\n\nNo videos found in this playlist."
        
        # Build output
        output = []
        
        # Title and metadata
        if self.format_style == "raw":
            output.append(f"YouTube Playlist")
            output.append(f"URL: {url}")
            output.append(f"Videos: {len(videos)}")
        else:
            output.append(f"# YouTube Playlist")
            output.append(f"URL: [{url}]({url})")
            output.append(f"Videos: {len(videos)}")
        
        output.append("")
        
        # If markdown format, add list of videos with links
        if self.format_style != "raw":
            output.append("## Videos in this Playlist")
            for i, video in enumerate(videos):
                output.append(f"{i+1}. [{video.get('title', 'Unknown')}]({video.get('url', '#')})")
            output.append("")
        
        # Process each video with the specified format function
        for i, video in enumerate(videos):
            # Append index number for playlist context
            if self.format_style == "raw":
                output.append(f"Video {i+1}:")
            
            # Format this individual video
            video_format = format_func(video, video.get('url', '#'))
            output.append(video_format)
            
            # Add separator between videos
            if i < len(videos) - 1:
                if self.format_style == "raw":
                    output.append("-" * 40)
                else:
                    output.append("---")
                output.append("")
        
        return "\n".join(output)
    
    def _format_channel(self, channel_data, url, format_func):
        """Format a YouTube channel using the specified format function."""
        videos = channel_data.get("videos", [])
        
        if not videos:
            return f"# YouTube Channel\n\nURL: [{url}]({url})\n\n*No videos found from this channel.*" \
                if self.format_style != "raw" else f"YouTube Channel\nURL: {url}\n\nNo videos found from this channel."
        
        # Get channel name from first video
        channel_name = videos[0].get('channel', 'Unknown Channel') if videos else 'Unknown Channel'
        
        # Build output
        output = []
        
        # Title and metadata
        if self.format_style == "raw":
            output.append(f"YouTube Channel: {channel_name}")
            output.append(f"URL: {url}")
            output.append(f"Videos: {len(videos)}")
        else:
            output.append(f"# YouTube Channel: {channel_name}")
            output.append(f"URL: [{url}]({url})")
            output.append(f"Videos: {len(videos)}")
        
        output.append("")
        
        # If markdown format, add list of videos with links
        if self.format_style != "raw":
            output.append("## Recent Videos")
            for i, video in enumerate(videos):
                output.append(f"{i+1}. [{video.get('title', 'Unknown')}]({video.get('url', '#')})")
            output.append("")
        
        # Process each video with the specified format function
        for i, video in enumerate(videos):
            # Append index number for channel context
            if self.format_style == "raw":
                output.append(f"Video {i+1}:")
            
            # Format this individual video
            video_format = format_func(video, video.get('url', '#'))
            output.append(video_format)
            
            # Add separator between videos
            if i < len(videos) - 1:
                if self.format_style == "raw":
                    output.append("-" * 40)
                else:
                    output.append("---")
                output.append("")
        
        return "\n".join(output)
    
    def get_extension(self):
        """Get the file extension for YouTube content based on format style."""
        if self.format_style == "raw":
            return "txt"
        else:
            return "md"