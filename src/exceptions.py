"""Custom exceptions for the song recommendation system."""


class SongRecommendationError(Exception):
    """Base exception for song recommendation system."""
    pass


class SpotifyAPIError(SongRecommendationError):
    """Raised when Spotify API calls fail."""
    pass


class DatabaseError(SongRecommendationError):
    """Raised when database operations fail."""
    pass


class AuthenticationError(SongRecommendationError):
    """Raised when user authentication fails."""
    pass


class DataValidationError(SongRecommendationError):
    """Raised when input data validation fails."""
    pass


class ModelLoadError(SongRecommendationError):
    """Raised when ML model loading fails."""
    pass


class PlaylistGenerationError(SongRecommendationError):
    """Raised when playlist generation fails."""
    pass
