"""Modernized Spotify client with async support and caching."""

import asyncio
import pickle
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time

import numpy as np
import pandas as pd
import requests
import spotipy
from scipy.spatial.distance import cdist
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from tqdm import tqdm

from .exceptions import SpotifyAPIError, DataValidationError
from .data_models import Track, AudioFeatures, Playlist
from .validators import validate_spotify_uri
from .logging_config import get_logger

logger = get_logger(__name__)


class SpotifyClient:
    """Modernized Spotify client with caching and async support."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        cache_dir: Path = Path("cache"),
        cache_ttl: int = 3600  # 1 hour
    ):
        """Initialize Spotify client.
        
        Args:
            client_id: Spotify client ID
            client_secret: Spotify client secret
            redirect_uri: Spotify redirect URI
            cache_dir: Directory for caching data
            cache_ttl: Cache time-to-live in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = cache_ttl
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Spotify clients
        self._init_clients()
        
        # Cache for audio features
        self._audio_features_cache: Dict[str, Tuple[AudioFeatures, float]] = {}
        
    def _init_clients(self) -> None:
        """Initialize Spotify OAuth and client credentials managers."""
        try:
            # For user authentication
            self.oauth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope="user-library-read user-read-private user-read-email"
            )
            
            # For app authentication
            self.client_credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            self.sp = spotipy.Spotify(auth_manager=self.client_credentials_manager)
            logger.info("Spotify client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            raise SpotifyAPIError(f"Failed to initialize Spotify client: {e}")
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is valid and not expired.
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            True if cache is valid
        """
        if not cache_path.exists():
            return False
        
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.cache_ttl
    
    def _load_from_cache(self, cache_key: str) -> Optional[Any]:
        """Load data from cache if valid.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None if not available/expired
        """
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                logger.debug(f"Loaded data from cache: {cache_key}")
                return data
            except Exception as e:
                logger.warning(f"Failed to load cache {cache_key}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """Save data to cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"Saved data to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_key}: {e}")
    
    @lru_cache(maxsize=1000)
    def get_track_features(self, track_uri: str) -> AudioFeatures:
        """Get audio features for a track with caching.
        
        Args:
            track_uri: Spotify track URI
            
        Returns:
            AudioFeatures object
        """
        validate_spotify_uri(track_uri, 'track')
        
        # Check memory cache first
        if track_uri in self._audio_features_cache:
            cached_data, timestamp = self._audio_features_cache[track_uri]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        
        # Check file cache
        cache_key = f"features_{track_uri.replace(':', '_')}"
        cached_features = self._load_from_cache(cache_key)
        
        if cached_features:
            self._audio_features_cache[track_uri] = (cached_features, time.time())
            return cached_features
        
        try:
            # Extract track ID from URI
            track_id = track_uri.split(':')[-1]
            
            # Get features from Spotify API
            features = self.sp.audio_features([track_id])
            
            if not features or not features[0]:
                raise SpotifyAPIError(f"No audio features found for track {track_uri}")
            
            feature_data = features[0]
            
            # Create AudioFeatures object
            audio_features = AudioFeatures(
                danceability=feature_data['danceability'],
                energy=feature_data['energy'],
                key=feature_data['key'],
                loudness=feature_data['loudness'],
                mode=feature_data['mode'],
                speechiness=feature_data['speechiness'],
                acousticness=feature_data['acousticness'],
                instrumentalness=feature_data['instrumentalness'],
                liveness=feature_data['liveness'],
                valence=feature_data['valence'],
                tempo=feature_data['tempo'],
                duration_ms=feature_data['duration_ms'],
                time_signature=feature_data['time_signature']
            )
            
            # Cache the result
            self._save_to_cache(cache_key, audio_features)
            self._audio_features_cache[track_uri] = (audio_features, time.time())
            
            return audio_features
            
        except Exception as e:
            logger.error(f"Failed to get audio features for {track_uri}: {e}")
            raise SpotifyAPIError(f"Failed to get audio features: {e}")
    
    async def get_multiple_track_features(self, track_uris: List[str]) -> List[AudioFeatures]:
        """Get audio features for multiple tracks concurrently.
        
        Args:
            track_uris: List of Spotify track URIs
            
        Returns:
            List of AudioFeatures objects
        """
        if not track_uris:
            return []
        
        # Validate all URIs first
        for uri in track_uris:
            validate_spotify_uri(uri, 'track')
        
        # Create tasks for concurrent execution
        tasks = []
        for uri in track_uris:
            task = asyncio.create_task(
                asyncio.to_thread(self.get_track_features, uri)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and rethrow if any
            audio_features = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to get features for {track_uris[i]}: {result}")
                    raise result
                audio_features.append(result)
            
            return audio_features
            
        except Exception as e:
            logger.error(f"Failed to get multiple track features: {e}")
            raise SpotifyAPIError(f"Failed to get multiple track features: {e}")
    
    def get_track_info(self, track_uri: str) -> Track:
        """Get detailed track information.
        
        Args:
            track_uri: Spotify track URI
            
        Returns:
            Track object
        """
        validate_spotify_uri(track_uri, 'track')
        
        # Check cache
        cache_key = f"track_{track_uri.replace(':', '_')}"
        cached_track = self._load_from_cache(cache_key)
        
        if cached_track:
            return cached_track
        
        try:
            track_id = track_uri.split(':')[-1]
            track_data = self.sp.track(track_id)
            
            track = Track(
                track_uri=track_uri,
                track_name=track_data['name'],
                artist_name=track_data['artists'][0]['name'],
                artist_uri=track_data['artists'][0]['uri'],
                album_uri=track_data['album']['uri'],
                album_name=track_data['album']['name'],
                track_id=track_data['id']
            )
            
            # Cache the result
            self._save_to_cache(cache_key, track)
            
            return track
            
        except Exception as e:
            logger.error(f"Failed to get track info for {track_uri}: {e}")
            raise SpotifyAPIError(f"Failed to get track info: {e}")
    
    def calculate_similarity_matrix(
        self, 
        track_uris: List[str],
        feature_weights: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """Calculate similarity matrix between tracks based on audio features.
        
        Args:
            track_uris: List of Spotify track URIs
            feature_weights: Optional weights for different features
            
        Returns:
            Similarity matrix
        """
        if not track_uris:
            raise DataValidationError("Track URIs list cannot be empty")
        
        # Default feature weights
        if feature_weights is None:
            feature_weights = {
                'danceability': 0.1,
                'energy': 0.1,
                'key': 0.05,
                'loudness': 0.1,
                'mode': 0.05,
                'speechiness': 0.1,
                'acousticness': 0.1,
                'instrumentalness': 0.1,
                'liveness': 0.05,
                'valence': 0.15,
                'tempo': 0.1
            }
        
        try:
            # Get audio features for all tracks
            features_list = []
            for uri in tqdm(track_uris, desc="Getting audio features"):
                features = self.get_track_features(uri)
                
                # Create feature vector with weights
                feature_vector = np.array([
                    features.danceability * feature_weights.get('danceability', 1.0),
                    features.energy * feature_weights.get('energy', 1.0),
                    features.key * feature_weights.get('key', 1.0),
                    features.loudness * feature_weights.get('loudness', 1.0),
                    features.mode * feature_weights.get('mode', 1.0),
                    features.speechiness * feature_weights.get('speechiness', 1.0),
                    features.acousticness * feature_weights.get('acousticness', 1.0),
                    features.instrumentalness * feature_weights.get('instrumentalness', 1.0),
                    features.liveness * feature_weights.get('liveness', 1.0),
                    features.valence * feature_weights.get('valence', 1.0),
                    features.tempo * feature_weights.get('tempo', 1.0)
                ])
                
                features_list.append(feature_vector)
            
            # Calculate similarity matrix using cosine distance
            features_matrix = np.array(features_list)
            similarity_matrix = 1 - cdist(features_matrix, features_matrix, metric='cosine')
            
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity matrix: {e}")
            raise SpotifyAPIError(f"Failed to calculate similarity matrix: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            # Clear file cache
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            
            # Clear memory cache
            self._audio_features_cache.clear()
            
            # Clear LRU cache
            self.get_track_features.cache_clear()
            
            logger.info("Cache cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise SpotifyAPIError(f"Failed to clear cache: {e}")
