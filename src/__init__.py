"""Song recommendation system utilities."""

from .exceptions import (
    SongRecommendationError,
    SpotifyAPIError,
    DatabaseError,
    AuthenticationError,
    DataValidationError,
    ModelLoadError,
    PlaylistGenerationError,
)

from .data_models import (
    Track,
    Playlist,
    User,
    RecommendationResult,
    AudioFeatures,
)

from .validators import (
    validate_spotify_uri,
    validate_email,
    validate_username,
    validate_password_strength,
    validate_track_data,
    validate_playlist_data,
    validate_pagination_params,
    sanitize_string,
)

from .logging_config import setup_logging, get_logger

__all__ = [
    # Exceptions
    "SongRecommendationError",
    "SpotifyAPIError", 
    "DatabaseError",
    "AuthenticationError",
    "DataValidationError",
    "ModelLoadError",
    "PlaylistGenerationError",
    
    # Data models
    "Track",
    "Playlist", 
    "User",
    "RecommendationResult",
    "AudioFeatures",
    
    # Validators
    "validate_spotify_uri",
    "validate_email",
    "validate_username", 
    "validate_password_strength",
    "validate_track_data",
    "validate_playlist_data",
    "validate_pagination_params",
    "sanitize_string",
    
    # Logging
    "setup_logging",
    "get_logger",
]
