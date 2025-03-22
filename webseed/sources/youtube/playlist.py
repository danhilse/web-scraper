"""YouTube playlist processing module for extracting videos from playlists."""

import yt_dlp
from typing import Dict, Any, List, Optional

from webseed.utils.logging import get_logger
from webseed.sources.youtube.video import process_video

logger = get_logger(__name__)


def get_playlist_videos(playlist_url: str) -> Dict[str, Any]:
    """
    Retrieve all video IDs and playlist title from a YouTube playlist.
    
    Args:
        playlist_url: URL of the YouTube playlist
        
    Returns:
        Dictionary with video IDs and playlist title
    """
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' in result:
                return {
                    'video_ids': [entry['id'] for entry in result['entries'] if 'id' in entry],
                    'playlist_title': result.get('title', 'Unknown Playlist'),
                    'playlist_url': playlist_url,
                    'uploader': result.get('uploader', 'Unknown'),
                    'video_count': len(result.get('entries', [])),
                }
            else:
                logger.warning(f"No entries found in playlist: {playlist_url}")
                return {
                    'video_ids': [],
                    'playlist_title': 'Unknown Playlist',
                    'playlist_url': playlist_url,
                    'uploader': 'Unknown',
                    'video_count': 0,
                }
    except Exception as e:
        logger.error(f"Error fetching playlist {playlist_url}: {e}")
        return {
            'video_ids': [],
            'playlist_title': 'Unknown Playlist',
            'playlist_url': playlist_url,
            'uploader': 'Unknown',
            'video_count': 0,
        }


def process_playlist(playlist_url: str, include_comments: bool = False, max_comments: int = 30, 
                      use_cache: bool = True) -> Dict[str, Any]:
    """
    Process a YouTube playlist to extract videos, transcripts, and optional comments.
    
    Args:
        playlist_url: URL of the YouTube playlist
        include_comments: Whether to include comments for each video
        max_comments: Maximum number of comments to fetch per video
        use_cache: Whether to use and update the cache
        
    Returns:
        Dictionary with playlist information and list of video data
    """
    logger.info(f"Processing YouTube playlist: {playlist_url}")
    
    from webseed.sources.youtube.cache import get_cache
    cache = get_cache()
    
    # Generate a cache key for the playlist
    playlist_id = None
    match = re.search(r'list=([\w-]+)', playlist_url)
    if match:
        playlist_id = match.group(1)
        
    # If we have a valid playlist ID, check the cache
    playlist_cache_path = None
    if playlist_id and use_cache:
        playlist_cache_path = os.path.join(cache.cache_dir, 'playlists', f"{playlist_id}.json")
        os.makedirs(os.path.dirname(playlist_cache_path), exist_ok=True)
        
        # Check if we have a cached playlist that's not too old (less than 1 day)
        if os.path.exists(playlist_cache_path):
            try:
                with open(playlist_cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Check if the cache is fresh enough (less than 1 day old)
                cache_time = cached_data.get('_cache_timestamp', 0)
                if time.time() - cache_time < 86400:  # 24 hours
                    logger.info(f"Using cached playlist data for {playlist_url}")
                    return cached_data
            except Exception as e:
                logger.warning(f"Error reading playlist cache: {e}")
    
    playlist_info = get_playlist_videos(playlist_url)
    video_ids = playlist_info['video_ids']
    
    if not video_ids:
        logger.warning(f"No videos found in playlist: {playlist_url}")
        result = {
            "type": "youtube_playlist",
            "title": playlist_info['playlist_title'],
            "url": playlist_url,
            "uploader": playlist_info['uploader'],
            "video_count": 0,
            "videos": []
        }
        
        # Cache the empty result
        if playlist_cache_path:
            try:
                result['_cache_timestamp'] = time.time()
                with open(playlist_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                logger.warning(f"Error caching playlist data: {e}")
                
        return result
    
    total_videos = len(video_ids)
    logger.info(f"Found {total_videos} videos in playlist")
    
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
        "type": "youtube_playlist",
        "title": playlist_info['playlist_title'],
        "url": playlist_url,
        "uploader": playlist_info['uploader'],
        "video_count": len(videos),
        "videos": videos,
        "_cache_timestamp": time.time()
    }
    
    # Cache the result
    if playlist_cache_path:
        try:
            with open(playlist_cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.warning(f"Error caching playlist data: {e}")
    
    return result