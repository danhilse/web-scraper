"""Main YouTube source processor for handling different types of YouTube URLs."""

import re
from typing import Dict, Any, List, Optional

from webseed.utils.logging import get_logger
from webseed.sources.youtube.video import extract_video_id, process_video
from webseed.sources.youtube.playlist import process_playlist
from webseed.sources.youtube.channel import process_channel

logger = get_logger(__name__)


def is_youtube_url(url: str) -> bool:
    """
    Check if the URL is a YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if it's a YouTube URL, False otherwise
    """
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/user/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    
    return False


def identify_youtube_url_type(url: str) -> str:
    """
    Identify the type of YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Type of URL: 'video', 'playlist', 'channel', or 'unknown'
    """
    if 'playlist' in url and 'list=' in url:
        return 'playlist'
    elif 'channel' in url or 'user' in url or 'c/' in url:
        return 'channel'
    elif 'watch' in url or 'youtu.be' in url:
        return 'video'
    else:
        return 'unknown'


def process_youtube_url(url: str, include_comments: bool = False, max_comments: int = 30, max_videos: int = 10) -> Optional[Dict[str, Any]]:
    """
    Process any YouTube URL by determining its type and calling the appropriate processor.
    
    Args:
        url: YouTube URL
        include_comments: Whether to include comments
        max_comments: Maximum number of comments per video
        max_videos: Maximum number of videos to process for channels
        
    Returns:
        Processed data dictionary or None if processing failed
    """
    if not is_youtube_url(url):
        logger.warning(f"Not a YouTube URL: {url}")
        return None
    
    url_type = identify_youtube_url_type(url)
    
    if url_type == 'video':
        try:
            video_id = extract_video_id(url)
            return process_video(video_id, include_comments, max_comments)
        except ValueError as e:
            logger.error(f"Invalid YouTube video URL: {e}")
            return None
    
    elif url_type == 'playlist':
        return process_playlist(url, include_comments, max_comments)
    
    elif url_type == 'channel':
        return process_channel(url, max_videos, include_comments, max_comments)
    
    else:
        logger.error(f"Unknown YouTube URL type: {url}")
        return None


def format_youtube_content_as_markdown(content: Dict[str, Any]) -> str:
    """
    Format YouTube content as Markdown.
    
    Args:
        content: YouTube content dictionary
        
    Returns:
        Markdown formatted content
    """
    if not content:
        return "No content to format."
    
    markdown = ""
    
    if content['type'] == 'youtube_video':
        markdown += f"# {content['title']}\n\n"
        markdown += f"**URL:** {content['url']}\n\n"
        markdown += f"**Uploader:** {content['uploader']}\n\n"
        
        if 'upload_date' in content and content['upload_date']:
            formatted_date = format_date(content['upload_date'])
            markdown += f"**Upload Date:** {formatted_date}\n\n"
        
        if 'description' in content and content['description']:
            markdown += "## Description\n\n"
            markdown += f"{content['description']}\n\n"
        
        if 'transcript' in content and content['transcript'] != "No transcript available":
            markdown += "## Transcript\n\n"
            markdown += f"{content['transcript']}\n\n"
        
        if 'comments' in content and content['comments']:
            markdown += "## Comments\n\n"
            for comment in content['comments']:
                markdown += f"{comment}\n---\n\n"
    
    elif content['type'] in ['youtube_playlist', 'youtube_channel']:
        content_type = "Playlist" if content['type'] == 'youtube_playlist' else "Channel"
        markdown += f"# {content['title']} ({content_type})\n\n"
        markdown += f"**URL:** {content['url']}\n\n"
        markdown += f"**Uploader:** {content['uploader']}\n\n"
        markdown += f"**Videos:** {content['video_count']}\n\n"
        
        if 'videos' in content and content['videos']:
            for i, video in enumerate(content['videos'], 1):
                markdown += f"## {i}. {video['title']}\n\n"
                markdown += f"**URL:** {video['url']}\n\n"
                
                if 'transcript' in video and video['transcript'] != "No transcript available":
                    markdown += "### Transcript\n\n"
                    markdown += f"{video['transcript']}\n\n"
                
                if 'comments' in video and video['comments']:
                    markdown += "### Comments\n\n"
                    for comment in video['comments']:
                        markdown += f"{comment}\n---\n\n"
                
                markdown += "---\n\n"
    
    return markdown


def format_youtube_content_as_tagged(content: Dict[str, Any]) -> str:
    """
    Format YouTube content as tagged text.
    
    Args:
        content: YouTube content dictionary
        
    Returns:
        Tagged formatted content
    """
    if not content:
        return "No content to format."
    
    tagged = ""
    
    if content['type'] == 'youtube_video':
        tagged += f"title: {content['title']}\n"
        tagged += f"url: {content['url']}\n"
        tagged += f"uploader: {content['uploader']}\n"
        
        if 'upload_date' in content and content['upload_date']:
            formatted_date = format_date(content['upload_date'])
            tagged += f"upload_date: {formatted_date}\n"
        
        if 'description' in content and content['description']:
            tagged += f"description: {content['description']}\n"
        
        if 'transcript' in content and content['transcript'] != "No transcript available":
            tagged += f"transcript: {content['transcript']}\n"
        
        if 'comments' in content and content['comments']:
            tagged += "comments:\n"
            for comment in content['comments']:
                tagged += f"comment: {comment}\n"
    
    elif content['type'] in ['youtube_playlist', 'youtube_channel']:
        content_type = "playlist" if content['type'] == 'youtube_playlist' else "channel"
        tagged += f"{content_type}_title: {content['title']}\n"
        tagged += f"{content_type}_url: {content['url']}\n"
        tagged += f"{content_type}_uploader: {content['uploader']}\n"
        tagged += f"{content_type}_video_count: {content['video_count']}\n"
        
        if 'videos' in content and content['videos']:
            for i, video in enumerate(content['videos'], 1):
                tagged += f"video_{i}_title: {video['title']}\n"
                tagged += f"video_{i}_url: {video['url']}\n"
                
                if 'transcript' in video and video['transcript'] != "No transcript available":
                    tagged += f"video_{i}_transcript: {video['transcript']}\n"
                
                if 'comments' in video and video['comments']:
                    tagged += f"video_{i}_comments:\n"
                    for comment in video['comments']:
                        tagged += f"video_{i}_comment: {comment}\n"
    
    return tagged


def format_date(date_str: str) -> str:
    """
    Format date string (YYYYMMDD) into a more readable format.
    
    Args:
        date_str: Date string in YYYYMMDD format
        
    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    if not date_str or len(date_str) != 8:
        return date_str
    
    try:
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    except Exception:
        return date_str