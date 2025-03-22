"""YouTube channel processing module for extracting videos from channels."""

import yt_dlp
from typing import Dict, Any, List, Optional

from webseed.utils.logging import get_logger
from webseed.sources.youtube.video import process_video

logger = get_logger(__name__)


def get_channel_videos(channel_url: str, max_videos: int = 10) -> Dict[str, Any]:
    """
    Retrieve video IDs and channel information from a YouTube channel.
    
    Args:
        channel_url: URL of the YouTube channel
        max_videos: Maximum number of videos to retrieve from the channel
        
    Returns:
        Dictionary with video IDs and channel information
    """
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'playlistend': max_videos  # Limit number of videos to fetch
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            
            if 'entries' in result:
                return {
                    'video_ids': [entry['id'] for entry in result['entries'] if 'id' in entry],
                    'channel_title': result.get('title', 'Unknown Channel'),
                    'channel_url': channel_url,
                    'uploader': result.get('uploader', 'Unknown'),
                    'video_count': len(result.get('entries', [])),
                }
            else:
                logger.warning(f"No entries found in channel: {channel_url}")
                return {
                    'video_ids': [],
                    'channel_title': 'Unknown Channel',
                    'channel_url': channel_url,
                    'uploader': 'Unknown',
                    'video_count': 0,
                }
    except Exception as e:
        logger.error(f"Error fetching channel {channel_url}: {e}")
        return {
            'video_ids': [],
            'channel_title': 'Unknown Channel',
            'channel_url': channel_url,
            'uploader': 'Unknown',
            'video_count': 0,
        }


def process_channel(channel_url: str, max_videos: int = 10, include_comments: bool = False, 
                     max_comments: int = 30, use_cache: bool = True) -> Dict[str, Any]:
    """
    Process a YouTube channel to extract videos, transcripts, and optional comments.
    
    Args:
        channel_url: URL of the YouTube channel
        max_videos: Maximum number of videos to process from the channel
        include_comments: Whether to include comments for each video
        max_comments: Maximum number of comments to fetch per video
        use_cache: Whether to use and update the cache
        
    Returns:
        Dictionary with channel information and list of video data
    """
    logger.info(f"Processing YouTube channel: {channel_url}")
    
    from webseed.sources.youtube.cache import get_cache
    cache = get_cache()
    
    # Extract channel ID
    channel_id = None
    if '/channel/' in channel_url:
        channel_id = channel_url.split('/channel/')[1].split('/')[0]
    elif '/c/' in channel_url:
        # For custom URLs, we'll use the URL path as the cache key
        channel_id = 'c_' + channel_url.split('/c/')[1].split('/')[0]
    elif '/user/' in channel_url:
        channel_id = 'user_' + channel_url.split('/user/')[1].split('/')[0]
    elif '@' in channel_url:
        channel_id = channel_url.split('@')[1].split('/')[0]
        
    # If we have a valid channel ID, check the cache
    channel_cache_path = None
    if channel_id and use_cache:
        channel_cache_path = os.path.join(cache.cache_dir, 'channels', f"{channel_id}.json")
        os.makedirs(os.path.dirname(channel_cache_path), exist_ok=True)
        
        # Check if we have a cached channel that's not too old (less than 1 day)
        if os.path.exists(channel_cache_path):
            try:
                with open(channel_cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Check if the cache is fresh enough (less than 1 day old)
                cache_time = cached_data.get('_cache_timestamp', 0)
                if time.time() - cache_time < 86400:  # 24 hours
                    logger.info(f"Using cached channel data for {channel_url}")
                    return cached_data
            except Exception as e:
                logger.warning(f"Error reading channel cache: {e}")
    
    channel_info = get_channel_videos(channel_url, max_videos)
    video_ids = channel_info['video_ids']
    
    if not video_ids:
        logger.warning(f"No videos found in channel: {channel_url}")
        result = {
            "type": "youtube_channel",
            "title": channel_info['channel_title'],
            "url": channel_url,
            "uploader": channel_info['uploader'],
            "video_count": 0,
            "videos": []
        }
        
        # Cache the empty result
        if channel_cache_path:
            try:
                result['_cache_timestamp'] = time.time()
                with open(channel_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                logger.warning(f"Error caching channel data: {e}")
                
        return result
    
    total_videos = len(video_ids)
    logger.info(f"Found {total_videos} videos in channel (limited to {max_videos})")
    
    videos = []
    for i, video_id in enumerate(video_ids, 1):
        logger.info(f"Processing video {i}/{total_videos}: {video_id}")
        
        video_data = process_video(video_id, include_comments, max_comments, use_cache)
        if video_data:
            videos.append(video_data)
            
        # Report progress
        if i % 5 == 0 or i == total_videos:
            logger.info(f"Progress: {i}/{total_videos} videos processed ({i/total_videos*100:.1f}%)")
    
    result = {
        "type": "youtube_channel",
        "title": channel_info['channel_title'],
        "url": channel_url,
        "uploader": channel_info['uploader'],
        "video_count": len(videos),
        "videos": videos,
        "_cache_timestamp": time.time()
    }
    
    # Cache the result
    if channel_cache_path:
        try:
            with open(channel_cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.warning(f"Error caching channel data: {e}")
    
    return result