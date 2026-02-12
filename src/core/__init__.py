"""Core functionality for song recommendation system."""

from .spotify import (
    SpotifyClient,
    SpotifyTrack,
    AudioFeatures,
    PlaylistInfo,
    SpotifyConfig
)

from ..recommendation_engine import RecommendationEngine

__all__ = [
    "SpotifyClient",
    "SpotifyTrack", 
    "AudioFeatures",
    "PlaylistInfo",
    "SpotifyConfig",
    "RecommendationEngine",
]
