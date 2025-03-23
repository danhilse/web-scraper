import re
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, List, Optional, Tuple, Union

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    if re.match(r'^[\w-]{11}$', url):
        return url
    match = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
    if match:
        return match.group(1)
    raise ValueError("Invalid YouTube URL or video ID")

def identify_youtube_url_type(url: str) -> Tuple[str, str]:
    """
    Identify YouTube URL type and return type and ID.
    Returns: (type, id) where type is 'video', 'playlist', or 'channel'
    """
    if 'youtube.com/playlist' in url or 'list=' in url:
        playlist_id = re.search(r'list=([\w-]+)', url)
        return ('playlist', playlist_id.group(1) if playlist_id else '')
    elif 'youtube.com/channel' in url or 'youtube.com/c/' in url or 'youtube.com/@' in url:
        # Extract channel ID or handle
        return ('channel', url.split('/')[-1])
    else:
        # Assume it's a video
        try:
            return ('video', extract_video_id(url))
        except ValueError:
            return ('unknown', '')

def get_transcript(video_id: str) -> str:
    """Get transcript for a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return "\n".join([f"[{entry['start']:.1f}s] {entry['text']}" for entry in transcript])
    except Exception as e:
        print(f"Error fetching transcript for video {video_id}: {e}")
        return ""

def get_video_info(video_id: str, include_comments: bool = False) -> Dict:
    """Get video metadata using yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
    }
    
    if include_comments:
        ydl_opts.update({
            'getcomments': True,
            'extractor_args': {
                'youtube': {
                    'comment_sort': ['likes'],
                    'max_comments': ['30']
                }
            }
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            
            result = {
                'title': info.get('title', 'Unknown'),
                'description': info.get('description', ''),
                'channel': info.get('uploader', 'Unknown'),
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
            if include_comments and 'comments' in info:
                # Filter to top-level comments only
                top_comments = [
                    comment for comment in info.get('comments', [])
                    if comment.get('parent') == 'root'
                ]
                
                # Sort by likes and limit to 30
                sorted_comments = sorted(
                    top_comments,
                    key=lambda x: x.get('like_count', 0) or 0,
                    reverse=True
                )[:30]
                
                result['comments'] = sorted_comments
            
            return result
    except Exception as e:
        print(f"Error fetching info for video {video_id}: {e}")
        return {'title': 'Unknown', 'url': f"https://www.youtube.com/watch?v={video_id}"}

def get_playlist_videos(playlist_id: str, max_videos: int = 30) -> List[str]:
    """Get video IDs from a playlist, limited by max_videos."""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'playlistend': max_videos
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"https://www.youtube.com/playlist?list={playlist_id}", download=False)
            if 'entries' in result:
                return [entry['id'] for entry in result['entries'] if 'id' in entry]
        except Exception as e:
            print(f"Error fetching playlist {playlist_id}: {e}")
    
    return []

def get_channel_videos(channel_id: str, max_videos: int = 30) -> List[str]:
    """Get recent video IDs from a channel, limited by max_videos."""
    if channel_id.startswith('@'):
        url = f"https://www.youtube.com/{channel_id}/videos"
    else:
        url = f"https://www.youtube.com/channel/{channel_id}/videos"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'playlistend': max_videos
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                return [entry['id'] for entry in result['entries'] if 'id' in entry]
        except Exception as e:
            print(f"Error fetching channel {channel_id}: {e}")
    
    return []