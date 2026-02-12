"""Data models for the song recommendation system."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Track:
    """Represents a music track."""
    track_uri: str
    track_name: str
    artist_name: str
    artist_uri: str
    album_uri: str
    album_name: str
    track_id: int
    
    def __post_init__(self) -> None:
        """Validate track data after initialization."""
        if not self.track_uri or not self.track_name:
            raise ValueError("Track URI and name are required")


@dataclass
class Playlist:
    """Represents a music playlist."""
    playlist_id: str
    name: str
    description: Optional[str]
    tracks: List[Track]
    modified_at: Optional[datetime] = None
    num_followers: int = 0
    num_edits: int = 0
    
    def __post_init__(self) -> None:
        """Validate playlist data after initialization."""
        if not self.playlist_id or not self.name:
            raise ValueError("Playlist ID and name are required")
        if not self.tracks:
            raise ValueError("Playlist must contain at least one track")


@dataclass
class User:
    """Represents a user in the system."""
    username: str
    password_hash: str
    email: str
    count: int = 10
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # User preferences
    loved_it: List[str] = None
    like_it: List[str] = None
    okay: List[str] = None
    hate_it: List[str] = None
    recently_searched: List[str] = None
    
    def __post_init__(self) -> None:
        """Initialize lists if not provided."""
        if self.loved_it is None:
            self.loved_it = []
        if self.like_it is None:
            self.like_it = []
        if self.okay is None:
            self.okay = []
        if self.hate_it is None:
            self.hate_it = []
        if self.recently_searched is None:
            self.recently_searched = []


@dataclass
class RecommendationResult:
    """Represents a recommendation result."""
    recommended_tracks: List[Track]
    confidence_scores: List[float]
    algorithm_used: str
    processing_time: float
    user_feedback: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Validate recommendation result."""
        if len(self.recommended_tracks) != len(self.confidence_scores):
            raise ValueError("Tracks and confidence scores must have same length")


@dataclass
class AudioFeatures:
    """Represents audio features of a track."""
    danceability: float
    energy: float
    key: int
    loudness: float
    mode: int
    speechiness: float
    acousticness: float
    instrumentalness: float
    liveness: float
    valence: float
    tempo: float
    duration_ms: int
    time_signature: int
    
    def __post_init__(self) -> None:
        """Validate audio features."""
        for feature_name in ['danceability', 'energy', 'speechiness', 
                           'acousticness', 'instrumentalness', 'liveness', 'valence']:
            value = getattr(self, feature_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{feature_name} must be between 0.0 and 1.0")
