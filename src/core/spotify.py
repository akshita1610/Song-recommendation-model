"""Modern Spotify API client with async support and Pydantic models."""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import base64

import httpx
import spotipy
from loguru import logger
from pydantic import BaseModel, Field, HttpUrl, validator
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

from ..exceptions import SpotifyAPIError, DataValidationError
from ..validators import validate_spotify_uri
from ..logging_config import get_logger


class SpotifyTrack(BaseModel):
    """Pydantic model for Spotify track data."""
    
    id: str = Field(..., description="Spotify track ID")
    name: str = Field(..., description="Track name")
    artist: str = Field(..., description="Primary artist name")
    album: str = Field(..., description="Album name")
    uri: str = Field(..., description="Spotify URI")
    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    popularity: int = Field(..., ge=0, le=100, description="Popularity score 0-100")
    
    @validator('uri')
    def validate_spotify_uri_format(cls, v):
        """Validate Spotify URI format."""
        validate_spotify_uri(v, 'track')
        return v
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True


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
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


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
        redirect_uri: str = "http://localhost:8888/callback",
        config: Optional[SpotifyConfig] = None
    ):
        """Initialize Spotify client.
        
        Args:
            client_id: Spotify client ID
            client_secret: Spotify client secret
            redirect_uri: OAuth redirect URI
            config: Optional configuration object
        """
        self.config = config or SpotifyConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        
        self.logger = get_logger(__name__)
        
        # Initialize Spotify clients
        self._init_clients()
        
        # HTTP client for async operations
        self._http_client = httpx.AsyncClient(timeout=self.config.requests_timeout)
        
        # Cache for track data
        self._track_cache: Dict[str, SpotifyTrack] = {}
        self._features_cache: Dict[str, AudioFeatures] = {}
    
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
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._track_cache.clear()
        self._features_cache.clear()
        self.logger.info("Spotify client cache cleared")
    
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
