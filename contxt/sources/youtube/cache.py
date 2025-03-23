"""Caching system for YouTube transcripts and metadata."""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

from webseed.utils.logging import get_logger

logger = get_logger(__name__)


class TranscriptCache:
    """Cache for YouTube transcripts and video information."""
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize the transcript cache.
        
        Args:
            cache_dir: Directory to store cache files. If None, uses 'webseed_cache' in the current directory.
        """
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), 'webseed_cache', 'youtube')
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """Create the cache directory if it doesn't exist."""
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(self.cache_dir, 'transcripts'), exist_ok=True)
        os.makedirs(os.path.join(self.cache_dir, 'metadata'), exist_ok=True)
    
    def get_transcript_path(self, video_id: str) -> str:
        """
        Get the file path for the transcript cache.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            File path for the transcript cache
        """
        return os.path.join(self.cache_dir, 'transcripts', f"{video_id}.txt")
    
    def get_metadata_path(self, video_id: str) -> str:
        """
        Get the file path for the video metadata cache.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            File path for the metadata cache
        """
        return os.path.join(self.cache_dir, 'metadata', f"{video_id}.json")
    
    def has_transcript(self, video_id: str) -> bool:
        """
        Check if the transcript is cached.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if the transcript is cached, False otherwise
        """
        return os.path.exists(self.get_transcript_path(video_id))
    
    def has_metadata(self, video_id: str) -> bool:
        """
        Check if the video metadata is cached.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if the metadata is cached, False otherwise
        """
        return os.path.exists(self.get_metadata_path(video_id))
    
    def get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get the cached transcript.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Cached transcript or None if not cached
        """
        if not self.has_transcript(video_id):
            return None
        
        try:
            with open(self.get_transcript_path(video_id), 'r', encoding='utf-8') as f:
                transcript = f.read()
                
            # Check if it's an empty transcript (indicating no captions available)
            if not transcript or transcript == "No transcript available":
                return "No transcript available"
                
            return transcript
        except Exception as e:
            logger.warning(f"Error reading cached transcript for {video_id}: {e}")
            return None
    
    def get_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the cached video metadata.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Cached metadata or None if not cached
        """
        if not self.has_metadata(video_id):
            return None
        
        try:
            with open(self.get_metadata_path(video_id), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading cached metadata for {video_id}: {e}")
            return None
    
    def save_transcript(self, video_id: str, transcript: str) -> bool:
        """
        Cache the transcript.
        
        Args:
            video_id: YouTube video ID
            transcript: Video transcript
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.get_transcript_path(video_id), 'w', encoding='utf-8') as f:
                f.write(transcript or "No transcript available")
            return True
        except Exception as e:
            logger.error(f"Error caching transcript for {video_id}: {e}")
            return False
    
    def save_metadata(self, video_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Cache the video metadata.
        
        Args:
            video_id: YouTube video ID
            metadata: Video metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add cache timestamp
            metadata['_cache_timestamp'] = time.time()
            metadata['_cache_date'] = datetime.now().isoformat()
            
            with open(self.get_metadata_path(video_id), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error caching metadata for {video_id}: {e}")
            return False
    
    def is_metadata_stale(self, video_id: str, max_age_seconds: int = 86400) -> bool:
        """
        Check if the cached metadata is stale.
        
        Args:
            video_id: YouTube video ID
            max_age_seconds: Maximum age in seconds before the cache is considered stale
            
        Returns:
            True if the cache is stale or doesn't exist, False otherwise
        """
        if not self.has_metadata(video_id):
            return True
        
        metadata = self.get_metadata(video_id)
        if not metadata or '_cache_timestamp' not in metadata:
            return True
        
        cache_age = time.time() - metadata['_cache_timestamp']
        return cache_age > max_age_seconds
    
    def clean_old_cache(self, max_age_days: int = 30) -> int:
        """
        Remove old cache files.
        
        Args:
            max_age_days: Maximum age in days before the cache is removed
            
        Returns:
            Number of files removed
        """
        max_age_seconds = max_age_days * 86400
        now = time.time()
        removed_count = 0
        
        # Clean transcripts
        for filename in os.listdir(os.path.join(self.cache_dir, 'transcripts')):
            filepath = os.path.join(self.cache_dir, 'transcripts', filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    try:
                        os.remove(filepath)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old cache file {filepath}: {e}")
        
        # Clean metadata
        for filename in os.listdir(os.path.join(self.cache_dir, 'metadata')):
            filepath = os.path.join(self.cache_dir, 'metadata', filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    try:
                        os.remove(filepath)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old cache file {filepath}: {e}")
        
        return removed_count


# Global cache instance
_cache = None


def get_cache() -> TranscriptCache:
    """
    Get the global cache instance.
    
    Returns:
        Global TranscriptCache instance
    """
    global _cache
    if _cache is None:
        _cache = TranscriptCache()
    return _cache