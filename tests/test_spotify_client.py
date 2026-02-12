"""Test modern Spotify client."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.spotify import (
    SpotifyClient,
    SpotifyTrack,
    AudioFeatures,
    PlaylistInfo,
    SpotifyConfig
)
from src.exceptions import SpotifyAPIError, DataValidationError


class TestSpotifyClient:
    """Test SpotifyClient class."""
    
    @pytest.fixture
    def client_config(self):
        """Create test Spotify configuration."""
        return SpotifyConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8888/callback"
        )
    
    @pytest.fixture
    def mock_spotify_client(self, client_config):
        """Create mock Spotify client."""
        with patch('src.core.spotify.Spotify') as mock_spotify:
            mock_spotify.return_value = MagicMock()
            client = SpotifyClient(
                client_id=client_config.client_id,
                client_secret=client_config.client_secret,
                redirect_uri=client_config.redirect_uri,
                config=client_config
            )
            return client
    
    def test_spotify_config_creation(self):
        """Test SpotifyConfig creation."""
        config = SpotifyConfig(
            client_id="test_id",
            client_secret="test_secret"
        )
        
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.redirect_uri == "http://localhost:8888/callback"
        assert config.scope is not None
    
    def test_spotify_track_validation(self):
        """Test SpotifyTrack model validation."""
        # Valid track
        track = SpotifyTrack(
            id="4iV5W9uYEdYUVa79Axb7Rh",
            name="Test Song",
            artist="Test Artist",
            album="Test Album",
            uri="spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
            duration_ms=180000,
            popularity=50
        )
        
        assert track.id == "4iV5W9uYEdYUVa79Axb7Rh"
        assert track.name == "Test Song"
        assert track.artist == "Test Artist"
        assert track.duration_ms == 180000
        assert track.popularity == 50
    
    def test_spotify_track_invalid_uri(self):
        """Test SpotifyTrack with invalid URI."""
        with pytest.raises(ValueError):  # Pydantic validation error
            SpotifyTrack(
                id="4iV5W9uYEdYUVa79Axb7Rh",
                name="Test Song",
                artist="Test Artist",
                album="Test Album",
                uri="invalid:uri",  # Invalid URI format
                duration_ms=180000,
                popularity=50
            )
    
    def test_audio_features_validation(self):
        """Test AudioFeatures model validation."""
        features = AudioFeatures(
            danceability=0.5,
            energy=0.8,
            key=5,
            loudness=-10.0,
            mode=1,
            speechiness=0.1,
            acousticness=0.3,
            instrumentalness=0.0,
            liveness=0.1,
            valence=0.7,
            tempo=120.0,
            duration_ms=180000,
            time_signature=4
        )
        
        assert features.danceability == 0.5
        assert features.energy == 0.8
        assert features.key == 5
        assert features.tempo == 120.0
    
    def test_audio_features_invalid_range(self):
        """Test AudioFeatures with invalid values."""
        with pytest.raises(ValueError):  # Pydantic validation error
            AudioFeatures(
                danceability=1.5,  # Invalid: > 1.0
                energy=0.8,
                key=5,
                loudness=-10.0,
                mode=1,
                speechiness=0.1,
                acousticness=0.3,
                instrumentalness=0.0,
                liveness=0.1,
                valence=0.7,
                tempo=120.0,
                duration_ms=180000,
                time_signature=4
            )
    
    @pytest.mark.asyncio
    async def test_get_track_success(self, mock_spotify_client):
        """Test successful track retrieval."""
        # Mock Spotify API response
        mock_track_data = {
            "id": "test_track_id",
            "name": "Test Track",
            "artists": [{"name": "Test Artist"}],
            "album": {"name": "Test Album"},
            "uri": "spotify:track:test_track_id",
            "duration_ms": 180000,
            "popularity": 75
        }
        
        mock_spotify_client._client.track.return_value = mock_track_data
        
        # Test the method
        track = await mock_spotify_client.get_track("test_track_id")
        
        assert track is not None
        assert track.id == "test_track_id"
        assert track.name == "Test Track"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.uri == "spotify:track:test_track_id"
        assert track.duration_ms == 180000
        assert track.popularity == 75
    
    @pytest.mark.asyncio
    async def test_get_track_not_found(self, mock_spotify_client):
        """Test track retrieval when track not found."""
        mock_spotify_client._client.track.return_value = None
        
        track = await mock_spotify_client.get_track("nonexistent_id")
        
        assert track is None
    
    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, mock_spotify_client):
        """Test successful recommendations generation."""
        # Mock Spotify API response
        mock_recommendations = {
            "tracks": [
                {
                    "id": "rec_track_1",
                    "name": "Recommended Track 1",
                    "artists": [{"name": "Artist 1"}],
                    "album": {"name": "Album 1"},
                    "uri": "spotify:track:rec_track_1",
                    "duration_ms": 200000,
                    "popularity": 80
                },
                {
                    "id": "rec_track_2", 
                    "name": "Recommended Track 2",
                    "artists": [{"name": "Artist 2"}],
                    "album": {"name": "Album 2"},
                    "uri": "spotify:track:rec_track_2",
                    "duration_ms": 210000,
                    "popularity": 70
                }
            ]
        }
        
        mock_spotify_client._client.recommendations.return_value = mock_recommendations
        
        # Test the method
        recommendations = await mock_spotify_client.get_recommendations(
            seed_tracks=["seed_1", "seed_2"],
            limit=10
        )
        
        assert len(recommendations) == 2
        assert recommendations[0].name == "Recommended Track 1"
        assert recommendations[1].name == "Recommended Track 2"
    
    @pytest.mark.asyncio
    async def test_get_recommendations_too_many_seeds(self, mock_spotify_client):
        """Test recommendations with too many seed tracks."""
        with pytest.raises(DataValidationError):
            await mock_spotify_client.get_recommendations(
                seed_tracks=["seed_1", "seed_2", "seed_3", "seed_4", "seed_5", "seed_6"],
                limit=10
            )
    
    @pytest.mark.asyncio
    async def test_get_recommendations_limit_too_high(self, mock_spotify_client):
        """Test recommendations with limit too high."""
        with pytest.raises(DataValidationError):
            await mock_spotify_client.get_recommendations(
                seed_tracks=["seed_1"],
                limit=150  # Exceeds Spotify's max of 100
            )
    
    @pytest.mark.asyncio
    async def test_search_tracks_success(self, mock_spotify_client):
        """Test successful track search."""
        # Mock Spotify API response
        mock_search_results = {
            "tracks": {
                "items": [
                    {
                        "id": "search_track_1",
                        "name": "Search Result 1",
                        "artists": [{"name": "Search Artist 1"}],
                        "album": {"name": "Search Album 1"},
                        "uri": "spotify:track:search_track_1",
                        "duration_ms": 190000,
                        "popularity": 85
                    }
                ]
            }
        }
        
        mock_spotify_client._client.search.return_value = mock_search_results
        
        # Test the method
        results = await mock_spotify_client.search_tracks("test query", limit=20)
        
        assert len(results) == 1
        assert results[0].name == "Search Result 1"
        assert results[0].artist == "Search Artist 1"
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, mock_spotify_client):
        """Test that caching works correctly."""
        # Mock Spotify API response
        mock_track_data = {
            "id": "cached_track",
            "name": "Cached Track",
            "artists": [{"name": "Cached Artist"}],
            "album": {"name": "Cached Album"},
            "uri": "spotify:track:cached_track",
            "duration_ms": 180000,
            "popularity": 60
        }
        
        mock_spotify_client._client.track.return_value = mock_track_data
        
        # First call should hit API
        track1 = await mock_spotify_client.get_track("cached_track")
        assert mock_spotify_client._client.track.call_count == 1
        
        # Second call should use cache
        track2 = await mock_spotify_client.get_track("cached_track")
        assert mock_spotify_client._client.track.call_count == 1  # No additional API call
        
        # Both tracks should be identical
        assert track1.id == track2.id
        assert track1.name == track2.name
    
    def test_clear_cache(self, mock_spotify_client):
        """Test cache clearing functionality."""
        # Add some data to cache
        mock_spotify_client._track_cache["test_id"] = MagicMock()
        mock_spotify_client._features_cache["test_id"] = MagicMock()
        
        # Clear cache
        mock_spotify_client.clear_cache()
        
        # Verify cache is empty
        assert len(mock_spotify_client._track_cache) == 0
        assert len(mock_spotify_client._features_cache) == 0
    
    @pytest.mark.asyncio
    async def test_close_client(self, mock_spotify_client):
        """Test client cleanup."""
        mock_spotify_client._http_client.aclose = AsyncMock()
        
        await mock_spotify_client.close()
        
        mock_spotify_client._http_client.aclose.assert_called_once()
    
    def test_from_env_missing_credentials(self):
        """Test from_env with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SpotifyAPIError):
                SpotifyClient.from_env()
    
    def test_from_env_success(self):
        """Test successful from_env creation."""
        env_vars = {
            'SPOTIPY_CLIENT_ID': 'test_client_id',
            'SPOTIPY_CLIENT_SECRET': 'test_client_secret',
            'SPOTIPY_REDIRECT_URI': 'http://localhost:8888/callback'
        }
        
        with patch.dict('os.environ', env_vars, clear=True):
            with patch('src.core.spotify.SpotifyClient') as mock_client_class:
                SpotifyClient.from_env()
                mock_client_class.assert_called_once_with(
                    client_id='test_client_id',
                    client_secret='test_client_secret',
                    redirect_uri='http://localhost:8888/callback',
                    config=pytest.any
                )
