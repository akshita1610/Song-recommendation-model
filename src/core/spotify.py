"""Modern Spotify API client with async support and Pydantic models."""

import asyncio
import os
import pickle
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
import base64

import httpx
import numpy as np
import pandas as pd
import spotipy
from loguru import logger
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from scipy.spatial.distance import cdist
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from tqdm import tqdm

from ..exceptions import SpotifyAPIError, DataValidationError
from ..validators import validate_spotify_uri
from ..logging_config import get_logger


class SpotifyTrack(BaseModel):
    """Pydantic model for Spotify track data."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
    
    id: str = Field(..., description="Spotify track ID")
    name: str = Field(..., description="Track name")
    artist: str = Field(..., description="Primary artist name")
    album: str = Field(..., description="Album name")
    uri: str = Field(..., description="Spotify URI")
    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    popularity: int = Field(..., ge=0, le=100, description="Popularity score 0-100")
    
    @field_validator('uri')
    @classmethod
    def validate_spotify_uri_format(cls, v):
        """Validate Spotify URI format."""
        validate_spotify_uri(v, 'track')
        return v


class AudioFeatures(BaseModel):
    """Pydantic model for audio features."""
    
    danceability: float = Field(..., ge=0.0, le=1.0)
    energy: float = Field(..., ge=0.0, le=1.0)
    key: int = Field(..., ge=-1, le=11)
    loudness: float = Field(..., ge=-60.0, le=0.0)
    mode: int = Field(..., ge=0, le=1)
    speechiness: float = Field(..., ge=0.0, le=1.0)
    acousticness: float = Field(..., ge=0.0, le=1.0)
    instrumentalness: float = Field(..., ge=0.0, le=1.0)
    liveness: float = Field(..., ge=0.0, le=1.0)
    valence: float = Field(..., ge=0.0, le=1.0)
    tempo: float = Field(..., ge=0.0)
    duration_ms: int = Field(..., ge=0)
    time_signature: int = Field(..., ge=1, le=12)
    
    model_config = ConfigDict(
        validate_assignment=True
    )


class PlaylistInfo(BaseModel):
    """Pydantic model for playlist information."""
    
    id: str
    name: str
    description: Optional[str] = None
    uri: str
    tracks_count: int = Field(..., ge=0)
    followers: int = Field(..., ge=0)
    public: bool
    collaborative: bool


@dataclass
class SpotifyConfig:
    """Configuration for Spotify client."""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8888/callback"
    scope: str = (
        "user-library-read user-follow-read playlist-modify-private "
        "playlist-modify user-top-read user-read-private"
    )
    cache_path: Optional[Path] = None
    requests_timeout: int = 30
    retries: int = 3


class SpotifyClient:
    """Modern Spotify API client with async support and caching."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        config: Optional[SpotifyConfig] = None,
        cache_dir: Path = Path("cache"),
        cache_ttl: int = 3600  # 1 hour
    ):
        """Initialize Spotify client.
        
        Args:
            client_id: Spotify client ID
            client_secret: Spotify client secret
            redirect_uri: Spotify redirect URI
            config: Optional Spotify configuration
            cache_dir: Directory for caching data
            cache_ttl: Cache time-to-live in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.config = config or SpotifyConfig()
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = cache_ttl
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger first
        self.logger = get_logger(__name__)
        
        # Initialize clients
        self._init_clients()
        
        # In-memory caches
        self._track_cache: Dict[str, SpotifyTrack] = {}
        self._features_cache: Dict[str, AudioFeatures] = {}
        
        # File-based cache for audio features (from legacy)
        self._audio_features_cache: Dict[str, Tuple[AudioFeatures, float]] = {}
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is valid and not expired."""
        if not cache_path.exists():
            return False
        
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.cache_ttl
    
    def _load_from_cache(self, cache_key: str) -> Optional[Any]:
        """Load data from cache if valid."""
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache {cache_key}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """Save data to cache."""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            self.logger.warning(f"Failed to save cache {cache_key}: {e}")
    
    def _init_clients(self) -> None:
        """Initialize Spotify OAuth and client credentials managers."""
        try:
            # For user authentication
            self.oauth_manager = SpotifyOAuth(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                redirect_uri=self.config.redirect_uri,
                scope=self.config.scope,
                cache_path=str(self.config.cache_path) if self.config.cache_path else None
            )
            
            # For app authentication
            self.client_credentials_manager = SpotifyClientCredentials(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )
            
            # Initialize Spotify client
            self._client = Spotify(auth_manager=self.client_credentials_manager)
            
            self.logger.info("Spotify client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify client: {e}")
            raise SpotifyAPIError(f"Failed to initialize Spotify client: {e}")
    
    async def get_track(self, track_id: str) -> Optional[SpotifyTrack]:
        """Get track details by ID with caching.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            SpotifyTrack object or None if not found
        """
        # Check cache first
        if track_id in self._track_cache:
            self.logger.debug(f"Track {track_id} found in cache")
            return self._track_cache[track_id]
        
        try:
            # Run synchronous Spotify API call in thread pool
            track_data = await asyncio.to_thread(self._client.track, track_id)
            
            if not track_data:
                self.logger.warning(f"Track {track_id} not found")
                return None
            
            # Create SpotifyTrack object
            track = SpotifyTrack(
                id=track_data["id"],
                name=track_data["name"],
                artist=track_data["artists"][0]["name"],
                album=track_data["album"]["name"],
                uri=track_data["uri"],
                duration_ms=track_data["duration_ms"],
                popularity=track_data["popularity"]
            )
            
            # Cache the result
            self._track_cache[track_id] = track
            
            self.logger.debug(f"Successfully fetched track: {track.name}")
            return track
            
        except Exception as e:
            self.logger.error(f"Error fetching track {track_id}: {e}")
            raise SpotifyAPIError(f"Failed to fetch track {track_id}: {e}")
    
    async def get_audio_features(self, track_id: str) -> Optional[AudioFeatures]:
        """Get audio features for a track with caching.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            AudioFeatures object or None if not found
        """
        # Check cache first
        if track_id in self._features_cache:
            self.logger.debug(f"Audio features for {track_id} found in cache")
            return self._features_cache[track_id]
        
        try:
            # Get audio features
            features_data = await asyncio.to_thread(
                self._client.audio_features, [track_id]
            )
            
            if not features_data or not features_data[0]:
                self.logger.warning(f"Audio features for {track_id} not found")
                return None
            
            features = features_data[0]
            
            # Create AudioFeatures object
            audio_features = AudioFeatures(
                danceability=features["danceability"],
                energy=features["energy"],
                key=features["key"],
                loudness=features["loudness"],
                mode=features["mode"],
                speechiness=features["speechiness"],
                acousticness=features["acousticness"],
                instrumentalness=features["instrumentalness"],
                liveness=features["liveness"],
                valence=features["valence"],
                tempo=features["tempo"],
                duration_ms=features["duration_ms"],
                time_signature=features["time_signature"]
            )
            
            # Cache the result
            self._features_cache[track_id] = audio_features
            
            self.logger.debug(f"Successfully fetched audio features for track {track_id}")
            return audio_features
            
        except Exception as e:
            self.logger.error(f"Error fetching audio features for {track_id}: {e}")
            raise SpotifyAPIError(f"Failed to fetch audio features for {track_id}: {e}")
    
    async def get_recommendations(
        self,
        seed_tracks: List[str],
        limit: int = 20,
        target_features: Optional[Dict[str, float]] = None
    ) -> List[SpotifyTrack]:
        """Get track recommendations based on seed tracks.
        
        Args:
            seed_tracks: List of seed track IDs (max 5)
            limit: Number of recommendations to return (max 100)
            target_features: Optional target audio features
            
        Returns:
            List of SpotifyTrack objects
        """
        if len(seed_tracks) > 5:
            raise DataValidationError("Maximum 5 seed tracks allowed")
        
        if limit > 100:
            raise DataValidationError("Maximum 100 recommendations allowed")
        
        try:
            # Prepare recommendation parameters
            params = {
                "seed_tracks": seed_tracks,
                "limit": min(limit, 100)
            }
            
            # Add target features if provided
            if target_features:
                params.update(target_features)
            
            # Get recommendations
            results = await asyncio.to_thread(self._client.recommendations, **params)
            
            # Convert to SpotifyTrack objects
            tracks = []
            for track_data in results.get("tracks", []):
                try:
                    track = SpotifyTrack(
                        id=track_data["id"],
                        name=track_data["name"],
                        artist=track_data["artists"][0]["name"],
                        album=track_data["album"]["name"],
                        uri=track_data["uri"],
                        duration_ms=track_data["duration_ms"],
                        popularity=track_data["popularity"]
                    )
                    tracks.append(track)
                except Exception as e:
                    self.logger.warning(f"Error processing track recommendation: {e}")
                    continue
            
            self.logger.info(f"Generated {len(tracks)} recommendations")
            return tracks
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            raise SpotifyAPIError(f"Failed to get recommendations: {e}")
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[SpotifyTrack]:
        """Get all tracks from a playlist with pagination.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of SpotifyTrack objects
        """
        try:
            # Get initial playlist tracks
            results = await asyncio.to_thread(
                self._client.playlist_tracks, playlist_id
            )
            
            tracks = []
            items = results.get("items", [])
            
            # Process initial batch
            for item in items:
                if item.get("track"):
                    try:
                        track = SpotifyTrack(
                            id=item["track"]["id"],
                            name=item["track"]["name"],
                            artist=item["track"]["artists"][0]["name"],
                            album=item["track"]["album"]["name"],
                            uri=item["track"]["uri"],
                            duration_ms=item["track"]["duration_ms"],
                            popularity=item["track"]["popularity"]
                        )
                        tracks.append(track)
                    except Exception as e:
                        self.logger.warning(f"Error processing playlist track: {e}")
                        continue
            
            # Handle pagination
            while results.get("next"):
                results = await asyncio.to_thread(self._client.next, results)
                
                for item in results.get("items", []):
                    if item.get("track"):
                        try:
                            track = SpotifyTrack(
                                id=item["track"]["id"],
                                name=item["track"]["name"],
                                artist=item["track"]["artists"][0]["name"],
                                album=item["track"]["album"]["name"],
                                uri=item["track"]["uri"],
                                duration_ms=item["track"]["duration_ms"],
                                popularity=item["track"]["popularity"]
                            )
                            tracks.append(track)
                        except Exception as e:
                            self.logger.warning(f"Error processing playlist track: {e}")
                            continue
            
            self.logger.info(f"Fetched {len(tracks)} tracks from playlist {playlist_id}")
            return tracks
            
        except Exception as e:
            self.logger.error(f"Error fetching playlist {playlist_id}: {e}")
            raise SpotifyAPIError(f"Failed to fetch playlist {playlist_id}: {e}")
    
    async def search_tracks(
        self,
        query: str,
        limit: int = 20,
        market: str = "US"
    ) -> List[SpotifyTrack]:
        """Search for tracks.
        
        Args:
            query: Search query
            limit: Number of results to return
            market: Market code (e.g., "US")
            
        Returns:
            List of SpotifyTrack objects
        """
        try:
            results = await asyncio.to_thread(
                self._client.search,
                q=query,
                type="track",
                limit=min(limit, 50),  # Spotify's max is 50
                market=market
            )
            
            tracks = []
            for track_data in results.get("tracks", {}).get("items", []):
                try:
                    track = SpotifyTrack(
                        id=track_data["id"],
                        name=track_data["name"],
                        artist=track_data["artists"][0]["name"],
                        album=track_data["album"]["name"],
                        uri=track_data["uri"],
                        duration_ms=track_data["duration_ms"],
                        popularity=track_data["popularity"]
                    )
                    tracks.append(track)
                except Exception as e:
                    self.logger.warning(f"Error processing search result: {e}")
                    continue
            
            self.logger.info(f"Found {len(tracks)} tracks for query: {query}")
            return tracks
            
        except Exception as e:
            self.logger.error(f"Error searching tracks: {e}")
            raise SpotifyAPIError(f"Failed to search tracks: {e}")
    
    async def get_user_playlists(self, limit: int = 50) -> List[PlaylistInfo]:
        """Get current user's playlists.
        
        Args:
            limit: Number of playlists to return
            
        Returns:
            List of PlaylistInfo objects
        """
        try:
            results = await asyncio.to_thread(
                self._client.current_user_playlists, limit=limit
            )
            
            playlists = []
            for playlist_data in results.get("items", []):
                try:
                    playlist = PlaylistInfo(
                        id=playlist_data["id"],
                        name=playlist_data["name"],
                        description=playlist_data.get("description"),
                        uri=playlist_data["uri"],
                        tracks_count=playlist_data["tracks"]["total"],
                        followers=playlist_data["followers"]["total"],
                        public=playlist_data["public"],
                        collaborative=playlist_data["collaborative"]
                    )
                    playlists.append(playlist)
                except Exception as e:
                    self.logger.warning(f"Error processing playlist: {e}")
                    continue
            
            self.logger.info(f"Fetched {len(playlists)} user playlists")
            return playlists
            
        except Exception as e:
            self.logger.error(f"Error fetching user playlists: {e}")
            raise SpotifyAPIError(f"Failed to fetch user playlists: {e}")
    
    @lru_cache(maxsize=1000)
    def get_track_features(self, track_uri: str) -> AudioFeatures:
        """Get audio features for a track with caching (legacy compatibility).
        
        Args:
            track_uri: Spotify track URI
            
        Returns:
            AudioFeatures object
        """
        try:
            # Extract track ID from URI
            track_id = track_uri.split(':')[-1]
            
            # Check in-memory cache first
            if track_id in self._features_cache:
                return self._features_cache[track_id]
            
            # Check file cache
            cached_features = self._load_from_cache(f"features_{track_id}")
            if cached_features:
                self._features_cache[track_id] = cached_features
                return cached_features
            
            # Fetch from Spotify
            features = self._client.audio_features([track_id])
            if not features or not features[0]:
                raise SpotifyAPIError(f"No audio features found for track {track_id}")
            
            # Convert to AudioFeatures model
            audio_features = AudioFeatures(**features[0])
            
            # Cache the result
            self._features_cache[track_id] = audio_features
            self._save_to_cache(f"features_{track_id}", audio_features.dict())
            
            return audio_features
            
        except Exception as e:
            self.logger.error(f"Failed to get audio features for {track_uri}: {e}")
            raise SpotifyAPIError(f"Failed to get audio features: {e}")
    
    async def get_multiple_track_features(self, track_uris: List[str]) -> List[AudioFeatures]:
        """Get audio features for multiple tracks concurrently.
        
        Args:
            track_uris: List of Spotify track URIs
            
        Returns:
            List of AudioFeatures objects
        """
        try:
            if not track_uris:
                return []
            
            # Create tasks for concurrent fetching
            tasks = []
            for uri in track_uris:
                # Check cache first
                track_id = uri.split(':')[-1]
                if track_id in self._features_cache:
                    tasks.append(asyncio.create_task(asyncio.sleep(0, self._features_cache[track_id])))
                else:
                    task = asyncio.create_task(self.get_audio_features(track_id))
                    tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return valid results
            features_list = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Failed to get features for a track: {result}")
                elif result is not None:
                    features_list.append(result)
            
            return features_list
            
        except Exception as e:
            self.logger.error(f"Failed to get multiple track features: {e}")
            raise SpotifyAPIError(f"Failed to get multiple track features: {e}")
    
    def calculate_similarity_matrix(
        self, 
        track_uris: List[str],
        feature_weights: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """Calculate similarity matrix between tracks using audio features.
        
        Args:
            track_uris: List of Spotify track URIs
            feature_weights: Optional weights for features
            
        Returns:
            Similarity matrix as numpy array
        """
        try:
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
                    'valence': 0.1,
                    'tempo': 0.1,
                    'duration_ms': 0.05
                }
            
            # Get audio features for all tracks
            features_list = []
            for uri in track_uris:
                features = self.get_track_features(uri)
                # Create feature vector
                feature_vector = np.array([
                    features.danceability,
                    features.energy,
                    features.key / 11.0,  # Normalize key
                    (features.loudness + 60) / 80.0,  # Normalize loudness
                    features.mode,
                    features.speechiness,
                    features.acousticness,
                    features.instrumentalness,
                    features.liveness,
                    features.valence,
                    features.tempo / 200.0,  # Normalize tempo
                    features.duration_ms / 300000.0  # Normalize duration
                ])
                
                # Apply weights
                weighted_vector = feature_vector * np.array(list(feature_weights.values()))
                features_list.append(weighted_vector)
            
            # Calculate similarity matrix
            features_matrix = np.array(features_list)
            similarity_matrix = 1 - cdist(features_matrix, features_matrix, 'cosine')
            
            return similarity_matrix
            
        except Exception as e:
            self.logger.error(f"Failed to calculate similarity matrix: {e}")
            raise SpotifyAPIError(f"Failed to calculate similarity matrix: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            # Clear in-memory caches
            self._track_cache.clear()
            self._features_cache.clear()
            self._audio_features_cache.clear()
            
            # Clear file cache
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.pkl"):
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete cache file {cache_file}: {e}")
            
            # Clear LRU cache
            self.get_track_features.cache_clear()
            
            self.logger.info("Spotify client cache cleared")
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self._http_client.aclose()
        self.logger.info("Spotify client closed")
    
    @classmethod
    def from_env(cls, cache_path: Optional[Path] = None) -> "SpotifyClient":
        """Create client using environment variables.
        
        Args:
            cache_path: Optional path for cache directory
            
        Returns:
            Configured SpotifyClient instance
        """
        client_id = os.getenv("SPOTIPY_CLIENT_ID", "")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
        
        if not client_id or not client_secret:
            raise SpotifyAPIError(
                "SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set in environment variables"
            )
        
        config = SpotifyConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            cache_path=cache_path
        )
        
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            config=config
        )
