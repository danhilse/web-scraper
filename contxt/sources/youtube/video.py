"""YouTube video processing module for extracting transcripts and comments."""

import re
import yt_dlp
from typing import Dict, Any, Optional, List
from youtube_transcript_api import YouTubeTranscriptApi

from webseed.utils.logging import get_logger

logger = get_logger(__name__)

def extract_video_id(url_or_id: str) -> str:
    """
    Extract the YouTube video ID from a URL or returns the ID if already provided.
    
    Args:
        url_or_id: YouTube URL or video ID
        
    Returns:
        YouTube video ID
        
    Raises:
        ValueError: If the URL or ID is invalid
    """
    # Check if it's already a valid video ID
    if re.match(r'^[\w-]{11}$', url_or_id):
        return url_or_id
    
    # More comprehensive regex for various YouTube URL formats
    # Handles standard watch URLs, shortened youtu.be links, embedded URLs, and more
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url_or_id)
    if match:
        return match.group(1)
    
    # If we get here, it's not a valid YouTube URL or ID
    raise ValueError(f"Invalid YouTube URL or video ID: {url_or_id}")

def get_video_info(video_id: str, include_comments: bool = False, max_comments: int = 30) -> Optional[Dict[str, Any]]:
    """
    Fetch video information including title and optional comments.
    
    Args:
        video_id: YouTube video ID
        include_comments: Whether to include comments
        max_comments: Maximum number of comments to fetch
        
    Returns:
        Dictionary with video information or None if an error occurred
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
    }
    
    # Add comment extraction options if needed
    if include_comments:
        ydl_opts.update({
            'getcomments': True,
            'extractor_args': {
                'youtube': {
                    'comment_sort': ['likes'],
                    'max_comments': [str(max(100, max_comments * 2))]  # Fetch more to filter
                }
            }
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            
            result = {
                'title': info.get('title', 'Unknown Title'),
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'description': info.get('description', ''),
                'upload_date': info.get('upload_date', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'uploader_url': info.get('uploader_url', ''),
            }
            
            if include_comments:
                comments = info.get('comments', [])
                logger.debug(f"Found {len(comments)} comments for video {video_id}")
                
                filtered_comments = filter_comments(comments, max_comments)
                formatted_comments = format_comments(filtered_comments)
                
                result['comments'] = formatted_comments
            
            return result
    except Exception as e:
        logger.error(f"Error fetching info for video {video_id}: {e}")
        return None


def filter_comments(comments: List[Dict[str, Any]], max_comments: int = 30) -> List[Dict[str, Any]]:
    """
    Filter comments to get the most relevant ones.
    
    Args:
        comments: List of comment dictionaries
        max_comments: Maximum number of comments to return
        
    Returns:
        Filtered list of comments
    """
    if not comments:
        return []
    
    # Try to get only root comments
    root_comments = [c for c in comments if c.get('parent') == 'root']
    
    # If no root comments found, use all comments
    if not root_comments:
        root_comments = comments
    
    # Sort by likes if available
    try:
        sorted_comments = sorted(
            root_comments,
            key=lambda x: x.get('like_count', 0) or 0,
            reverse=True
        )
    except Exception:
        # Fallback to sort by text length
        sorted_comments = sorted(
            root_comments,
            key=lambda x: len(x.get('text', '')),
            reverse=True
        )
    
    return sorted_comments[:max_comments]


def format_comments(comments: List[Dict[str, Any]]) -> List[str]:
    """
    Format comments into readable strings.
    
    Args:
        comments: List of comment dictionaries
        
    Returns:
        List of formatted comment strings
    """
    formatted_comments = []
    for comment in comments:
        formatted_comment = (
            f"Author: {comment.get('author', 'Anonymous')}\n"
            f"Comment: {comment.get('text', '')}\n"
        )
        if 'like_count' in comment and comment['like_count']:
            formatted_comment += f"Likes: {comment['like_count']}\n"
        
        formatted_comments.append(formatted_comment)
    
    return formatted_comments


def get_captions(video_id: str, use_cache: bool = True) -> str:
    """
    Retrieve captions (transcript) for a YouTube video.
    
    Args:
        video_id: YouTube video ID
        use_cache: Whether to use and update the cache
        
    Returns:
        Video transcript as text or 'No transcript available'
    """
    from webseed.sources.youtube.cache import get_cache
    cache = get_cache()
    
    # Check cache first if enabled
    if use_cache and cache.has_transcript(video_id):
        cached_transcript = cache.get_transcript(video_id)
        logger.debug(f"Using cached transcript for video {video_id}")
        return cached_transcript
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript])
        
        # Save to cache if enabled
        if use_cache:
            cache.save_transcript(video_id, transcript_text)
            
        return transcript_text
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error fetching captions for video {video_id}: {error_msg}")
        
        # Cache the failure to avoid repeated requests for videos without captions
        if use_cache:
            if "No transcript" in error_msg or "translat" in error_msg:
                cache.save_transcript(video_id, "No transcript available")
                
        return "No transcript available"


def process_video(video_id: str, include_comments: bool = False, max_comments: int = 30, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Process a single video to extract information, transcript and optional comments.
    
    Args:
        video_id: YouTube video ID
        include_comments: Whether to include comments
        max_comments: Maximum number of comments to fetch
        use_cache: Whether to use and update the cache
        
    Returns:
        Dictionary with video data or None if processing failed
    """
    from webseed.sources.youtube.cache import get_cache
    cache = get_cache()
    
    # Check if we have cached metadata
    cached_metadata = None
    if use_cache and not cache.is_metadata_stale(video_id):
        cached_metadata = cache.get_metadata(video_id)
        logger.debug(f"Using cached metadata for video {video_id}")
    
    # Fetch video info or use cache
    if cached_metadata:
        video_info = cached_metadata
    else:
        video_info = get_video_info(video_id, include_comments, max_comments)
        if not video_info:
            logger.error(f"Failed to get info for video {video_id}")
            return None
        
        # Save to cache
        if use_cache:
            cache.save_metadata(video_id, video_info)
    
    # Get captions (this function handles caching internally)
    captions = get_captions(video_id, use_cache)
    if captions == "No transcript available":
        logger.warning(f"No transcript available for video {video_id}")
    
    video_data = {
        "type": "youtube_video",
        "title": video_info['title'],
        "url": video_info['url'],
        "uploader": video_info['uploader'],
        "upload_date": video_info['upload_date'],
        "view_count": video_info['view_count'],
        "duration": video_info['duration'],
        "description": video_info['description'],
        "transcript": captions
    }
    
    if include_comments and 'comments' in video_info:
        video_data['comments'] = video_info['comments']
    
    return video_data