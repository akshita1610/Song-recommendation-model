"""Input validation utilities for the song recommendation system."""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .exceptions import DataValidationError
from .data_models import Track, Playlist, User


def validate_spotify_uri(uri: str, uri_type: str = "track") -> bool:
    """Validate Spotify URI format.
    
    Args:
        uri: Spotify URI to validate
        uri_type: Type of URI (track, artist, album, playlist)
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if not uri or not isinstance(uri, str):
        raise DataValidationError(f"URI must be a non-empty string")
    
    # More flexible pattern - Spotify IDs can be 22 characters (base62) or variable length
    pattern = f"spotify:{uri_type}:[a-zA-Z0-9]{{16,22}}"
    if not re.match(pattern, uri):
        raise DataValidationError(f"Invalid Spotify {uri_type} URI format")
    
    return True


def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if not email or not isinstance(email, str):
        raise DataValidationError("Email must be a non-empty string")
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise DataValidationError("Invalid email address format")
    
    return True


def validate_username(username: str) -> bool:
    """Validate username format.
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if not username or not isinstance(username, str):
        raise DataValidationError("Username must be a non-empty string")
    
    if len(username) < 3 or len(username) > 30:
        raise DataValidationError("Username must be between 3 and 30 characters")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise DataValidationError("Username can only contain letters, numbers, and underscores")
    
    return True


def validate_password_strength(password: str) -> bool:
    """Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if not password or not isinstance(password, str):
        raise DataValidationError("Password must be a non-empty string")
    
    if len(password) < 8:
        raise DataValidationError("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        raise DataValidationError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        raise DataValidationError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        raise DataValidationError("Password must contain at least one digit")
    
    return True


def validate_track_data(track_data: Dict[str, Any]) -> bool:
    """Validate track data dictionary.
    
    Args:
        track_data: Dictionary containing track information
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    required_fields = ['track_uri', 'track_name', 'artist_name', 'artist_uri']
    
    for field in required_fields:
        if field not in track_data or not track_data[field]:
            raise DataValidationError(f"Missing required field: {field}")
    
    validate_spotify_uri(track_data['track_uri'], 'track')
    validate_spotify_uri(track_data['artist_uri'], 'artist')
    
    return True


def validate_playlist_data(playlist_data: Dict[str, Any]) -> bool:
    """Validate playlist data dictionary.
    
    Args:
        playlist_data: Dictionary containing playlist information
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if 'tracks' not in playlist_data or not playlist_data['tracks']:
        raise DataValidationError("Playlist must contain at least one track")
    
    if not isinstance(playlist_data['tracks'], list):
        raise DataValidationError("Tracks must be a list")
    
    for track in playlist_data['tracks']:
        validate_track_data(track)
    
    return True


def validate_pagination_params(limit: int, offset: int) -> bool:
    """Validate pagination parameters.
    
    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip
        
    Returns:
        True if valid, raises DataValidationError if invalid
    """
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise DataValidationError("Limit must be an integer between 1 and 100")
    
    if not isinstance(offset, int) or offset < 0:
        raise DataValidationError("Offset must be a non-negative integer")
    
    return True


def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """Sanitize string input.
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_string, str):
        raise DataValidationError("Input must be a string")
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', input_string)
    
    # Trim whitespace and limit length
    sanitized = sanitized.strip()[:max_length]
    
    return sanitized
