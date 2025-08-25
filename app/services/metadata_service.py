"""
Metadata Service - Handles metadata fetching and processing
"""

from typing import Dict, Optional, Any
from app.utils.metadata_utils import ComicMetadataFetcher


class MetadataService:
    """Service for handling metadata operations"""
    
    def __init__(self):
        self.metadata_fetcher = ComicMetadataFetcher()
    
    def search_kapowarr_volume(self, volume_id: str) -> Optional[Dict[str, Any]]:
        """Search for a volume in Kapowarr"""
        return self.metadata_fetcher.search_kapowarr_volume(volume_id)
    
    def get_comicvine_metadata(self, comicvine_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata from ComicVine"""
        return self.metadata_fetcher.get_comicvine_metadata(comicvine_id)