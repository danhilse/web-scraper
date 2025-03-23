import logging
from .base_formatter import BaseFormatter

logger = logging.getLogger(__name__)

class YouTubeFormatter(BaseFormatter):
    """Formatter for YouTube content with specialized markdown output."""
    
    def format(self, scraped_data):
        """Format YouTube scraped data as markdown."""
        if not scraped_data.get("youtube_data"):
            return f"# Error: Not YouTube Content\n\nThe provided content is not from YouTube."
        
        # Extract YouTube-specific data
        youtube_data = scraped_data.get("youtube_data", {})
        content_type = youtube_data.get("type", "unknown")
        
        if content_type == "video":
            return self._format_video(youtube_data, scraped_data["url"])
        elif content_type == "playlist":
            return self._format_playlist(youtube_data, scraped_data["url"])
        elif content_type == "channel":
            return self._format_channel(youtube_data, scraped_data["url"])
        else:
            return f"# Error: Unknown YouTube Content Type\n\nCould not identify the YouTube content type."
    
    def _format_video(self, youtube_data, url):
        """Format a single YouTube video as markdown."""
        video_info = youtube_data.get("video_info", {})
        transcript = youtube_data.get("transcript", "No transcript available")
        
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
        
    def _format_playlist(self, youtube_data, url):
        """Format a YouTube playlist as markdown."""
        videos = youtube_data.get("videos", [])
        
        if not videos:
            return f"# YouTube Playlist\n\nURL: [{url}]({url})\n\n*No videos found in this playlist.*"
        
        # Build markdown output
        output = []
        
        # Title and metadata
        output.append(f"# YouTube Playlist")
        output.append(f"URL: [{url}]({url})")
        output.append(f"Videos: {len(videos)}")
        output.append("")
        
        # List of videos with links
        output.append("## Videos in this Playlist")
        for i, video in enumerate(videos):
            output.append(f"{i+1}. [{video.get('title', 'Unknown')}]({video.get('url', '#')})")
        
        output.append("")
        
        # Process each video
        for i, video in enumerate(videos):
            output.append(f"## {i+1}. {video.get('title', 'Unknown Video')}")
            output.append(f"Channel: **{video.get('channel', 'Unknown')}**")
            output.append(f"URL: [{video.get('url', '#')}]({video.get('url', '#')})")
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
            
            # Add separator between videos
            if i < len(videos) - 1:
                output.append("---")
                output.append("")
        
        return "\n".join(output)
    
    def _format_channel(self, youtube_data, url):
        """Format YouTube channel videos as markdown."""
        videos = youtube_data.get("videos", [])
        
        if not videos:
            return f"# YouTube Channel\n\nURL: [{url}]({url})\n\n*No videos found from this channel.*"
        
        # Get channel name from first video
        channel_name = videos[0].get('channel', 'Unknown Channel') if videos else 'Unknown Channel'
        
        # Title and metadata
        output = []
        output.append(f"# YouTube Channel: {channel_name}")
        output.append(f"URL: [{url}]({url})")
        output.append(f"Videos: {len(videos)}")
        output.append("")
        
        # List of videos with links
        output.append("## Recent Videos")
        for i, video in enumerate(videos):
            output.append(f"{i+1}. [{video.get('title', 'Unknown')}]({video.get('url', '#')})")
        
        output.append("")
        
        # Process each video (similar to playlist)
        for i, video in enumerate(videos):
            output.append(f"## {i+1}. {video.get('title', 'Unknown Video')}")
            output.append(f"Channel: **{video.get('channel', 'Unknown')}**")
            output.append(f"URL: [{video.get('url', '#')}]({video.get('url', '#')})")
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
            
            # Add separator between videos
            if i < len(videos) - 1:
                output.append("---")
                output.append("")
        
        return "\n".join(output)
    
    def get_extension(self):
        """Get the file extension for YouTube content."""
        return "md"