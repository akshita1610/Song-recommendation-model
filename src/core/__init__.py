"""Core functionality for song recommendation system."""

from .spotify import (
    SpotifyClient,
    SpotifyTrack,
    AudioFeatures,
    PlaylistInfo,
    SpotifyConfig
)

from ..spotify_client import SpotifyClient as LegacySpotifyClient
from ..recommendation_engine import RecommendationEngine

__all__ = [
    "SpotifyClient",
    "SpotifyTrack", 
    "AudioFeatures",
    "PlaylistInfo",
    "SpotifyConfig",
    "LegacySpotifyClient",
    "RecommendationEngine",
]
